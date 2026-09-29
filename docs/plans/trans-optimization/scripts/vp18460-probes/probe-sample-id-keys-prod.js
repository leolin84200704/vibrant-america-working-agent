const axios = require('axios'); const qs = require('querystring');
const ACC = process.argv[2];
const W = 'https://api.vibrant-wellness.com';
const SHIP = 'http://lis-shipping-service.shipping.svc.cluster.local:16256';
const ACC_SVC = 'http://lis-accounting-service.bkkeeping.svc.cluster.local:8084';
const SMP = 'http://lis-sample-service.sample.svc.cluster.local:16300';
(async () => {
  const r = await axios.post(process.env.OAUTH2_TOKEN_ENDPOINT, qs.stringify({client_id: process.env.OAUTH2_CLIENT_ID, client_secret: process.env.OAUTH2_CLIENT_SECRET, grant_type: 'client_credentials'}), {headers: {'Content-Type': 'application/x-www-form-urlencoded'}});
  const token = r.data.access_token;
  const call = (m, u, body) => axios({method: m, url: u, data: body, headers: Object.assign({Authorization: 'Bearer ' + token}, body ? {'Content-Type': 'application/json'} : {}), responseType: 'arraybuffer', validateStatus: () => true, timeout: 40000}).then(x => ({status: x.status, len: x.data.length, body: Buffer.from(x.data)}));
  const kit = await call('GET', SMP + '/patients/v2/kits?accession_id=' + ACC);
  const txt = kit.body.toString(); const m = txt.match(/"sample_id"\s*:\s*"?(\d+)/); const SID = m ? m[1] : null;
  console.log('sample_id from kit status: ' + SID + ' (keys: ' + Object.keys(JSON.parse(txt)).slice(0,8).join(',') + ')');
  if (!SID) return;
  const E = [
   ['inventory_url', 'GET', W+'/v1/lis/shipping/orders/samples/'+SID, SHIP+'/orders/samples/'+SID],
   ['shippin_address', 'GET', W+'/v1/lis/shipping/orders/samples/shipping-address?sample_id='+SID, SHIP+'/orders/samples/shipping-address?sample_id='+SID],
   ['inventory_url_skin', 'GET', W+'/v1/lis/shipping/orders/'+SID, SHIP+'/orders/'+SID],
   ['CHARGE_INFO_URL', 'GET', W+'/v1/lis/accounting/charge/invoice?charge_type_id='+SID, ACC_SVC+'/v1/lis/accounting/charge/invoice?charge_type_id='+SID],
   ['getOrderRecept', 'GET', W+'/v2/accounting/statement/downloadReceipt?sample_id='+SID, ACC_SVC+'/v2/accounting/statement/downloadReceipt?sample_id='+SID],
   ['sample_url', 'GET', W+'/v1/lis/samples/status?sample_id='+SID, SMP+'/status?sample_id='+SID],
   ['transaction', 'POST', W+'/v1/charging/transaction/transactionInfoV2', 'http://lis-charging-service.charging.svc.cluster.local:8084/v1/charging/transaction/transactionInfoV2', {sample_id: Number(SID)}],
   ['billing_detail', 'POST', W+'/v2/accounting/charge/billingDetail', ACC_SVC+'/v2/accounting/charge/billingDetail', {sample_id: Number(SID)}],
  ];
  for (const [k, mth, o, n, body] of E) {
    const [a, b] = await Promise.all([call(mth, o, body), call(mth, n, body)]);
    const eq = a.status === b.status && a.body.equals(b.body);
    console.log(`${k}: old=${a.status}/${a.len}B new=${b.status}/${b.len}B eq=${eq}` + (eq ? '' : `\n    old: ${a.body.toString().slice(0,140).replace(/\n/g,' ')}\n    new: ${b.body.toString().slice(0,140).replace(/\n/g,' ')}`));
  }
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
