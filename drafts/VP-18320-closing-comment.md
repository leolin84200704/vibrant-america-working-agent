# VP-18320 — closing comment (post on the ticket, then Done)

**Removed and deployed 2026-09-30.** All 13 routes are gone from trans v1 in both environments:

- LIS-transformer #847 → `main`, deployed to prod 00:5xZ (commit 9431720); #848 → `stage_test`, deployed to staging 00:4xZ (bacfeee).
- Removed: `/proxy/grpc/getTestStatus`, `getQuestionaireBySampleId`, `listTnpCode`; `/proxy/old-report/getRequisitionForm`, `GenerateBatchReqOrReportV2`, `GenerateOnlineZipDownloadV2`, `getOrderSummaryReportZip`, `GetSpecificReports`, `GenerateOnlineSummaryReport`, `GenerateProducctSummaryReport`, `GenerateProducctReport`, `checkIfPersonalizedReportCanBeCreated`, `oneClickPersonalizedReport`, plus the five DTOs only they used. `OldReportProxyService`, `ProxyService` (still used by `/trans/*`) and every env key stay.

**Evidence on the day (15-day window 09-15 → 09-30, per-request logs):** 0 requests on all 13 routes in prod. The only residue was on staging trans v1 — `getTestStatus` / `getQuestionaireBySampleId`, 31 calls each between 09-23 and 09-29 — from LIS-transformer-v2 staging still in http mode; that caller moved to direct gRPC (LIS-transformer-v2 #661) and its proxy keys were removed on 09-30 before this deploy. No objection was raised on the ticket.

**Verified after deploy:** in-cluster probe returns 404 on all 13 paths in prod and staging; `getKitStatus` and `getPatientTestsResult` still answer 200; 0 error-level log lines on the new pods; `/trans/*` traffic after the rollout 100% 2xx. Tests added: a supertest spec pins the 13 paths at 404 and `downloadTestOrderPDF` at the same streamed object.

**Config keys:** none of the keys that pointed at these 13 routes remain in any ConfigMap (removed under VP-18461 and VP-18466). The remaining `/proxy` routes and keys (`getKitStatus`, `getPatientTestsResult`, `downloadTestOrderPDF`) are VP-18463, removal notice posted for 2026-10-14.

Rollback, if ever needed: revert #847 / #848 and deploy.
