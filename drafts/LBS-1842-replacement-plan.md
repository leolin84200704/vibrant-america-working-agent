# LIS-Sample routes removed in VP-18480: replacement plan (LBS-1842)

Status: the 18 routes are restored by LIS-Sample #218 (master) / #219 (dev), a plain revert of 208861b / 26efad4.
Rule from here on: a route is removed only after (1) its replacement is live, (2) every code caller has moved,
(3) the old route shows zero calls for 14 days after the move.

Target home is trans v1 (LIS-transformer), per the VP-18480 decision. Every LIS-Sample route below is a thin
wrapper: the replacement is the same downstream call made from trans v1, exposed on the same path under
`/v1/lis/trans-service/samples/*`, so the frontend change is a base-URL switch.

| Route | What it actually does | Caller | Replacement (trans v1) | Family ticket |
|---|---|---|---|---|
| POST /patients/orders/hormone-qnr | Shipping gRPC `SendHormoneQnrEmail` | LIS-frontend ResendEmailDialog | same path -> Shipping gRPC | VP-18798 |
| POST /patients/orders/cardio-zoomer-qnr | Shipping gRPC `SendCardioZoomerQnrEmail` | LIS-frontend ResendEmailDialog | same path -> Shipping gRPC | VP-18798 |
| POST /patients/orders/nutriproz-skincare-qnr | Shipping gRPC `SendNutriSkQnrEmail` | LIS-frontend ResendEmailDialog, NutriprozFollowupQuestionnaireDialog | same path -> Shipping gRPC | VP-18798 |
| POST /patients/orders/disclosure-restricted-notif | Shipping gRPC `SendDisclosureRestrictedNotification` | LIS-frontend SampleStatusTable | same path -> Shipping gRPC | VP-18798 |
| POST /patients/complete-reports | HTTP GET to trans v1 `trans/ShareCompleteeport` | LIS-frontend ResendEmailDialog (Share Result to Patient) | frontend calls trans v1 directly (logic already lives there) | VP-18798 |
| GET /patients | Core gRPC `PatientService.GetPatient` | LIS-frontend SearchEntranceStore | same path -> Core gRPC | VP-18798 |
| GET /interaction-logs/:id/details | vibrant_tracking `service_call_records` read + Core `GetCustomerByIDs` | LIS-frontend SearchLogDialog | add to trans v1 `interaction-logs` controller | VP-18801 (Dev Complete, but this route was not ported) |
| POST /interaction-logs/resolution | updateMany on `service_call_records` + `interaction_call_records` | LIS-frontend InteractionLogStore | add to trans v1 `interaction-logs` controller | VP-18801 (Dev Complete, but this route was not ported) |
| POST /storage/records/batch/removal | lis_inventory `sample_storage_records` batch delete + outbox | LIS-frontend StoragePageStore | add to trans v1 `storage` controller | VP-18802 (Dev Complete, but this route was not ported) |
| PUT/DELETE /storage/racks/samples/tubes/:idx | lis_inventory `sample_storage_records` update/delete + outbox | none found in local repos | add to trans v1, or drop after org-wide search | VP-18802 (Dev Complete, not ported) |
| GET /notifications/active (+ POST/PATCH/DELETE /notifications) | Core gRPC `NotificationService` pass-through | vibrant-wellness-portal Notification.js (GET only) | same path -> Core gRPC | new (none of the nine family tickets covers it) |
| POST /record-management/transfer-all-orders, transfer-all-patients | Core gRPC `TransferAllOrders` / `TransferAllPatients` | none found in local repos | move with record management | VP-18800 |
| GET /customers | Shipping gRPC customer search | none found in local repos | drop after org-wide search | VP-18803 |

Per route, in order:
1. Add the route to trans v1 (same request/response contract; contract snapshot diff in the PR).
2. Switch the caller (LIS-frontend `samplePageRequest` base URL / vibrant-wellness-portal `PORTAL_NOTIFICATION`) and release.
3. Watch `caller_attribution` on LIS-Sample for the old route: 14 days at zero.
4. Org-wide GitHub code search for the path returns nothing outside LIS-Sample.
5. Announce in the LIS dev channel with the route list and date, then remove from LIS-Sample.

Gap found 2026-10-15: VP-18801 and VP-18802 ported their families to trans v1 (`src/sample/interaction-logs`, `src/sample/storage`)
after 208861b, so the five removed interaction-log/storage routes are missing there. VP-18803 (ingress rewrite of
`/v1/lis/samples/*` to trans) must not ship until they are added, or the frontend gets the same 404 again.

Open: the "none found" rows were searched in local clones only; run org-wide code search before treating them as callerless.
