const axios = require('axios'); const qs = require('querystring');
const BARCODE = process.argv[2] || '0000000000';
const OLD = 'https://api.vibrant-wellness.com/v1/lis/base-report-staging-service';
const NEW = 'http://lis-base-report-staging.report.svc.cluster.local:30801';
const paths = {
  Get_product_report_map: '/result/abbreviation?type=aa',
  full_test_mapping: '/result/testHierarchyForReports?barcode=' + BARCODE,
  getReportStatusListV2: '/result/getReportStatusListV2?barcode=' + BARCODE,
  getReportStatusListV2WithInteractiveProducts: '/result/getReportStatusListV2WithInteractiveProducts?barcode=' + BARCODE,
  report_finish_time: '/result/v1ReportGenerationTime?barcode=' + BARCODE,
  pdf_cache_download_url: '/pdf-cache/download/' + BARCODE + '?style=advanced&mode=download',
};
(async () => {
  const r = await axios.post(process.env.OAUTH2_TOKEN_ENDPOINT, qs.stringify({client_id: process.env.OAUTH2_CLIENT_ID, client_secret: process.env.OAUTH2_CLIENT_SECRET, grant_type: 'client_credentials'}), {headers: {'Content-Type': 'application/x-www-form-urlencoded'}});
  const token = r.data.access_token; console.log('token ok len=' + token.length);
  const get = (u, auth) => axios.get(u, {headers: auth ? {Authorization: 'Bearer ' + token} : {}, responseType: 'arraybuffer', validateStatus: () => true, timeout: 30000}).then(x => ({status: x.status, len: x.data.length, body: Buffer.from(x.data)}));
  for (const [k, p] of Object.entries(paths)) {
    const [o, n, ou, nu] = await Promise.all([get(OLD + p, true), get(NEW + p, true), get(OLD + p, false), get(NEW + p, false)]);
    const same = o.status === n.status && o.body.equals(n.body);
    console.log(`${k}: old=${o.status}/${o.len}B new=${n.status}/${n.len}B equal=${same} | unauth old=${ou.status} new=${nu.status}`);
    if (!same) console.log('   old: ' + o.body.toString().slice(0, 200).replace(/\n/g, ' ') + '\n   new: ' + n.body.toString().slice(0, 200).replace(/\n/g, ' '));
  }
  // batch (POST)
  const post = (u, body) => axios.post(u, body, {headers: {Authorization: 'Bearer ' + token}, validateStatus: () => true, timeout: 30000}).then(x => ({status: x.status, body: JSON.stringify(x.data)}));
  const [bo, bn] = await Promise.all([post(OLD + '/result/getReportStatusListV2Batch', {barcodes: [BARCODE]}), post(NEW + '/result/getReportStatusListV2Batch', {barcodes: [BARCODE]})]);
  console.log(`getReportStatusListV2Batch: old=${bo.status}/${bo.body.length}B new=${bn.status}/${bn.body.length}B equal=${bo.status === bn.status && bo.body === bn.body}`);
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
