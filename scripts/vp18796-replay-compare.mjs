#!/usr/bin/env node
// Replay the same POST bodies against two services and compare the answers.
// Built for VP-18796 (LIS-Sample -> trans, POST /storage/records/samples/retrieval);
// parameterised so Phase C (VP-18482) can reuse or discard it.
//
// Usage:
//   node scripts/vp18796-replay-compare.mjs \
//     --a https://api.vibrant-wellness.com/v1/lis/samples \
//     --b http://127.0.0.1:3146 \
//     --path /storage/records/samples/retrieval \
//     --token "$TOKEN" --bodies bodies.json [--concurrency 4] [--out report.json]
//
// bodies.json: {"bodies":[{...}, ...]}  (one JSON body per request)
// Token is read from --token or env REPLAY_TOKEN; it is never printed.
//
// Verdict per body (ENGINEERING-LESSONS "shadow compare three-state"):
//   equal        both 2xx and normalised bodies deep-equal
//   differ       both 2xx, bodies differ after normalisation AND after one re-run of both sides
//   both_failed  both non-2xx (compared by status only)
//   a_failed / b_failed   exactly one side non-2xx
// Normalisation: `data.watermark` is excluded from equality and checked
// separately as b >= a (B is called after A); `data.storage_records` sorted by
// `index`; list fields sorted. Everything else must match byte for byte.

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
const PATH = args.path ?? '/storage/records/samples/retrieval';
const TOKEN = args.token ?? process.env.REPLAY_TOKEN;
if (!TOKEN) { console.error('missing --token or REPLAY_TOKEN'); process.exit(2); }
const bodies = JSON.parse(fs.readFileSync(need('bodies'), 'utf8')).bodies;
const concurrency = Number(args.concurrency ?? 4);
const timeoutMs = Number(args.timeout ?? 10000);

async function call(base, body) {
  const t0 = Date.now();
  try {
    const res = await fetch(base + PATH, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${TOKEN}`, 'service-name': 'vp18796-replay' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch { /* non-JSON body */ }
    return { ok: res.status >= 200 && res.status < 300, status: res.status, json, text: json ? undefined : text.slice(0, 200), ms: Date.now() - t0 };
  } catch (e) {
    return { ok: false, status: 0, error: String(e?.message ?? e), ms: Date.now() - t0 };
  }
}

const sortBy = (arr, key) => [...arr].sort((x, y) => (x[key] > y[key] ? 1 : x[key] < y[key] ? -1 : 0));
function normalise(json) {
  if (!json || typeof json !== 'object') return json;
  const out = JSON.parse(JSON.stringify(json));
  if (out.data && typeof out.data === 'object') {
    delete out.data.watermark;
    if (Array.isArray(out.data.storage_records)) out.data.storage_records = sortBy(out.data.storage_records, 'index');
    for (const k of ['rack_id_list', 'rack_type_list', 'rack_dimension_list', 'user_list'])
      if (Array.isArray(out.data[k])) out.data[k] = [...out.data[k]].sort();
  }
  return out;
}
const same = (x, y) => JSON.stringify(normalise(x)) === JSON.stringify(normalise(y));

function diffPaths(x, y, prefix = '') {
  const out = [];
  if (typeof x !== typeof y || Array.isArray(x) !== Array.isArray(y)) return [prefix || '/'];
  if (x && typeof x === 'object') {
    for (const k of new Set([...Object.keys(x), ...Object.keys(y)])) out.push(...diffPaths(x[k], y[k], `${prefix}/${k}`));
    return out;
  }
  return x === y ? [] : [prefix || '/'];
}

async function judge(body) {
  let a = await call(A, body);
  let b = await call(B, body);
  let verdict;
  const detail = { body, a: { status: a.status, ms: a.ms, error: a.error, text: a.text }, b: { status: b.status, ms: b.ms, error: b.error, text: b.text } };
  if (a.ok && b.ok) {
    if (same(a.json, b.json)) verdict = 'equal';
    else {
      // Data may have moved between the two calls: re-run both once before counting a differ.
      a = await call(A, body); b = await call(B, body);
      detail.rerun = { a: a.status, b: b.status };
      verdict = a.ok && b.ok ? (same(a.json, b.json) ? 'equal' : 'differ') : (!a.ok && !b.ok ? 'both_failed' : !a.ok ? 'a_failed' : 'b_failed');
      if (verdict === 'differ') detail.diff = diffPaths(normalise(a.json), normalise(b.json)).slice(0, 20);
    }
    if (a.ok && b.ok) {
      const wa = a.json?.data?.watermark, wb = b.json?.data?.watermark;
      detail.watermark = { a: wa, b: wb, monotonic: wa == null || wb == null ? null : wb >= wa };
    }
  } else if (!a.ok && !b.ok) verdict = a.status === b.status ? 'both_failed' : 'both_failed_status_differs';
  else verdict = !a.ok ? 'a_failed' : 'b_failed';
  return { verdict, ...detail };
}

const results = [];
let next = 0;
async function worker() {
  while (next < bodies.length) {
    const i = next++;
    results[i] = await judge(bodies[i]);
    process.stderr.write(`${i + 1}/${bodies.length} ${results[i].verdict}\n`);
  }
}
await Promise.all(Array.from({ length: Math.min(concurrency, bodies.length) }, worker));

const counts = {};
for (const r of results) counts[r.verdict] = (counts[r.verdict] ?? 0) + 1;
const wmViolations = results.filter((r) => r.watermark && r.watermark.monotonic === false).length;
const lat = (side) => { const xs = results.map((r) => r[side].ms).sort((x, y) => x - y); return { p50: xs[Math.floor(xs.length * 0.5)], p95: xs[Math.floor(xs.length * 0.95)], max: xs[xs.length - 1] }; };
const summary = { total: bodies.length, counts, watermark_monotonic_violations: wmViolations, latency_ms: { a: lat('a'), b: lat('b') }, a: A, b: B, path: PATH, at: new Date().toISOString() };
console.log(JSON.stringify(summary, null, 2));
if (args.out) fs.writeFileSync(args.out, JSON.stringify({ summary, results }, null, 1));
process.exit(counts.equal === bodies.length ? 0 : 1);
