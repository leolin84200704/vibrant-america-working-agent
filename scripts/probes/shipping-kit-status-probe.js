// Read-only probe: call LIS-Shipping GetKitStatusBySampleId for a list of sample ids and print
// outbound / return package status. Run from inside an emr-v2 pod (node + @grpc/* available).
//
//   node shipping-kit-status-probe.js 2598251,2598000
//   IDS=$(seq -f '%.0f' -s, 2598230 2598275)   # NOT plain `seq`: macOS seq prints %g (2.59823e+06)
//
// Every id is validated as a plain integer BEFORE anything is sent. The proto field is a string
// and shipping's V1 fallback silently Number()s whatever arrives, so a malformed id would come
// back as a different sample's data (2026-09-30 incident, see STM VP-18593).
const raw = (process.argv[2] || '').split(',').map((s) => s.trim()).filter(Boolean);
if (!raw.length) { console.error('usage: node shipping-kit-status-probe.js <id>[,<id>...]'); process.exit(2); }
const bad = raw.filter((id) => !/^\d+$/.test(id));
if (bad.length) {
  console.error(`refusing to send ${bad.length} non-integer sample id(s): ${bad.slice(0, 5).join(', ')}${bad.length > 5 ? ', ...' : ''}`);
  console.error("hint: on macOS generate ranges with: seq -f '%.0f' -s, START END");
  process.exit(2);
}
const ids = [...new Set(raw)];
if (ids.length !== raw.length) console.error(`note: ${raw.length - ids.length} duplicate id(s) dropped`);

// gRPC modules are loaded only after the id list passed validation.
const grpc = require('@grpc/grpc-js');
const loader = require('@grpc/proto-loader');
const fs = require('fs');
const os = require('os');
const path = require('path');

const proto = `syntax = "proto3"; package shipping;
service ShippingService { rpc GetKitStatusBySampleId(SampleId) returns (KitStatus) {} }
message SampleId { string sample_id = 1; }
message KitStatus { repeated SendOut send_out = 1; ReturnFrom return_from = 2; }
message SendOut { int32 po_number = 1; string po_create_time = 2; string customer_type = 3; repeated Packages packages = 4; }
message Packages { string tracking_number = 1; string package_status = 2; string url = 3; string kit_name = 4; string pickup_time = 5; }
message ReturnFrom { repeated Kits kits = 1; }
message Kits { int32 po_number = 1; string kit_name = 2; string tracking_number = 3; string kit_status = 4; }`;
const protoPath = path.join(os.tmpdir(), `shipping-kit-status-probe-${process.pid}.proto`);
fs.writeFileSync(protoPath, proto);
const def = loader.loadSync(protoPath, { keepCase: true, longs: String, enums: String, defaults: true });
fs.unlinkSync(protoPath);
const pkg = grpc.loadPackageDefinition(def).shipping;

const host = (process.env.GRPC_SHIPPING_CLOUD_HOST || 'lis-shipping-service-grpc.shipping.svc.cluster.local')
  + ':' + (process.env.GRPC_SHIPPING_CLOUD_PORT || '63142');
const client = new pkg.ShippingService(host, grpc.credentials.createInsecure());

function one(id) {
  return new Promise((res) => {
    const deadline = new Date(Date.now() + 8000);
    client.GetKitStatusBySampleId({ sample_id: id }, new grpc.Metadata(), { deadline }, (err, r) => {
      if (err) { console.log(id, 'ERR', err.message); return res(); }
      for (const so of r.send_out || []) for (const p of so.packages || [])
        console.log(id, 'OUT', JSON.stringify({ tn: p.tracking_number, st: p.package_status, url: p.url, pickup_time: p.pickup_time, po_create: so.po_create_time }));
      for (const k of (r.return_from && r.return_from.kits) || [])
        console.log(id, 'RET', JSON.stringify({ tn: k.tracking_number, st: k.kit_status }));
      if (!(r.send_out || []).length) console.log(id, 'no send_out');
      res();
    });
  });
}
(async () => { for (const id of ids) await one(id); process.exit(0); })();
