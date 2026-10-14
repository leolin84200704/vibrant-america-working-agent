Results storage retrieval now runs on trans (prod), 2026-10-14.

**What changed**
- trans v1 serves `POST /storage/records/samples/retrieval` (LIS-Sample's route ported verbatim onto the Phase B `lis_inventory` client; same path, 201, body and HS256 guard). PRs: #929 (stage_test), #930 (main, deployed efb5782).
- `lis-trans-config` (prod) gained `DATABASE_URL_LIS_INVENTORY_MASTER` (same value and pool budget as LIS-Sample).
- results-web ConfigMaps `lis-test-web-generation-config` (18:44Z) and `lis-test-web-config` (18:46Z): `SAMPLE_STORAGE_BASE_URL` = `http://lis-trans-service.default.svc.cluster.local:3146` (in-cluster, no trailing slash: trans has no path-normalising proxy, `//storage/...` is a 404), rolling restarts done. Rollback = previous value + restart.

**Verification**
- Shadow replay before the flip: staging 35/35 and prod 101/101 identical answers (incl. 60 real request bodies, a 500-id batch, deleted-only / suffix / unknown ids), watermark identical; trans p50 101 ms vs LIS-Sample 133 ms.
- After the flip: results generation cycle calling trans every minute with 201 (first at 18:46:00Z), `storage-seed-degraded` = 0, staff traffic on lis-test-web continuous through the rolling restart, no new error signatures (the restart-time error-level lines are the known winston-mislevelled Nest boot messages). LIS-Sample receives no cloud `lis.results` calls after 18:45Z.

**Remaining before Done**
- 30-day soak with the LIS-Sample route kept (cloud callers at zero; on-prem results pods still use their own config and account for ~3 calls/day until on-prem retires).
- results staging mirrors (`lis-test-web-staging-config`) to trans-st.
