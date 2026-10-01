// VP-18243: set ehr_integrations cmufl8atf002d1p07juhd9h11 (clinic 98737 MELISSA JONES_NPI) LIVE -> REJECTED
const fs = require('fs');
const mysql = require('/Users/hung.l/src/lis-backend-emr-v2/node_modules/mysql2/promise');
const env = fs.readFileSync('/Users/hung.l/src/lis-backend-emr-v2/.env', 'utf8');
const url = env.match(/^DATABASE_URL=["']?([^"'\n]+)/m)[1];
const ID = 'cmufl8atf002d1p07juhd9h11';
const BY = 'VP-18243';
const REASON = 'VP-18243: REJECTED - ChARM confirmed no lab interface exists for this practice';
const DETAILS = '98737 MELISSA JONES_NPI (customer 11886, msh06 98737, hl7_version 2.3) -- VP-18243: set to REJECTED on 2026-10-01 on Leo\'s instruction, following ChARM Support\'s written reply of 2026-10-01: "there is currently no Vibrant lab interface set up for Melissa Jones\'s practice, so we don\'t have a receiving-facility code to provide ... please leave this request on hold and treat it the same as the six practices above until an interface is established." ChARM also confirmed HL7 2.3.1 is required (2.3 messages are never accepted) and that an empty response body means non-delivery. This row was reverted to PENDING on 2026-09-28 (history 206) and re-approved to LIVE on 2026-09-29 20:51Z (history 214); one result was then sent on 2026-09-30 22:06Z (sample 2626317, accession 2608316525) as HL7 2.3 with MSH-6 98737 and received an empty body - it was never delivered and must be handled outside the interface. Do not set this row LIVE again until ChARM has onboarded the practice through lab-requests@medicalmine.com and supplied its receiving-facility code, and hl7_version has been set to 2.3.1. ChARM has the practice name as "All In One Peace"; ours is Houston Area Pediatric Neurology (NPI 1114170123) - name mismatch is being queried with ChARM.';
(async () => {
  const u = new URL(url);
  const conn = await mysql.createConnection({ host: u.hostname, port: Number(u.port || 3306), user: decodeURIComponent(u.username), password: decodeURIComponent(u.password), database: u.pathname.replace('/', ''), ssl: { rejectUnauthorized: false } });
  try {
    await conn.beginTransaction();
    const [pre] = await conn.query('SELECT id, status, clinic_id, customer_id, msh06_receiving_facility, hl7_version, updated_at FROM ehr_integrations WHERE id = ? FOR UPDATE', [ID]);
    console.log('pre-image', JSON.stringify(pre));
    if (pre.length !== 1 || pre[0].status !== 'LIVE' || String(pre[0].clinic_id) !== '98737' || pre[0].msh06_receiving_facility !== '98737') throw new Error('pre-image mismatch, abort');
    const [u] = await conn.query('UPDATE ehr_integrations SET status = ?, last_modified_by = ?, updated_at = NOW(3) WHERE id = ? AND status = ?', ['REJECTED', BY, ID, 'LIVE']);
    console.log('update affected', u.affectedRows, 'changed', u.changedRows);
    if (u.affectedRows !== 1) throw new Error('affectedRows != 1, abort');
    const [h] = await conn.query('INSERT INTO ehr_integration_status_history (integration_id, from_status, to_status, reason, additional_details, created_at, changed_by) VALUES (?, ?, ?, ?, ?, NOW(3), ?)', [ID, 'LIVE', 'REJECTED', REASON, DETAILS, BY]);
    console.log('history id', h.insertId);
    const [n] = await conn.query('INSERT INTO ehr_integration_notes (integration_id, content, is_internal, note_type, created_at, updated_at, created_by) VALUES (?, ?, 1, ?, NOW(3), NOW(3), ?)', [ID, DETAILS, 'TECHNICAL', BY]);
    console.log('note id', n.insertId);
    const [v] = await conn.query('SELECT status, updated_at, last_modified_by FROM ehr_integrations WHERE id = ?', [ID]);
    const [live] = await conn.query("SELECT COUNT(*) c FROM ehr_integrations WHERE (clinic_id = 98737 OR customer_id = '11886') AND status = 'LIVE'");
    console.log('in-tx verify', JSON.stringify(v), 'live rows for clinic/customer', live[0].c);
    if (v[0].status !== 'REJECTED' || live[0].c !== 0) throw new Error('in-tx verify failed, abort');
    await conn.commit();
    console.log('COMMITTED');
  } catch (e) {
    await conn.rollback();
    console.error('ROLLED BACK:', e.message);
    process.exitCode = 1;
  } finally {
    await conn.end();
  }
})();
