# IT Inquiry: locate a rogue lis-backend-emr-v2 instance hitting production

Prepared 2026-07-14, updated 2026-07-15 — **PRIORITY P1**. Send to IT / infra.
Goal: identify the machine running an unauthorized old copy of the order-fetch
service against production.

## 2026-07-15 UPDATE — escalating, now ~hourly, and it is INTERNAL

Live monitoring caught two fresh strands on 2026-07-15, roughly one hour apart,
and one gives a direct internal lead:

- **2026-07-15 16:04:14 UTC** — pulled `12604_071526.hl7` from **THM SFTP
  45.24.217.155** (this is Vibrant's OWN internal SFTP). Because the target is
  internal, IT can read **45.24.217.155's SFTP auth log** for which internal
  host authenticated as user `THM` and fetched `/Prod/Orders/12604_071526.hl7`
  at 16:04 UTC — this should pinpoint the machine directly.
- **2026-07-15 17:05:14 UTC** — pulled `order_354_1784134863_74.hl7` from
  **MDHQ 34.199.194.51:2210** (clinic risefunctionalmedicine).

The rogue's DB connections come from behind the office/on-prem NAT
**45.24.217.146** — same 45.24.217.x subnet as the internal SFTP it hit — so
**the machine is inside Vibrant's internal network**, not a home/remote laptop.
Cadence is ~hourly around :04–:05 past the hour, so it is also predictable
enough to watch live. Each firing strands a real patient order (5+ so far).

## What we're seeing

A second, unidentified instance of the EMR order-fetch service is polling the
**production** MySQL and pulling order files from vendor SFTP, racing the
legitimate Kubernetes pods. When it wins the race it writes the order file to
its own local `/tmp` (a path only OLD code used — current pods use
`/EMR_storage/...`), so the legitimate pod can't read the file and the order
gets stranded until it exhausts retries. It has stranded at least 3 real
orders since 2026-07-01 (most recent 2026-07-13). It runs pre-2026-06 code
with a production `.env` (DB + SFTP credentials that have not been rotated).

## Fingerprint of the rogue instance

- Connects to prod DB `lisportalprod2.mysql.database.azure.com` as user
  `lis_emr` (the app account).
- Its DB rows carry an EMPTY pod-name field (the real deployments inject the
  Kubernetes pod name; this one has none) and write `localDir=/tmp/hl7/...`.
- Makes outbound SFTP connections to vendor hosts, notably
  **MDHQ `34.199.194.51:2210`** and **`64.124.9.100`** (Follow That Patient).
- Activity is intermittent — roughly every few days, not continuous —
  suggesting a developer/test machine that is powered on occasionally, not a
  server.

## Concrete timestamps to correlate (UTC)

Two confirmed rogue fetches. Please check firewall / NAT / egress logs for an
**internal** host making an OUTBOUND connection to `34.199.194.51:2210`
(MDHQ SFTP) at or just before these times:

| UTC time | File fetched |
|---|---|
| 2026-07-13 20:06 | order_337_1783973082_9.hl7 (clinic risefunctionalmedicine) |
| 2026-07-13 19:04 | order_1465_1783969461_0.hl7 (clinic innatewellnessaz) |

Also useful: any internal host connecting to prod MySQL
`lisportalprod2.mysql.database.azure.com:3306` as `lis_emr` that is NOT one of
our Kubernetes nodes (AKS egress `20.14.29.219`) or the on-prem emr-v2 pod.

## From our side (DB view)

Prod DB `information_schema.PROCESSLIST` shows two source IPs for the app
account: `10.224.x.x` (AKS cloud pods, legitimate) and `45.24.217.146` (the
office/on-prem NAT egress). The rogue instance is almost certainly behind
`45.24.217.146` — from the DB it is indistinguishable from the legitimate
on-prem pod because they share that NAT IP. That's why we need the NAT/firewall
log to see the individual internal host behind it.

We have added live capture on our monitoring: the next time the rogue fetches,
we snapshot the DB connection list (with source ports) at that instant, which
should give you a port to match against the NAT table. We'll forward it when it
fires.

## Ask (P1)

1. **Fastest path**: read `45.24.217.155` SFTP auth log for the internal host
   that logged in as user `THM` and pulled `/Prod/Orders/12604_071526.hl7` at
   **2026-07-15 16:04:14 UTC**. That host is the rogue instance.
2. Cross-check NAT/firewall egress to `34.199.194.51:2210` (MDHQ) at
   **2026-07-15 17:05:14 UTC** and to `64.124.9.100` on prior dates.
3. Once identified: stop that instance and tell us whose machine it is.
4. Rotate the prod DB (`lis_emr`) + vendor SFTP credentials afterward — the
   rogue holds an old copy of them.

## Why this matters

Every time it wins a fetch race, a real patient order is silently stranded
(no sample created) until someone manually rescues it. It's also running
untrusted old code against production data with unrotated credentials.
