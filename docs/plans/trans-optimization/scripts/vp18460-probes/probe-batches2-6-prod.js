// Generic old-vs-new equivalence probe. argv: accession, sampleId(optional), barcodeId(optional)
const axios = require('axios'); const qs = require('querystring');
const ACC = process.argv[2] || '0000000000'; const SID = process.argv[3] || '0'; const BC = process.argv[4] || ACC;
const W = 'https://api.vibrant-wellness.com'; const VA = 'https://api.vibrant-america.com';
const SHIP = 'http://lis-shipping-service.shipping.svc.cluster.local:16256';
const ACC_SVC = 'http://lis-accounting-service.bkkeeping.svc.cluster.local:8084';
const CHG = 'http://lis-charging-service.charging.svc.cluster.local:8084';
const SMP = 'http://lis-sample-service.sample.svc.cluster.local:16300';
const ORD = 'http://lis-order.default.svc.cluster.local:4242';
const IR = 'http://lis-interactive-report.report.svc.cluster.local:30900';
const OAUTH = 'http://oauth-service.oauth.svc.cluster.local:8000';
const TRANS = 'http://lis-trans-service.default.svc.cluster.local:3146';
const PDF = 'http://report-pdf-engine.report.svc.cluster.local:80';
const E = [
 // batch 2 shipping
 ['inventory_url', 'GET', W+'/v1/lis/shipping', SHIP, '/orders/samples/'+SID, true],
 ['shippin_address', 'GET', W+'/v1/lis/shipping', SHIP, '/orders/samples/shipping-address?sample_id='+SID, true],
 ['inventory_url_skin', 'GET', W+'/v1/lis/shipping/orders', SHIP+'/orders', '/'+SID, true],
 ['shipping_collection_status', 'POST', W+'/v1/lis/shipping/orders/samples/collection-status/submission', SHIP+'/orders/samples/collection-status/submission', '', false],
 // batch 3 accounting + charging
 ['CHARGE_INFO_URL', 'GET', W+'/v1/lis/accounting/charge/invoice?charge_type_id', ACC_SVC+'/v1/lis/accounting/charge/invoice?charge_type_id', '='+SID, true],
 ['getinvoice', 'GET', W+'/v1/accounting/charge/invoice?charge_type=testorder&charge_type_id=', ACC_SVC+'/v1/accounting/charge/invoice?charge_type=testorder&charge_type_id=', SID, true],
 ['billing_detail', 'POST', W+'/v2/accounting/charge/billingDetail', ACC_SVC+'/v2/accounting/charge/billingDetail', '', false],
 ['getOrderRecept', 'GET', W+'/v2/accounting/statement/downloadReceipt?sample_id=', ACC_SVC+'/v2/accounting/statement/downloadReceipt?sample_id=', SID, true],
 ['transaction', 'POST', W+'/v1/charging/transaction/transactionInfoV2', CHG+'/v1/charging/transaction/transactionInfoV2', '', false],
 // batch 4 samples + order
 ['getKitStatusV2', 'GET', W+'/v1/lis/samples/patients/v2/kits?accession_id=', SMP+'/patients/v2/kits?accession_id=', ACC, true],
 ['sample_url', 'GET', W+'/v1/lis/samples', SMP, '/status?sample_id='+SID, true],
 ['url_order_summary_new', 'GET', W+'/v1/portal/order/patientPage/generateNormalOrderPdf?sampleId=', ORD+'/patientPage/generateNormalOrderPdf?sampleId=', SID, false],
 ['url_order_summary_new_redraw', 'GET', W+'/v1/portal/order/patientPage/generateRedrawOrderPdf?sampleId=', ORD+'/patientPage/generateRedrawOrderPdf?sampleId=', SID, false],
 // batch 5 interactive-report
 ['getSubmittedBarcodesInfo_questionnaire', 'GET', W+'/v1/lis/interactive-report-service/questions-data/getSubmittedBarcodesInfo?templateId=', IR+'/questions-data/getSubmittedBarcodesInfo?templateId=', '2', true],
 ['questionnaire_status', 'GET', W+'/v1/lis/interactive-report-service/questions-data/getBarcodeQuestionnairesStatus?barcodeId=', IR+'/questions-data/getBarcodeQuestionnairesStatus?barcodeId=', BC, true],
 ['skin_questions_data_getAnswer', 'POST', W+'/v1/lis/interactive-report-service/questions-data/getAnswer', IR+'/questions-data/getAnswer', '', false],
 ['skin_questions_data_template_questions', 'GET', W+'/v1/lis/interactive-report-service/questions-data/template-questions?templateId=2', IR+'/questions-data/template-questions?templateId=2', '', true],
 ['NutriProZ', 'POST', W+'/v1/lis/interactive-report-service/report-data/getResultZoneInOut', IR+'/report-data/getResultZoneInOut', '', false],
 // batch 6 remainder
 ['OAUTH2_TOKEN_ENDPOINT', 'POST', W+'/v1/oauth2/token', OAUTH+'/token', '', 'oauth'],
 ['GET_SETTING_URL', 'GET', W+'/v1/portal/trans-service/utility/getSetting', TRANS+'/utility/getSetting', '', true],
 ['va_events', 'POST', W+'/v1/portal/calendar/events/samples/get-events', TRANS+'/events/samples/get-events', '', false],
 ['url_get_product_report1', 'GET', VA+'/v1/report-pdf-engine/pdf?url=', PDF+'/pdf?url=', 'https%3A%2F%2Fexample.invalid%2F', false],
];
(async () => {
  const r = await axios.post(process.env.OAUTH2_TOKEN_ENDPOINT, qs.stringify({client_id: process.env.OAUTH2_CLIENT_ID, client_secret: process.env.OAUTH2_CLIENT_SECRET, grant_type: 'client_credentials'}), {headers: {'Content-Type': 'application/x-www-form-urlencoded'}});
  const token = r.data.access_token; console.log('token ok');
  const call = (m, u, auth, body) => axios({method: m, url: u, data: body, headers: Object.assign({}, auth ? {Authorization: 'Bearer ' + token} : {}, body ? {'Content-Type': 'application/json'} : {}), responseType: 'arraybuffer', validateStatus: () => true, timeout: 40000}).then(x => ({status: x.status, len: x.data.length, body: Buffer.from(x.data)})).catch(e => ({status: 'ERR:' + e.code, len: 0, body: Buffer.alloc(0)}));
  for (const [k, m, o, n, suf, auth] of E) {
    let line = k + ': ';
    if (auth === 'oauth') {
      const form = qs.stringify({client_id: process.env.OAUTH2_CLIENT_ID, client_secret: process.env.OAUTH2_CLIENT_SECRET, grant_type: 'client_credentials'});
      const [a, b] = await Promise.all([axios.post(o, form, {headers: {'Content-Type': 'application/x-www-form-urlencoded'}, validateStatus: () => true}), axios.post(n, form, {headers: {'Content-Type': 'application/x-www-form-urlencoded'}, validateStatus: () => true})]);
      line += `token old=${a.status} new=${b.status} keys_equal=${JSON.stringify(Object.keys(a.data||{}).sort())===JSON.stringify(Object.keys(b.data||{}).sort())} exp=${a.data&&a.data.expires_in}/${b.data&&b.data.expires_in}`;
      console.log(line); continue;
    }
    const body = m === 'POST' ? {} : undefined;
    const [uo, un] = await Promise.all([call(m, o + suf, false, body), call(m, n + suf, false, body)]);
    line += `unauth old=${uo.status}/${uo.len}B new=${un.status}/${un.len}B eq=${uo.status===un.status && uo.body.equals(un.body)}`;
    if (auth === true) {
      const [ao, an] = await Promise.all([call(m, o + suf, true, body), call(m, n + suf, true, body)]);
      line += ` | auth old=${ao.status}/${ao.len}B new=${an.status}/${an.len}B eq=${ao.status===an.status && ao.body.equals(an.body)}`;
      if (!(ao.status===an.status && ao.body.equals(an.body))) line += `\n    old: ${ao.body.toString().slice(0,160).replace(/\n/g,' ')}\n    new: ${an.body.toString().slice(0,160).replace(/\n/g,' ')}`;
    }
    console.log(line);
  }
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
