---
name: emr-order-customer-resolution
description: How lis-backend-emr-v2 resolves an inbound HL7 order's customer from the ORC.12 NPI, and how to debug emr_code_not_found / orders resolving to the wrong customer. Use whenever working on emr-v2 order intake, bundle/shortcut mapping, "order went to the wrong customer", "emr_code_not_found", an NPI that maps to an unexpected customer, or anything touching ehr_integrations vs order_clients for order routing. Reach for this before assuming order_clients drives order routing — it does not anymore.
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

## Related
- emr-v2 makes parse failures terminal, so stuck orders do **not** auto-recover after you fix the mapping — they need a retry/rescan (VP-17120). Re-process the affected orders explicitly after the fix.
- Any prod change to integrations/bundles here goes through the prod-change-gate (branch first, verify on live not mock, bound the SQL scope to the specific NPI/customer).
