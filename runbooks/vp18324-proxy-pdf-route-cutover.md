# VP-18324 — `downloadTestOrderPDF` off the trans proxy route: rollback runbook

> Prepared 2026-09-22, after the cutover was already live (Leo: "先不刪，把可以backup 的方案做好先").
> Status: **cutover LIVE on all 8 pods. Rollback path DRILLED on staging, not merely written.**
> Nothing has been deleted. The old route is still served and still works.

## 1. What is live

Two independent steps, each reversible on its own.

| Step | What | Where | State |
|---|---|---|---|
| 1 | The call sends `&clinic_id=` | `LIS-setting-consumer` `setting-consumer.controller.ts` `getOrderReport` | main `24d8c5c` (prod), stage_test `22d09fe` (staging) |
| 2 | The URL points at `/trans` instead of `/proxy/old-report` | 4 ConfigMaps in ns `setting` | flipped 2026-09-22 23:27–23:33Z |

Step 1 is additive and **needs no rollback**: the old proxy route accepts the extra parameter and
returns the same document. That is what let the two steps ship separately.

Step 2 is one key in four ConfigMaps.

## 2. The only value that changed

Key: `url_downloadTestOrderPDFv2`

| ConfigMap (ns `setting`) | Deployment | Pods | Before → After |
|---|---|---|---|
| `lis-setting-consumer-config` | `lis-setting-consumer` | 3 | `…:3146/proxy/old-report/downloadTestOrderPDF` → `…:3146/trans/downloadTestOrderPDF` |
| `lis-setting-consumer-local-config` | `lis-setting-consumer-local` | 3 | same as above |
| `lis-setting-consumer-st-config` | `lis-setting-consumer-st` | 1 | `…-st…:3147/proxy/old-report/downloadTestOrderPDF` → `…-st…:3147/trans/downloadTestOrderPDF` |
| `lis-setting-consumer-local-st-config` | `lis-setting-consumer-local-st` | 1 | same as above |

Full host prefixes:
- prod: `http://lis-trans-service.default.svc.cluster.local:3146`
- staging: `http://lis-trans-service-st.default.svc.cluster.local:3147`

Key counts are unchanged by the edit: 135 / 122 / 135 / 122.

## 3. Do NOT commit ConfigMap dumps

These ConfigMaps carry real secrets — `Azure_kafka_connection_string`, `Azure_redis_pass`,
`Azure_noti_topic_connection`, `OAUTH2_CLIENT_ID` among them. A `kubectl get cm -o yaml` dump must
never reach a git repo, this one included.

A full dump is also the wrong artifact for this change. One key moved; nobody would restore 135 keys
to undo it. The table above **is** the backup: the previous value is a URL, not a secret, and it is
reproducible from the route name alone.

If a full dump is wanted for a different reason, write it outside any repo and delete it afterwards.

## 4. Rollback

Per environment. Staging first if both are being reverted.

```bash
# --- prod ---
OLD=http://lis-trans-service.default.svc.cluster.local:3146/proxy/old-report/downloadTestOrderPDF
for cm in lis-setting-consumer-config lis-setting-consumer-local-config; do
  kubectl patch cm -n setting $cm --type merge \
    -p "{\"data\":{\"url_downloadTestOrderPDFv2\":\"$OLD\"}}"
done
kubectl rollout restart -n setting deploy/lis-setting-consumer deploy/lis-setting-consumer-local

# --- staging ---
OLD_ST=http://lis-trans-service-st.default.svc.cluster.local:3147/proxy/old-report/downloadTestOrderPDF
for cm in lis-setting-consumer-st-config lis-setting-consumer-local-st-config; do
  kubectl patch cm -n setting $cm --type merge \
    -p "{\"data\":{\"url_downloadTestOrderPDFv2\":\"$OLD_ST\"}}"
done
kubectl rollout restart -n setting deploy/lis-setting-consumer-st deploy/lis-setting-consumer-local-st
```

**The restart is not optional.** All four ConfigMaps reach the pods through
`envFrom: configMapRef`, so the value is baked into the container environment at start. Editing the
ConfigMap alone changes nothing for a running pod.

## 5. How to know the rollback actually took

`kubectl rollout status` is not sufficient — during this cutover it reported
"successfully rolled out" while old pods were still running and still carrying the old value. Judge
on the pods themselves:

```bash
# 1. only the new replicaset remains
kubectl get pods -n setting

# 2. every remaining pod carries the intended value
for P in $(kubectl get pods -n setting -o name | sed 's|pod/||'); do
  c=$(kubectl get pod -n setting $P -o jsonpath='{.spec.containers[0].name}')
  printf "%-48s %s\n" "$P" \
    "$(kubectl exec -n setting $P -c $c -- sh -c 'echo $url_downloadTestOrderPDFv2')"
done
```

Then confirm the route answers, from inside a pod using that pod's own service token. The probe used
for the cutover is `verify_after_flip.js` (see §7) — it calls the pod's live URL and the other route
with the same query and compares status and byte length.

## 6. Rollback drill — performed, not assumed

Run on `lis-setting-consumer-st` on 2026-09-22, immediately after the cutover:

1. Patched the ConfigMap back to `/proxy/old-report/…`, restarted → new pod
   `66b4c4c849-97z7h` came up carrying the old value.
2. Probed from that pod: the proxy route answered normally, and `/trans` without `clinic_id` still
   answered 400 — i.e. the reverted pod is genuinely on the old path.
3. Patched forward again, restarted → `66cc5f79f-pqdjf` carrying the `/trans` value.

Elapsed per environment: the patch is instant, the restart dominates — about 60–90 s for a
single-pod deployment, longer for the 3-pod prod ones.

The drill is why this document claims the rollback works rather than that it should.

## 7. Verification evidence from the cutover (for comparison after any revert)

Measured from inside a prod pod with that pod's own OAuth2 service token. Byte length is identical
on both routes; the sha256 differs **on every call, including two calls of the same route**, because
the PDF trailer's `/ID` is regenerated per render — so compare length, never hash.

| sample | bytes on both routes |
|---|---|
| 2640083 | 482,019 |
| 2640082 | 2,055,992 |
| 2640081 | 493,190 |
| 2640080 | 481,611 |

`/trans` is roughly 3× faster (≈3 s vs ≈8.8 s), since it skips the proxy hop.

Traffic moved cleanly, counted from trans v1 request logs (`service:lis-trans-deployment`,
`@url:*downloadTestOrderPDF*`, bucketed per minute):

```
23:20–23:29Z   proxy 4–10/min      trans 0        before
23:30–23:31Z   proxy 4–6           trans 4–8      rolling restart, both replicasets alive
23:32Z on      proxy 0             trans 8–14     cut over
23:38Z         proxy 4             trans 8        the verification probe, which calls both routes
```

Note the route path lives in the `custom.url` attribute, **not** in the log message — a free-text
search for `old-report` returns zero and must not be read as "no traffic".

## 8. What is deliberately NOT done

Nothing has been deleted. The eleven `/proxy/old-report/*` routes are still served.

**Correction, same day.** An earlier version of this section said `/proxy/old-report` had no caller
attribution. That was wrong — it was written from a local checkout 20 commits behind origin.
`ProxyCallerLogInterceptor` was wired onto that controller in `5a9473f` (2026-09-18) and the deployed
prod image carries it. Attribution has been recording all along, and over the first four days it
shows `downloadTestOrderPDF` at 2,932 events from a single in-cluster `axios/1.4.0` client and the
other ten routes at **zero** — so those ten are backed by measurement, not by a code search.

What VP-18346 is actually for is narrower: both proxy families log under the same labels, so the
old-report events answer to `@operation:proxyGrpcCaller` and are separable only by their `route`
field. PR #813 gives the old-report family its own `@operation:proxyOldReportCaller`.

Also worth holding in mind: `cloud-local-proxy` serves a route-for-route copy of the same eleven
routes. Zero traffic on trans v1 is sufficient to delete trans v1's copy; it is not evidence that the
capability is unused.

Related: VP-18324 (this cutover), VP-18345, VP-18346, VP-18347, epic VP-18260.
