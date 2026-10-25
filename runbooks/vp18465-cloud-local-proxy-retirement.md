# VP-18465 — cloud-local-proxy: scale to zero, delete, archive (runbook)

> Prepared 2026-10-25 (pre-flight). Status: **nothing executed yet.** Ticket start 2026-11-09, due 11-13.
> Companion STM: `storage/short_term_memory/VP-18465.md`. Mechanics inherited from VP-18464 / VP-18730.

## 0. Gate — all three must hold on the day, re-checked live, not from memory

| # | Gate | How to test | Status 2026-10-25 |
|---|---|---|---|
| G1 | Every caller migrated | org code search `lis/cloud-proxy` = billing dead code only; trans v2 repointed 09-14 | PASS |
| G2 | 30 d at zero on AKS | Datadog `@event:cloud_proxy_request -@user_agent:vp184*`, 15 d window, 0 rows; AND the observer is alive (send a probe with UA `vp18465-readonly-probe/1.0`, see its line in Datadog) | PASS for 10-10 -> 10-25 (0 rows; probe line seen 05:53Z). Re-run on 11-09 to cover 10-25 -> 11-09 |
| G3 | 30 d at zero on-prem | appserver04 `/var/tmp/vp18464-capture/cloud-proxy-access.log` (0 non-probe lines) with `heartbeat.log` continuous since 2026-10-06 19:15Z and `capture.err` not growing; AND `kubectl -n lis logs` of the 4 proxy pods, grep `cloud_proxy_request` minus probe UAs | PASS for 10-06 19:15Z -> 10-25 06:03Z (12 access-log lines, all probes; heartbeat 1402-1422 polls every full day; pods 5 lines, all probes). Window ends 2026-11-05 |

Probe command (read-only, leaves a log line on purpose):
```
UA="vp18465-readonly-probe/1.0"
for u in https://api.vibrant-america.com/v1/lis/cloud-proxy/ https://api.vibrant-america.com/v1/lis/cloud-proxy-st/ \
         https://www.vibrant-america.com/lisapi/v1/lis/cloud-proxy/ https://www.vibrant-america.com/lisapi/v1/lis/cloud-proxy-st/; do
  curl -s -o /dev/null -w "$u %{http_code}\n" -A "$UA" --max-time 20 "$u"; done
```
Expected before Phase 1: 200 x4. The api front lines land in Datadog (`service:lis-trans-service-proxy`); the www front lines land in the on-prem pod logs only.

On-prem access: `~/src/credential/onprem-appserver-ssh.md` (password SSH, `leo@192.168.60.5`, expect script). Reachability test: `nc -z -w 3 192.168.60.5 22`.

## 1. Inventory of what gets removed

### AKS (context `lisportalprod`, ns `cloud-local`)
| Kind | Name | Note |
|---|---|---|
| Deployment | `cloud-local-proxy-deployment` (3 replicas), `cloud-local-proxy-deployment-st` (1) | image `lisportalprod.azurecr.io/vibrant/cloud-local-proxy:latest` = 847c103f |
| Service | `cloud-local-proxy-service` :3047, `cloud-local-proxy-service-st` :3048 | ClusterIP |
| Ingress | `cloud-local-ingress` | dedicated: only the two cloud-proxy paths on api.vibrant-america.com; its `tls-secret` does not exist in the ns, nothing else depends on it |
| ConfigMap | `cloud-local-proxy-config`, `cloud-local-proxy-config-st` | 55 keys each, **contain secrets** (Azure redis pass, OAuth2 client secret, JWT secrets) |
| Secret | `tls-secret-dd7fz` | cert-manager temp key, orphan; delete with the rest |

### On-prem (ssh appserver04, ns `lis`)
| Kind | Name | Note |
|---|---|---|
| Deployment | `cloud-local-proxy-deployment` (3), `cloud-local-proxy-deployment-st` (1) | image `192.168.60.9:6004/vibrant/cloud-local-proxy:latest` = f017a0c9; env patched 10-08 with redis/OAuth2 keys |
| Service | `cloud-local-proxy-service` :3047, `cloud-local-proxy-service-st` :3048 | |
| Ingress | `k8s-ingress` — **shared**, 3 paths: `/v1/lis/vw-page(/|$)(.*)` -> `vw-page-service:8444` (index 0, STAYS), `/v1/lis/cloud-proxy(/|$)(.*)` (index 1), `/v1/lis/cloud-proxy-st(/|$)(.*)` (index 2) | never delete the Ingress object; re-read the indices on the day |
| ConfigMap | `cloud-local-proxy-config`, `cloud-local-proxy-config-st` | secrets, same as AKS |
| Capture loop | `/var/tmp/vp18464-capture/` (capture2.sh pid 2165176) | stop after Phase 2 (`pkill` from a script file, not from a `bash -c` whose cmdline contains the pattern) |

Leftovers that stay (harmless, note in the closeout comment): ACR tags `75162fe`, `a419bbd`, `faf8c67`, `faf8c67-node16-noboot`, `latest`; on-prem registry tags `75162fe`, `a419bbd`, `latest`; Azure redis key `lis_local_proxy_service_oauth2_token` (1 h TTL, expires by itself); the proxy's OAuth2 client credentials on api.vibrant-wellness.com (revocation is the OAuth owner's call, not in this ticket).

## 2. Phase 1 — scale to zero (2026-11-09)

Pre-steps, in order:
1. Re-run Gate G2 + G3 live. Any non-probe line => stop, identify the caller (`cf_connecting_ip` is the real caller IP on both clusters), do not scale.
2. Preserve evidence before anything restarts (hot lesson): dump all 4 AKS pod logs and all 4 on-prem pod logs to the scratchpad, plus a copy of the on-prem capture dir; copy the AKS object backup + ConfigMap dump to `~/src/credential/vp18465-cloud-local-backup/` (secrets stay out of git).
3. Send the probe once more (baseline 200 x4).

Scale:
```
# AKS
kubectl -n cloud-local scale deploy cloud-local-proxy-deployment cloud-local-proxy-deployment-st --replicas=0
kubectl -n cloud-local get deploy,pods
# on-prem (as leo on appserver04)
kubectl -n lis scale deploy cloud-local-proxy-deployment cloud-local-proxy-deployment-st --replicas=0
kubectl -n lis get deploy,pods | grep cloud-local
```
Verify: probe x4 now returns 503 (AKS app-routing) / 503 or 502 (on-prem ingress-nginx) — not 200. Record the codes.
Jira: draft the comment (Leo posts) with timestamps, the final zero counts, the probe codes, and the Phase 2 date.

Rollback (seconds): `kubectl ... scale --replicas=3` / `--replicas=1` in the same namespaces; the on-prem env patch stays in place.

## 3. Phase 2 — delete (earliest 2026-11-16, one week after Phase 1, only if nobody reported breakage)

AKS:
```
kubectl -n cloud-local delete ingress cloud-local-ingress
kubectl -n cloud-local delete svc cloud-local-proxy-service cloud-local-proxy-service-st
kubectl -n cloud-local delete deploy cloud-local-proxy-deployment cloud-local-proxy-deployment-st
kubectl -n cloud-local delete cm cloud-local-proxy-config cloud-local-proxy-config-st
kubectl -n cloud-local delete secret tls-secret-dd7fz
kubectl -n cloud-local get all,cm,ingress,secret   # expect only kube-root-ca.crt + default SA token
```
Leave the `cloud-local` namespace itself (Leo 2026-10-25: 先留; deleting a namespace is the one step here that is not undone by re-applying a yaml).

On-prem (appserver04): first `kubectl -n lis get ingress k8s-ingress -o yaml > /var/tmp/vp18465/k8s-ingress-before.yaml`, then remove the two cloud-proxy path entries with a JSON patch by index (read the indices from the dump that day; do not assume), re-get to confirm the other paths are intact, then delete the two Deployments, two Services, two ConfigMaps. Stop capture2.sh and `rm -rf /var/tmp/vp18464-capture` (keep the copied evidence locally).

Verify: probe x4 returns 404 from both fronts; `kubectl get ingress -A | grep cloud` empty on AKS; on-prem k8s-ingress path count = before minus 2.

Rollback: `kubectl apply -f` the saved yamls (AKS objects + ConfigMaps; on-prem ingress-before + Deployments/Services/ConfigMaps dumped before deletion). Images remain in both registries.

## 4. Phase 3 — archive + docs

- Repo `Vibrant-America/cloud-local-proxy`: add a one-paragraph "Retired on <date>, replaced by trans v1 `/trans/*`" note at the top of README (PR, needs an admin merge because of the dead `cloudlocalpremerge-cibuild` required check), then `gh repo archive` — org admin only (Ray). Ask Ray in the same message.
- `platform-infra` `docs/services/redis-caches.md` line 16: drop cloud-local-proxy from the `vibrant-cloud-cache` user list (PR).
- Confluence "Retiring /proxy and cloud-local-proxy" (2697166874, Leo's): add a status line "cloud-local-proxy retired <date>". Roadmap 2711453698 rows P1-E3 / section 5.1 are Yekai's page — tell him in the Jira comment, do not edit.
- `Vibrant-knowledge`: 0 references (checked 2026-10-25), nothing to change — say so in the closeout.
- Jira VP-18465 -> Dev Complete with the four-section closeout; QA twin QH-7323 gets the probe evidence.
