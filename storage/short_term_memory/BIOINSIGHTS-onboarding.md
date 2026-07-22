---
id: BIOINSIGHTS-onboarding
type: stm
category: emr_integration
status: active
created: 2026-07-21
updated: '2026-07-21'
links:
- FHIR-ONDEMAND-RESULT
- INCIDENT-2604156666
- LBS-1541
- LBS-1656
- QH-1660
- QH-2257
- QH-2577
- QH-3752
- QH-4350
- QH-4352
- QH-4608
- QH-5840
- VP-14787
- VP-15279
- VP-15952
- VP-16014
- VP-16166
- VP-16175
- VP-16186
- VP-16193
- VP-16251
- VP-16271
- VP-16280
- VP-16329
- VP-16685
- VP-16720
- VP-16734
- VP-16765
- VP-16766
- VP-16784-87
- VP-16832
- VP-16881
- VP-16885
- VP-16934
- VP-16968
- VP-16987
- VP-17076
- VP-17117
- VP-17120
- VP-17136
- VP-17283
- VP-17286
- VP-17344
- VP-17385
- VP-17411
- VP-17475
- emr-integration
- fhir-api
- repos
tags:
- bioinsights
- sftp
- key-auth
- vendor-onboarding
summary: 'New EMR vendor BioInsights — first key-based (non-password) SFTP integration.
  Code shipped: emr-v2 PR #275 merged to main 2026-07-20 (branch feature/leo/bioinsights-sftp-key,
  no VP ticket yet): migration 20260720_add_sftp_private_key adds nullable sftp_private_key
  to ehr_vendors + ehr_integrations and private_key to emr_sftp_source; order fetch
  accepts key-only credential rows (VP-17385 drift check extended to privateKey);
  result push passes key through to connect. Migration must be applied MANUALLY to
  prod (lisportalprod2) and staging (192.168.60.11) BEFORE deploying the code (prod
  not Prisma-managed). Connection per vendor (Thomas): sftp.bioinsights.com:2022,
  user vibrant-wellness, ed25519 keypair (PPK v3 unencrypted at ~/Downloads/bioinsights_key.ppk;
  emr-v2 needs OpenSSH PEM — convert with puttygen). 2026-07-21 verified from local:
  auth OK, but account has ZERO perms (ls/stat/put all fail) — vendor-side provisioning
  incomplete. Migration verified applied prod+staging; PR #275 in both deployed images;
  33 existing password vendors unaffected; AKS pod egress to bioinsights:2022 OK.
  2026-07-21 email sent to Thomas (perms + dir layout + sample HL7). STATUS: waiting
  on vendor reply.'
jira_status: none
score: 0.63
---
















































# BioInsights EMR vendor onboarding (SFTP, key-based auth)

## Facts

### [2026-07-21 12:00]
- Vendor connection (from Thomas @ BioInsights, tested OK by company IT):
  - Host `sftp.bioinsights.com`, port `2022`, username `vibrant-wellness`
  - Auth = ed25519 keypair, comment `vibrant-wellness-bioinsights-sftp`
  - Private key: `~/Downloads/bioinsights_key.ppk` (PPK v3, UNENCRYPTED — should move out of Downloads into credential store)
  - Public key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF1/iaD2dcHdpj/WgGDC6MvRmMdqGa0oMjfixyQ/O45t`
- emr-v2 SFTP client wants `privateKey` as **OpenSSH PEM string** (`sftp-connection.service.ts`), NOT ppk. Convert: `puttygen x.ppk -O private-openssh -o x.pem` (brew install putty).
- Local connection test 2026-07-21: auth SUCCEEDS; `ls /` returns "Couldn't read directory: Failure" (chroot/perm); probed orders/results/inbound/outbound/in/out/upload/download/files/vibrant*/home — none exist. **Remote dir layout unknown.**

## Code state (done)
- `lis-backend-emr-v2` PR #275 MERGED to main 2026-07-20 (also in staging). Branch `feature/leo/bioinsights-sftp-key`. Commits:
  - `b6dc99d` migration `20260720_add_sftp_private_key`: ALTER ehr_vendors ADD sftp_private_key TEXT NULL; ehr_integrations ADD sftp_private_key; emr_sftp_source ADD private_key
  - `365e30b` order fetch: loadCredentialStores accepts password-OR-key rows; key carried through HostGroup into connect(); drift compare includes privateKey (names only, never values)
  - `517e396` result push: key pass-through in sftp.service
- No VP ticket exists for this onboarding (Jira text search 0 hits as of 2026-07-21).

### [2026-07-21 22:30] Verification pass (migration/deploy/regression)
- **Vendor account has ZERO permissions**: auth OK but ls/stat/cd/put ALL fail at root and every probed path (20+ naming conventions + write probe). Server-side provisioning incomplete — BLOCKED ON VENDOR (Thomas). IT's "tested OK" was auth-handshake only.
- **Migration applied on BOTH DBs**: prod (via AKS pod prisma, lis_emr) and staging (staging pod, root@lis_emr) both have ehr_vendors.sftp_private_key + ehr_integrations.sftp_private_key.
- **emr_sftp_source table does NOT exist in either prod or staging DB** — migration's 3rd ALTER inapplicable. Harmless: VP-17460 (merged after PR #275) removed the emr_sftp_source fallback from the fetch path; main reads ehr_vendors only via loadVendorCredentials. NOTE pre-existing landmine: auto-integrate integration-request.service.ts still queries prisma.emrSftpSource (would 1146 at runtime) — unrelated to BioInsights, not touched.
- **Deploy confirmed**: prod image 60fc05cd (= origin/main HEAD, merge PR #280) and staging image 17c5b70 BOTH contain PR #275 (verified via git merge-base --is-ancestor).
- **No regression risk to existing integrations**: prod ehr_vendors 33 rows with sftp_host — all 33 password, 0 key, 0 neither → password-OR-key change alters no existing row's behavior. 12h prod logs: order-fetch 0 errors (ticks normal), sftp 0 errors.
- **Egress OK**: prod AKS pod TCP-connects to sftp.bioinsights.com:2022 directly — no allowlist negotiation needed (unlike VP-17312 batch-5 vendors).

### [2026-07-21 23:00] Email sent to Thomas — WAITING ON VENDOR
- Leo sent the drafted email to Thomas @ BioInsights asking for: (1) account read/write permission provisioning (auth works, zero perms), (2) directory layout (orders pickup dir / results drop dir / archive convention), (3) sample HL7 order files for parsing + transformer-mapping assessment.
- Our side fully ready: PR #275 deployed prod+staging, migration applied, egress from AKS pod to sftp.bioinsights.com:2022 verified.
- NEXT ACTION when Thomas replies: re-run connectivity test (ls + put probe), inspect dir layout, review sample HL7 → decide transformer mapping + integration scope (order/result/bidirectional, which practices) → then gated ehr_vendors INSERT.

## Open items (go-live checklist)
1. BLOCKER: Thomas/BioInsights must provision account permissions (home dir readable/writable) + tell us directory layout (orders pickup dir, results drop dir).
2. Scope unclear: orders inbound only, results outbound only, or bidirectional? Which practices/clinics? (drives ehr_integrations + order_clients rows — order gate is order_clients per VP-16968)
3. DB rows to insert (GATED, prod change): ehr_vendors BIOINSIGHTS row (host/port/username + sftp_private_key PEM); ehr_integrations per practice.
4. Need sample HL7 files from vendor to decide transformer mapping needs.
5. Move/secure the private key (unencrypted in ~/Downloads); consider filing a VP ticket for tracking.
