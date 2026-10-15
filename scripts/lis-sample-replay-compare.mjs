#!/usr/bin/env node
// Replay the same requests against two services and compare the answers.
// Generalises scripts/vp18796-replay-compare.mjs (POST-only, storage-specific)
// for the LIS-Sample -> trans route families of Phase C (VP-18482).
//
// Usage:
//   node scripts/lis-sample-replay-compare.mjs \
//     --a http://127.0.0.1:16399 --b http://127.0.0.1:3147 \
//     --method GET --path /patients/v2/kits --requests kits.json \
//     [--compare bytes|json] [--normalise none|storage] \
//     [--concurrency 4] [--timeout 10000] [--out report.json]
//
// requests.json: {"requests":[{"query":"accession_id=2610026298"}, {"body":{...}}, ...]}
//   GET  -> each entry's `query` is appended as ?query
//   POST -> each entry's `body` is sent as JSON (`query` also honoured)
// Token: env REPLAY_TOKEN (never printed). Ids in requests.json are opaque;
// keep the file out of git (PHI-safe ids only, per VP-18482).
//
// --compare bytes (default): the raw response text must be identical.
// --compare json: bodies are parsed and compared after --normalise.
//
// Verdict per request (ENGINEERING-LESSONS "shadow compare three-state"):
//   equal        both 2xx and identical (per --compare)
//   differ       both 2xx, not identical, also after one re-run of both sides
//   both_failed  both non-2xx with the same status (and same body under bytes)
//   both_failed_status_differs
//   a_failed / b_failed   exactly one side non-2xx

import fs from 'node:fs';

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, cur, i, arr) => {
    if (cur.startsWith('--')) acc.push([cur.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : 'true']);
    return acc;
  }, []),
);
const need = (k) => { if (!args[k]) { console.error(`missing --${k}`); process.exit(2); } return args[k]; };
const A = need('a').replace(/\/$/, '');
const B = need('b').replace(/\/$/, '');
const METHOD = (args.method ?? 'GET').toUpperCase();
const PATH = need('path');
const TOKEN = process.env.REPLAY_TOKEN;
if (!TOKEN) { console.error('missing env REPLAY_TOKEN'); process.exit(2); }
const COMPARE = args.compare ?? 'bytes';
const NORMALISE = args.normalise ?? 'none';
const requests = JSON.parse(fs.readFileSync(need('requests'), 'utf8')).requests;
const concurrency = Number(args.concurrency ?? 4);
const timeoutMs = Number(args.timeout ?? 10000);

async function call(base, req) {
  const t0 = Date.now();
  const url = base + PATH + (req.query ? `?${req.query}` : '');
  try {
    const res = await fetch(url, {
      method: METHOD,
      headers: { 'content-type': 'application/json', authorization: `Bearer ${TOKEN}`, 'service-name': 'lis-sample-replay' },
      body: METHOD === 'GET' || req.body === undefined ? undefined : JSON.stringify(req.body),
      signal: AbortSignal.timeout(timeoutMs),
    });
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch { /* non-JSON body */ }
    return { ok: res.status >= 200 && res.status < 300, status: res.status, text, json, ms: Date.now() - t0 };
  } catch (e) {
    return { ok: false, status: 0, text: '', json: null, error: String(e?.message ?? e), ms: Date.now() - t0 };
  }
}

const sortBy = (arr, key) => [...arr].sort((x, y) => (x[key] > y[key] ? 1 : x[key] < y[key] ? -1 : 0));
const normalisers = {
  none: (j) => j,
  storage: (j) => {
    if (!j || typeof j !== 'object' || !j.data || typeof j.data !== 'object') return j;
    const out = JSON.parse(JSON.stringify(j));
    delete out.data.watermark;
    if (Array.isArray(out.data.storage_records)) out.data.storage_records = sortBy(out.data.storage_records, 'index');
    for (const k of ['rack_id_list', 'rack_type_list', 'rack_dimension_list', 'user_list'])
      if (Array.isArray(out.data[k])) out.data[k] = [...out.data[k]].sort();
    return out;
  },
};
const normalise = normalisers[NORMALISE];
if (!normalise) { console.error(`unknown --normalise ${NORMALISE}`); process.exit(2); }
const same = (a, b) => (COMPARE === 'bytes' ? a.text === b.text : JSON.stringify(normalise(a.json)) === JSON.stringify(normalise(b.json)));

function diffPaths(x, y, prefix = '') {
  if (typeof x !== typeof y || Array.isArray(x) !== Array.isArray(y)) return [prefix || '/'];
  if (x && typeof x === 'object') {
    const keysX = Object.keys(x), keysY = Object.keys(y);
    const out = [];
    if (!Array.isArray(x) && keysX.join() !== keysY.join() && keysX.sort().join() === keysY.sort().join()) out.push(`${prefix || '/'} (key order)`);
    for (const k of new Set([...keysX, ...keysY])) out.push(...diffPaths(x[k], y[k], `${prefix}/${k}`));
    return out;
  }
  return x === y ? [] : [prefix || '/'];
}

function verdictOf(a, b) {
  if (a.ok && b.ok) return same(a, b) ? 'equal' : 'differ';
  if (!a.ok && !b.ok) return a.status === b.status && (COMPARE !== 'bytes' || a.text === b.text) ? 'both_failed' : 'both_failed_status_differs';
  return !a.ok ? 'a_failed' : 'b_failed';
}

async function judge(req) {
  let a = await call(A, req);
  let b = await call(B, req);
  let verdict = verdictOf(a, b);
  const detail = {};
  if (verdict === 'differ') {
    // Data may have moved between the two calls: re-run both once before counting a differ.
    a = await call(A, req); b = await call(B, req);
    verdict = verdictOf(a, b);
    detail.rerun = true;
  }
  if (verdict !== 'equal' && verdict !== 'both_failed') {
    detail.diff = a.json && b.json ? diffPaths(normalise(a.json), normalise(b.json)).slice(0, 20) : undefined;
    detail.a_text = a.text.slice(0, 300);
    detail.b_text = b.text.slice(0, 300);
  }
  return { verdict, req, a: { status: a.status, ms: a.ms, error: a.error }, b: { status: b.status, ms: b.ms, error: b.error }, ...detail };
}

const results = [];
let next = 0;
async function worker() {
  while (next < requests.length) {
    const i = next++;
    results[i] = await judge(requests[i]);
    process.stderr.write(`${i + 1}/${requests.length} ${results[i].verdict}\n`);
  }
}
await Promise.all(Array.from({ length: Math.min(concurrency, requests.length) }, worker));

const counts = {};
for (const r of results) counts[r.verdict] = (counts[r.verdict] ?? 0) + 1;
const lat = (side) => { const xs = results.map((r) => r[side].ms).sort((x, y) => x - y); return { p50: xs[Math.floor(xs.length * 0.5)], p95: xs[Math.floor(xs.length * 0.95)], max: xs[xs.length - 1] }; };
const summary = { total: requests.length, counts, latency_ms: { a: lat('a'), b: lat('b') }, method: METHOD, path: PATH, compare: COMPARE, normalise: NORMALISE, a: A, b: B, at: new Date().toISOString() };
console.log(JSON.stringify(summary, null, 2));
if (args.out) fs.writeFileSync(args.out, JSON.stringify({ summary, results }, null, 1));
process.exit((counts.equal ?? 0) + (counts.both_failed ?? 0) === requests.length ? 0 : 1);
