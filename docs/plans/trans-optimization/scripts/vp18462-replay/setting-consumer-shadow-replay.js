// Read-only replay of setting-consumer's shadow comparison, using the pod's OWN
// proto files, loader options, oauth helpers and diffShadow (dist/), for a range of ids.
const grpc = require('/node_modules/@grpc/grpc-js');
const pl = require('/node_modules/@grpc/proto-loader');
let axios;
const opts = require('/dist/grpc.options.js');
const { diffShadow, normaliseKitStatus } = require('/dist/setting-consumer/proxy-grpc-mode.js');
const oauth = require('/dist/oauth2.js');
const mk = (o) => {
  const def = pl.loadSync(o.options.protoPath, o.options.loader);
  return grpc.loadPackageDefinition(def)[o.options.package];
};
const ship = mk(opts.microserviceOptions_ship), tests = mk(opts.microserviceOptions_tests);
const shipC = new ship.ShippingService(process.env.SHIPPING_RPC, grpc.credentials.createInsecure());
const testC = new tests.TestResultGrpcService(process.env.TEST_RESULT_RPC, grpc.credentials.createInsecure());
const pick = (c, re) => { const k = Object.keys(Object.getPrototypeOf(c)).find(k => re.test(k)); return c[k].bind(c); };
const kitFn = pick(shipC, /^getKitStatusBySampleId$/i), resFn = pick(testC, /^getPatientTestsResult$/i);
const call = (fn, req, md) => new Promise((res, rej) => { const d = new Date(Date.now() + 15000); fn(req, md, { deadline: d }, (e, r) => e ? rej(e) : res(r)); });
const range = (c, n) => Array.from({ length: 2 * n + 1 }, (_, i) => c - n + i);
(async () => { axios = (await import('/node_modules/axios/index.js')).default;
  const tid = 'vp18462-replay-' + Date.now();
  const token = await oauth.getServiceToken();
  const hdr = { headers: { Authorization: 'Bearer ' + token }, validateStatus: () => true };
  const md = await oauth.createOAuth2Metadata(tid, 'setting-bot');
  let stats = { kit: { agree: 0, differ: 0, err: 0, nonEmpty: 0 }, res: { agree: 0, differ: 0, err: 0, nonEmpty: 0 } };
  const kitIds = [...range(Number(process.argv[2] || 2640784), Number(process.argv[3] || 15)), ...process.argv.slice(6).flatMap(c => range(Number(c), 10))];
  for (const sid of kitIds) {
    try {
      const h = await axios.get(process.env.proxy_getkit + sid, hdr);
      const g = normaliseKitStatus(await call(kitFn, { sample_id: String(sid) }, md));
      if (h.status !== 200) { stats.kit.err++; console.log(`kit ${sid} proxy http=${h.status}`); continue; }
      if ((h.data && h.data.send_out && h.data.send_out.length) || (h.data && h.data.return_from && h.data.return_from.kits && h.data.return_from.kits.length)) stats.kit.nonEmpty++;
      const d = diffShadow(h.data, g);
      if (d === null) stats.kit.agree++; else { stats.kit.differ++; console.log(`kit ${sid} DIFF ${JSON.stringify(d).slice(0, 300)}`); }
    } catch (e) { stats.kit.err++; console.log(`kit ${sid} ERR ${String(e.message).slice(0, 160)}`); }
  }
  for (const pid of range(Number(process.argv[4] || 3250142), Number(process.argv[5] || 10))) {
    try {
      const h = await axios.get(process.env.proxy_getresult + pid, hdr);
      const g = await call(resFn, { id: pid }, md);
      if (h.status !== 200) { stats.res.err++; console.log(`res ${pid} proxy http=${h.status}`); continue; }
      if (JSON.stringify(h.data).length > 20) stats.res.nonEmpty++;
      const d = diffShadow(h.data, g);
      if (d === null) stats.res.agree++; else { stats.res.differ++; console.log(`res ${pid} DIFF ${JSON.stringify(d).slice(0, 300)}`); }
    } catch (e) { stats.res.err++; console.log(`res ${pid} ERR ${String(e.message).slice(0, 160)}`); }
  }
  console.log('SUMMARY ' + JSON.stringify(stats) + ' tracking_id=' + tid + ' at ' + new Date().toISOString()); process.exit(0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
