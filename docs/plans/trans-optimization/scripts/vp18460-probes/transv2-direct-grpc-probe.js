// Direct gRPC probe from the transv2-st pod: ShippingService.GetKitStatusBySampleId at a given address,
// compared with trans v1 st /proxy/grpc/getKitStatus over HTTP (what http mode does today).
const grpc = require('@grpc/grpc-js'); const pl = require('@grpc/proto-loader'); const axios = require('axios'); const qs = require('querystring');
const ADDR = process.argv[2]; const TADDR = process.argv[3]; const SID = process.argv[4] || '500000';
const opts = { keepCase: true, longs: String, enums: String, defaults: true, oneofs: true };
const ship = grpc.loadPackageDefinition(pl.loadSync('', opts)).shipping;
const tests = grpc.loadPackageDefinition(pl.loadSync('/tests.proto', opts)).testresult;
const canon = (v) => JSON.stringify(v, Object.keys(flatten(v)).sort());
function flatten(o, p = '', out = {}) { if (o && typeof o === 'object') for (const k of Object.keys(o)) { out[k] = 1; flatten(o[k], p + k + '.', out); } return out; }
(async () => {
  console.log('shipping pkg keys: ' + Object.keys(ship).join(',') + ' | testresult keys: ' + Object.keys(tests).join(','));
  const c = new ship.ShippingService(ADDR, grpc.credentials.createInsecure());
  const t = new tests.TestResultGrpcService(TADDR, grpc.credentials.createInsecure());
  const cm = Object.keys(Object.getPrototypeOf(c)).filter(k => /^GetKitStatusBySampleId$/.test(k)); console.log('all kit methods: ' + Object.keys(Object.getPrototypeOf(c)).filter(k => /kit/i.test(k)).join(',')); const tm = Object.keys(Object.getPrototypeOf(t)).filter(k => /^getTestStatus$/.test(k));
  console.log('kit methods: ' + cm.join(',') + ' | test methods: ' + tm.join(','));
  c.GetKitStatusBySampleId = c[cm[0]]; t.getTestStatus = t[tm[0]];
  const dl = () => { const d = new Date(); d.setSeconds(d.getSeconds() + 10); return d; };
  const kit = await new Promise((res, rej) => c.GetKitStatusBySampleId({ sample_id: SID }, new grpc.Metadata(), { deadline: dl() }, (e, r) => e ? rej(e) : res(r)));
  console.log('grpc kit ok: ' + JSON.stringify(kit).slice(0, 200));
  const ts = await new Promise((res, rej) => t.getTestStatus({ sampleId: Number(SID) }, new grpc.Metadata(), { deadline: dl() }, (e, r) => e ? rej(e) : res(r)));
  console.log('grpc testStatus ok: ' + JSON.stringify(ts).slice(0, 200));
  // http via trans v1 st proxy
  const r = await axios.post(process.env.OAUTH2_TOKEN_ENDPOINT, qs.stringify({client_id: process.env.OAUTH2_CLIENT_ID, client_secret: process.env.OAUTH2_CLIENT_SECRET, grant_type: 'client_credentials'}), {headers: {'Content-Type': 'application/x-www-form-urlencoded'}, validateStatus: () => true});
  if (r.status !== 200) { console.log('token status ' + r.status + ' ' + JSON.stringify(r.data).slice(0,120)); return; }
  const h = await axios.get(process.env.proxy_getkit + SID, { headers: { Authorization: 'Bearer ' + r.data.access_token }, validateStatus: () => true });
  console.log('http proxy kit: ' + h.status + ' ' + JSON.stringify(h.data).slice(0, 200));
  console.log('canonical equal: ' + (canon(h.data) === canon(kit)));
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
