// staging: old = current lis-trans-config-st values (AKS-staging or on-prem dev), new = AKS staging in-cluster
const axios = require('axios'); const qs = require('querystring');
const ACC = process.argv[2] || '0000000000'; const SID = process.argv[3] || '0';
const W = 'https://api.vibrant-wellness.com'; const L = 'https://www.vibrant-america.com/lisapi';
const SHIP = 'http://lis-shipping-service-staging.shipping.svc.cluster.local:16256';
const ACC_SVC = 'http://lis-accounting-service-staging.bkkeeping.svc.cluster.local:8084';
const CHG = 'http://lis-charging-service-staging.charging.svc.cluster.local:8084';
const SMP = 'http://lis-sample-service-staging.sample.svc.cluster.local:16300';
const ORD = 'http://lis-order-dev.lis-order.svc.cluster.local:14242';
const IR = 'http://lis-interactive-report-staging.report.svc.cluster.local:30901';
const OAUTH = 'http://oauth-staging-service.oauth-staging.svc.cluster.local:8000';
const TRANS = 'http://lis-trans-service-st.default.svc.cluster.local:3147';
const E = [
 ['shippin_address', 'GET', W+'/v1/lis/shipping/staging', SHIP, '/orders/samples/shipping-address?sample_id='+SID, true],
 ['inventory_url_skin', 'GET', L+'/v1/lis/inventory-dev-http/orders', SHIP+'/orders', '/'+SID, true],
 ['shipping_collection_status', 'POST', L+'/v1/lis/inventory-dev-http/orders/samples/collection-status/submission', SHIP+'/orders/samples/collection-status/submission', '', false],
 ['CHARGE_INFO_URL', 'GET', W+'/v1/lis/accounting/staging/charge/invoice?charge_type_id', ACC_SVC+'/v1/lis/accounting/staging/charge/invoice?charge_type_id', '='+SID, true],
 ['billing_detail', 'POST', W+'/v2/accounting/staging/charge/billingDetail', ACC_SVC+'/v2/accounting/staging/charge/billingDetail', '', false],
 ['getOrderRecept', 'GET', W+'/v2/accounting/staging/statement/downloadReceipt?sample_id=', ACC_SVC+'/v2/accounting/staging/statement/downloadReceipt?sample_id=', SID, true],
 ['transaction', 'POST', L+'/v1/charging/staging/transaction/transactionInfoV2', CHG+'/v1/charging/staging/transaction/transactionInfoV2', '', false],
 ['getKitStatusV2', 'GET', L+'/v1/lis/sample-dev/patients/v2/kits?accession_id=', SMP+'/patients/v2/kits?accession_id=', ACC, true],
 ['GET_ORDER_tube', 'GET', W+'/v1/portal/order/staging/nonBloodSampleTubeType?sampleId=', ORD+'/nonBloodSampleTubeType?sampleId=', SID, true],
 ['getSubmittedBarcodesInfo_questionnaire', 'GET', L+'/v1/lis/interactive-report-staging-service/questions-data/getSubmittedBarcodesInfo?templateId=', IR+'/questions-data/getSubmittedBarcodesInfo?templateId=', '2', true],
 ['NutriProZ', 'POST', L+'/v1/lis/interactive-report-service/report-data/getResultZoneInOut', IR+'/report-data/getResultZoneInOut', '', false],
 ['questionnaire_status', 'GET', L+'/v1/lis/interactive-report-service/questions-data/getBarcodeQuestionnairesStatus?barcodeId=', IR+'/questions-data/getBarcodeQuestionnairesStatus?barcodeId=', ACC, true],
 ['skin_questions_data_getAnswer', 'POST', W+'/v1/lis/interactive-report-staging-service/questions-data/getAnswer', IR+'/questions-data/getAnswer', '', false],
 ['skin_questions_data_template_questions', 'GET', L+'/v1/lis/interactive-report-service/questions-data/template-questions?templateId=2', IR+'/questions-data/template-questions?templateId=2', '', true],
 ['OAUTH2_TOKEN_ENDPOINT', 'POST', W+'/v1/oauth2/staging/token', OAUTH+'/token', '', 'oauth'],
 ['GET_SETTING_URL', 'GET', W+'/v1/portal/trans-service-st/utility/getSetting', TRANS+'/utility/getSetting', '', true],
 ['va_events', 'POST', L+'/v1/lis/portal-calendar-dev/events/samples/get-events', TRANS+'/events/samples/get-events', '', false],
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
      console.log(line + `token old=${a.status} new=${b.status} keys_equal=${JSON.stringify(Object.keys(a.data||{}).sort())===JSON.stringify(Object.keys(b.data||{}).sort())}`); continue;
    }
    const body = m === 'POST' ? {} : undefined;
    const [uo, un] = await Promise.all([call(m, o + suf, false, body), call(m, n + suf, false, body)]);
    line += `unauth old=${uo.status}/${uo.len}B new=${un.status}/${un.len}B eq=${uo.status===un.status && uo.body.equals(un.body)}`;
    if (auth === true) {
      const [ao, an] = await Promise.all([call(m, o + suf, true, body), call(m, n + suf, true, body)]);
      line += ` | auth old=${ao.status}/${ao.len}B new=${an.status}/${an.len}B eq=${ao.status===an.status && ao.body.equals(an.body)}`;
      if (!(ao.status===an.status && ao.body.equals(an.body))) line += `\n    old: ${ao.body.toString().slice(0,140).replace(/\n/g,' ')}\n    new: ${an.body.toString().slice(0,140).replace(/\n/g,' ')}`;
    }
    console.log(line);
  }
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
