const axios = require('axios'); const qs = require('querystring');
const W = 'https://api.vibrant-wellness.com';
(async () => {
  const r = await axios.post(process.env.OAUTH2_TOKEN_ENDPOINT, qs.stringify({client_id: process.env.OAUTH2_CLIENT_ID, client_secret: process.env.OAUTH2_CLIENT_SECRET, grant_type: 'client_credentials'}), {headers: {'Content-Type': 'application/x-www-form-urlencoded'}});
  const token = r.data.access_token;
  const get = (u, auth) => axios.get(u, {headers: auth ? {Authorization: 'Bearer ' + token} : {}, responseType: 'text', validateStatus: () => true, timeout: 60000}).then(x => x.data);
  // 1. order summary unauth bodies
  const o1 = await get(W + '/v1/portal/order/patientPage/generateNormalOrderPdf?sampleId=0', false);
  const n1 = await get('http://lis-order.default.svc.cluster.local:4242/patientPage/generateNormalOrderPdf?sampleId=0', false);
  console.log('order_summary unauth old body: ' + o1); console.log('order_summary unauth new body: ' + n1);
  // 2. submitted barcodes: old twice, new once; strip signed-url noise
  const strip = (s) => s.replace(/X-Amz-[A-Za-z-]+=[^&"]*/g, 'X').replace(/[?&](Expires|Signature|Key-Pair-Id|Policy)=[^&"]*/g, '').replace(/https?:\/\/[^"]*/g, (m) => m.split('?')[0]);
  const u = W + '/v1/lis/interactive-report-service/questions-data/getSubmittedBarcodesInfo?templateId=2';
  const nu = 'http://lis-interactive-report.report.svc.cluster.local:30900/questions-data/getSubmittedBarcodesInfo?templateId=2';
  const [a, b, c] = await Promise.all([get(u, true), get(u, true), get(nu, true)]);
  console.log(`submitted: old1==old2 raw=${a === b} stripped=${strip(a) === strip(b)} | old1==new raw=${a === c} stripped=${strip(a) === strip(c)} | lens ${a.length}/${b.length}/${c.length}`);
  if (strip(a) !== strip(c)) { const sa = strip(a), sc = strip(c); let i = 0; while (i < sa.length && sa[i] === sc[i]) i++; console.log('first diff at ' + i + ':\n  old: ' + sa.slice(Math.max(0,i-80), i+120) + '\n  new: ' + sc.slice(Math.max(0,i-80), i+120)); }
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
