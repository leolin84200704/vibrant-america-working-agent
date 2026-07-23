---
name: emr-order-customer-resolution
description: How lis-backend-emr-v2 resolves an inbound HL7 order's customer from the ORC.12 NPI, and how to debug/fix customer_not_found, emr_code_not_found, and orders resolving to the wrong customer. Use whenever working on emr-v2 order intake, bundle/shortcut mapping, "order went to the wrong customer", "customer_not_found" in hl7_file_input, "emr_code_not_found", an NPI that maps to an unexpected customer, or anything touching ehr_integrations vs order_clients for order routing. Includes the add-provider integration playbook (mirror practice peer + retry_num re-place). Reach for this before assuming order_clients drives order routing — it does not anymore.
---

# emr-v2 Order → Customer Resolution

The single most common wrong assumption here is that an order's customer comes from `order_clients`. It does **not** anymore (superseded ~VP-16968). Knowing the real path saves hours on routing bugs.

> Caveat: the call chain below was accurate as of 2026-06. emr-v2 prod is not Prisma-managed and the code moves — verify the current service/method names against the live code before asserting them in a ticket.

## The resolution path

An inbound HL7 order's customer is resolved from the **ORC.12 NPI**:

```
ORC.12 NPI
  → CustomerDetailFetcherService.fetchByNpi
  → gRPC getCustomerByNPINumber
  → resolveOrderingIntegration  (on ehr_integrations)
  → candidates[0].customer_id
```

`fetchById` also routes through `resolveOrderingIntegration`. **`order_clients` is not consulted for order routing.**

### How the winner is picked (`resolveOrderingIntegration`)
Among `ehr_integrations` rows for that NPI:
1. Filter: `status = 'LIVE'` AND `ordering_enabled = true`
2. Sort by `typeRank`: `FULL_INTEGRATION = 0`, `ORDER_ONLY = 1`, else `2`
3. Tie-break: `updated_at` DESC
4. Take `candidates[0].customer_id`

So: the most-recently-updated LIVE FULL integration for that NPI wins.

## The gotcha: one NPI, multiple LIVE integrations

If a single NPI has **more than one** LIVE + ordering `ehr_integrations` row (e.g. on two different customers), the winner is decided purely by typeRank then `updated_at` DESC. A custom bundle keyed on `${oldOrderTypeId},${customerId}` (order-mapping-cache) that is bound to a **different** customer than the winning integration → lookup miss → **`emr_code_not_found`**.

### Debug recipe for emr_code_not_found / wrong-customer
1. Find all `ehr_integrations` rows for the NPI where `status='LIVE'` and `ordering_enabled=true`.
2. Apply typeRank → `updated_at` DESC. The top row's `customer_id` is who the order actually resolves to.
3. Check which `customer_id` the relevant bundle/shortcut is bound to.
4. If they differ, that's the bug. Two fixes:
   - **Align the bundle** to the winning customer, or
   - **Deactivate the duplicate/stale integration** (set its status away from LIVE) so the NPI resolves to the intended customer.

### Worked example (2026-06-19)
NPI `1396844346` had LIVE integrations on customer `3057` (newer `updated_at`) and `4953`. Bundles `VACP149591/149592/126422` were on `4953`, but orders resolved to `3057` (newer wins) → stuck with `emr_code_not_found`. Resolved by setting the `3057` integration → PENDING so the NPI fell back to `4953`.

## customer_not_found fix playbook (add-provider integration)

`hl7_file_input.customer_not_found` (provider NAME recorded, sample_id null) almost always means: the provider has a VA account + NPI, but **zero `ehr_integrations` rows**, so `resolveOrderingIntegration` finds no LIVE+ordering candidate. Leo confirmed (2026-07-23) this is expected to recur — the fix is a routine add-provider integration. Worked examples: STM `HL7FAIL-20260722-MDHQ`, VP-16765, VP-16734.

1. **Identify the provider**: `customer_details` (192.168.60.3:3307 `vibrant_america_information`) by name from `customer_not_found` → customer_id, NPI, login. Clinic via `lis_core_v7._clinictocustomer` (A=clinic_id, B=customer_id) — never guess the clinic from the ticket.
2. **Find the practice peer**: existing LIVE row in `ehr_integrations` for the same practice (match the failing row's `sftpDir` against `sftp_result_path`/`sftp_ordering_path`, or by clinic_id). The peer is the template.
3. **INSERT `ehr_integrations`** mirroring the peer column-for-column, changing only: customer_id, customer_npi/effective_npi, msh06. Conventions: `msh06_receiving_facility = clinic_id` (2026-04+ policy; do NOT retro-align peers without vendor coordination), `integration_origin=NEW_INTEGRATION`, `report_option` follows the practice peer, contact = Leo, `requested_by` = ticket id or `customer_not_found-fix-{date}`. FULL_INTEGRATION also needs an **`order_clients`** row (name/NPI/practice/clinic/kits_options=0/emr_name/remote_folder_path). `sftp_folder_mapping` is practice-level — usually exists already; don't touch.
4. **Execution discipline**: single transaction + pre-check guards (no existing row for this customer/NPI; peer in expected LIVE/FULL state) + in-tx verify; dry-run (rollback) first, then `--commit`; 100% post-commit verify. Write via the emr-v2 app account — parse `.env` with `^DATABASE_URL=` anchored (the commented staging line bites bare substring matches).
5. **Re-place the order**: `UPDATE hl7_file_input SET retry_num = 3 WHERE id IN (...) AND parse_finished = 0` — customer_not_found is retryable (VP-17120); the owning pod's 15-min fetch cron re-parses from its retained local file. **This is the only correct re-order path**: the original HL7 content usually exists ONLY on that pod's local disk (`order_input` often null), so hand-crafting the order is impossible.
6. **Owning pod**: check `sftp_folder_mapping.pipeline_location` for the folder — `onprem` rows are retried by the on-prem pod. Pod names are ambiguous: the on-prem cluster runs a deployment named identically to the AKS one (`lis-emr-v2-deployment-prod`), so `last_update_pod_name` alone cannot tell you the cluster.
7. **Verify in core** (`lis_core_v7.sample` + `order_info`, ground truth — not the EMR mirror): sample created, correct customer_id + clinic_id, order isActive=1, and no duplicate samples for the same patient+customer.

## Related
- emr-v2 makes parse failures terminal only for non-retryable classes; customer_not_found and config-class failures keep `parse_finished=0` and auto-recover via the retry-rescan once `retry_num > 0` (VP-17120). For other stuck classes, re-process explicitly after the fix.
- Any prod change to integrations/bundles here goes through the prod-change-gate (branch first, verify on live not mock, bound the SQL scope to the specific NPI/customer).
