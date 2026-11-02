// Read-only: fetch Cerbo vendor SFTP creds (SELECT) and list SFTP root + check target paths.
const path = require('path');
const nm = '/Users/hung.l/src/lis-backend-emr-v2/node_modules/';
const mysql = require(nm + 'mysql2/promise');
const Sftp = require(nm + 'ssh2-sftp-client');
const fs = require('fs');
const env = Object.fromEntries(fs.readFileSync('/Users/hung.l/src/vibrant-america-working-agent/.env','utf8')
  .split('\n').filter(l => /^LIS_EMR_DB_/.test(l)).map(l => { const i = l.indexOf('='); return [l.slice(0,i), l.slice(i+1).replace(/^["']|["']$/g,'')]; }));
(async () => {
  const db = await mysql.createConnection({ host: env.LIS_EMR_DB_HOST, port: +env.LIS_EMR_DB_PORT || 3306,
    user: env.LIS_EMR_DB_USER, password: env.LIS_EMR_DB_PASSWORD, database: env.LIS_EMR_DB_NAME, ssl: {} });
  const [v] = await db.query("SELECT id,name,sftp_host,sftp_port,sftp_username,sftp_password FROM ehr_vendors WHERE id=1");
  const [t] = await db.query("SELECT sftp_order_path,sftp_result_path FROM ehr_vendor_sftp_templates WHERE ehr_vendor_id=1");
  const [r] = await db.query("SELECT id,status,sftp_result_path FROM ehr_integrations WHERE customer_id='12556' OR clinic_id='130454' OR sftp_result_path LIKE '%restorativefunctional%'");
  await db.end();
  const c = v[0];
  console.log('vendor:', c.id, c.name, `${c.sftp_host}:${c.sftp_port}`, c.sftp_username);
  console.log('template:', JSON.stringify(t[0]));
  console.log('existing integration rows for 12556/130454/restorativefunctional*:', r.length);
  const s = new Sftp();
  await s.connect({ host: c.sftp_host, port: c.sftp_port, username: c.sftp_username, password: c.sftp_password, readyTimeout: 15000 });
  for (const p of ['/restorativefunctionalmedicine/orders/','/restorativefunctionalmedicine/results/','/restorativefunctionalmedicineemr/orders/','/restorativefunctionalmedicineemr/results/'])
    console.log(`exists(${p}) =`, await s.exists(p));
  const root = await s.list('/');
  const dirs = root.filter(e => e.type === 'd').map(e => e.name).sort();
  console.log(`root: ${dirs.length} folders`);
  console.log('root folders matching /restor|functional/i:', dirs.filter(n => /restor|functional/i.test(n)));
  await s.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
