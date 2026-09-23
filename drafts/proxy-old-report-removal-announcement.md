# DRAFT — Slack announcement: removing `/proxy/old-report/downloadTestOrderPDF`

> For Leo to post. Written 2026-09-23. Removal date assumes a one-week notice.
> Section 2 (the other ten routes) is optional — see the note at the bottom.

---

## :warning: Removing `/proxy/old-report/downloadTestOrderPDF` from trans v1 — **2026-09-30**

**Announced 2026-09-23 · removal on or after 2026-09-30 · VP-18324**

### What is going away

```
GET /proxy/old-report/downloadTestOrderPDF
```
on trans v1 (`lis-trans-service`, port 3146).

**If you call this, reply here before 2026-09-30 and it stays until you have moved.**

### Why it is safe to remove

It had exactly one caller, LIS-setting-consumer, and that caller moved to the equivalent `/trans` route yesterday. Traffic, counted from trans v1 request logs:

| | `/proxy/old-report/downloadTestOrderPDF` | `/trans/downloadTestOrderPDF` |
|---|---|---|
| 7 days before the switch | 100–650 per hour at peak | a trickle |
| since 2026-09-22 23:32Z | **0** | 100–600 per hour |

The work did not disappear — it moved. The only hits on the old route since the switch are four requests from our own verification probes at 18:00Z and 19:00Z today, which deliberately call both routes to compare them.

Caller attribution has been running on these routes since 2026-09-18 and names the caller on every request, so this is measured rather than inferred.

### If you need this endpoint

The replacement is the same service, same port, same response:

```
GET /trans/downloadTestOrderPDF
```

**One difference that will bite you:** `/trans` resolves identity from the JWT and falls back to query parameters, so a service token that carries neither `customer_id` nor `clinic_id` gets **400 Bad Request** unless you send `clinic_id` in the query. The proxy route never needed it. Add `&clinic_id=` and you get a byte-for-byte equivalent document — and about 3× faster, since it skips the proxy hop.

### Timeline

- **2026-09-23** — announced, one week's notice starts
- **2026-09-30** — re-check the logs, then open the removal PR
- Removal is a route deletion in trans v1; reverting it is a revert, not a config change

---

## 2. The other ten `/proxy/old-report/*` routes (optional to include)

The same family has ten more routes. Since caller attribution went live on 2026-09-18, **not one of them has recorded a single request** — 2,936 attributed requests in that window, all of them `downloadTestOrderPDF`.

```
getRequisitionForm              GenerateBatchReqOrReportV2
GenerateOnlineZipDownloadV2     getOrderSummaryReportZip
GetSpecificReports              GenerateOnlineSummaryReport
GenerateProducctSummaryReport   GenerateProducctReport
checkIfPersonalizedReportCanBeCreated
oneClickPersonalizedReport
```

Every one has a 1:1 twin on `/trans` served by the same code, so removing them deletes a duplicated surface rather than a capability. Same date, same deal: **reply here before 2026-09-30 if you call one.**

Note that `cloud-local-proxy` serves its own copy of all eleven routes at `…/lisapi/v1/lis/cloud-proxy/old-report/*`. This announcement is about trans v1's copy only; if you call cloud-proxy, nothing changes for you yet.

---

## Notes for Leo, not for Slack

- **Scope choice.** You asked for `downloadTestOrderPDF`. I added section 2 because the other ten are in the same removal in VP-18324, they are now backed by measurement rather than a code search, and announcing twice for one deletion invites a second round of "nobody told me". Delete section 2 if you would rather keep the notice narrow — the first section stands on its own.
- **One thing is asserted, not yet verified.** VP-18346 split the attribution labels so the old-report family gets its own `@operation:proxyOldReportCaller`. It is merged and deployed (trans v1 `ad5ab17`, live 21:00Z today), but no request has hit those routes since, so the new label has not been observed working. It does not affect anything in this announcement — the counts above come from the request logs and from the old label, both of which are solid — but I have not confirmed the split yet and will when a request lands.
- **The four probe hits** at 18:00Z and 19:00Z are mine: two verification runs, two requests each, each of which calls the old route on purpose to compare it against the new one. I attributed them by timing and count, and the attribution log agrees (2 requests per hour in exactly those two hours).
- **Date arithmetic.** One week from 2026-09-23 is 2026-09-30. Change both mentions if you post on a different day.
