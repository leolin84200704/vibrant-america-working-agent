# VP-18463 — announcement comment draft (post on VP-18463; also link from the Confluence retirement page 2697166874)

**Removal notice — 2026-10-14.** The last two in-use `/proxy/grpc` routes and the last `/proxy/old-report` route on trans v1 will be removed on **2026-10-14**, together with the ConfigMap keys that point at them:

- `GET /proxy/grpc/getKitStatus`
- `GET /proxy/grpc/getPatientTestsResult`
- `GET /proxy/old-report/downloadTestOrderPDF`

**Why now.** Their only caller, LIS-setting-consumer, is off them: `downloadTestOrderPDF` moved to `/trans/downloadTestOrderPDF` on 2026-09-22 (VP-18324), and the two gRPC lookups moved to the shipping / test-connect gRPC services directly on 2026-09-30 00:13Z (VP-18462). Caller attribution has been live on both route families since 2026-09-18/21, and it named that one caller only.

**Scope note.** The ten unused `/proxy/old-report/*` routes and the three dead `/proxy/grpc` routes are not part of this ticket any more — they are being removed under VP-18320 (widened 2026-09-23). This ticket is the three routes above plus keys.

**If you call any of these three, comment here before 2026-10-14** and the route stays until you have moved. Replacements: `/trans/downloadTestOrderPDF` (same PDF; add `clinic_id`), and for the two lookups the gRPC services directly — carry over the JWT-to-metadata construction (`createMetadataForCoresampleV2`) and the proto3 `packages` normalisation, as documented on VP-18320 and in LIS-transformer-v2 #629 / LIS-setting-consumer #179.

**Plan.** 2026-09-30 to 10-14: attribution logs on the three routes must read zero (my replay traffic on 09-30 00:03–00:12Z excluded). 2026-10-14: re-check, then one PR removing the routes and the keys; rollback = revert.
