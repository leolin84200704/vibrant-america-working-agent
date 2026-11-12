# VP-19305 - Engineering input for the EMR integration SOP and HL7/SFTP spec

Answers to the 39 questions in VP-19305 comment 200608, plus the materials.
Code answers were checked against lis-backend-emr-v2 main (69b55d0). Data answers were checked against prod `lis_emr` and `lis_core_v7` on 2026-11-11 and 2026-11-12.
No patient data in this file or in the attachments. Sample messages use placeholder values.

## Materials (separate files, same folder)

| File | For |
| --- | --- |
| `materials/VP-19305_sample-order-ORM.hl7` | A2: sample order |
| `materials/VP-19305_sample-result-ORU.hl7` | A2: sample result (PDF payload truncated) |
| `materials/VP-19305_field-list.csv` | A3, A4, A6: order and result fields |
| `materials/VP-19305_test-code-list.csv` | A14: orderable test codes (269) |
| `materials/VP-19305_vendor-config-export.csv` | B6: one row per vendor, no credentials |
| `materials/VP-19305_vendor-practices-live.csv` | B6: one row per vendor and practice |
| `materials/VP-19305_B18_files-sent-to-connection.sql` | B18: files sent to a connection over a date range |
| `materials/VP-19305_B2_customer-ehr-integrations-page.png` | B2: the practice's integration page |

There is no ACK sample because we do not send or read ACKs.

## AI questions (21)

Answered from the EMR service code; each has a "Where:" line.

### A1
- Results: HL7 v2 ORU^R01. MSH-12 comes from the integration's `hl7_version`. The default for integrations created on the Website is "2.3".
- Orders: most vendors send ORM^O01. OML^O21 is also parsed.
- ACK: none. We do not send or expect an ACK/MSA in either direction. Delivery is a plain SFTP file drop.

Where: src/modules/hl7/services/hl7-encoder.service.ts (encode, buildMSH); integration-request.service.ts:303 (hl7_version default)

### A3
See the attached field list. In short:
- Order (inbound): PID-3/PID-2 patient id; PID-5 name; PID-7 DOB; PID-8 sex; PID-11 address; PID-13 phone; PID-20.1 email (non-standard); ORC-12 ordering provider NPI (OBR-16 fallback); practice ID (see A4); OBR-4.1 test code; OBR-7 collection date; IN1-2.1 billing option; optional ZKD kit delivery.
- We identify the vendor by the SFTP folder the file came from, not by MSH-5.
- Result (outbound): MSH-6 receiving facility (set per integration); PID echoes the order's patient id (Nextech: PID-2); ORC-1 = RE; ORC-2/OBR-2 placer order number; OBR-3 our accession; ORC-5, OBR-25 and OBX-11 = F; OBX result rows; the last OBX holds the PDF as Base64 (`^AP^^Base64^`).

Where: hl7-order-processing/services/parser.service.ts; hl7/services/hl7-encoder.service.ts; sftp_folder_mapping (vendor by folder)

### A4
- Ordering provider NPI: ORC-12.1, with OBR-16 as fallback. This is the main key that picks the integration. Exception: FOLLOWTHATPATIENT sends our customer id in ORC-12, not an NPI.
- Practice ID: the numeric Vibrant practice id. The field is configured per vendor in `ehr_vendors.order_practice_id_field`, and `order_practice_id_required` says whether it is mandatory.
  - ORC-17.1 is read for MDHQ (Cerbo), FOLLOWTHATPATIENT and THM (Gundry).
  - Nextech's practice id is read from MSH-4.
  - Other vendors send no practice id.
- Do not rely on MSH-4/MSH-6 for practice in general. Their meaning differs per vendor.

Where: parser.service.ts:240 (extractPracticeId); services/practice-id-field.ts:54; hl7-order.processor.ts:218

### A5
- A returning patient is matched on exact first name, last name and sex plus DOB. The search covers patients of the ordering provider and of the other providers in the same practice. The EMR patient id is stored on the sample but not used for matching.
- On an existing patient, an order can change only phone (PID-13) and email (PID-20), and only when the new value is not blank and differs. The address on the order is used for that order only.
- If a vendor sends the practice's office phone or email instead of the patient's, those patients end up with the practice's contact details.

Where: hl7-order-processing/services/patient-detail-parser.service.ts; grpc/services/grpc-client-v2.service.ts:945; core-v2 patient service (matching rule)

### A6
- Field: IN1-2.1.
- "C" (uppercase, exact) bills the provider's card on file.
- Any other value, or no IN1 segment, means the patient pays later. The patient gets an email with a payment link.
- There is no per-integration default. A failed card charge does not stop the order; the reason is stored on the order.

Where: parser.service.ts:799 (chargeMethodFromIn1)

### A8
- Each vendor has an order folder and a result folder. Result folders are on the vendor row. The order folders we poll are listed in `sftp_folder_mapping`. Cerbo has one order folder per practice; other vendors have one.
- Orders: we read only files ending in .hl7 / .HL7. A file is read once per path and file name, so a resend needs a new file name.
- Results: `{accession}.hl7`. Per-report delivery uses `{accession}_{report short name}.hl7`. Cerbo Total Tox uses `{accession}_TTB.hl7`. Order Summary and report PDFs, when enabled, are written next to the HL7 with the same base name.

Where: hl7-order-fetch.service.ts:95 (HL7_FILE_EXTENSIONS); result-generation.service.ts:367; result-attachment.service.ts:128,350

### A9
- Order folders are polled every 15 minutes.
- After pickup, the file is moved to `{order folder}/archive` on the vendor's SFTP. The folder name is fixed.
- Result files: we write them and never delete them. The partner removes them after pickup.

Where: hl7-order-fetch.service.ts:117 (cron '0 */15 * * * *'), :26-30, :103-109

### A11
1. The cron picks up the file, saves it in `hl7_file_input`, and queues it.
2. The worker parses it and finds the integration from the NPI (ORC-12), and from the practice id when the vendor sends one.
3. It checks vendor, practice, test codes, kit delivery and payment.
4. It places the order through the Place Order API, which creates the order and sample in LIS. The order then shows in the Portal under that provider and practice.
5. If enabled, the Order Summary PDF is written back to the vendor's SFTP right away.
6. Status and errors are written back to `hl7_file_input`.

Where: hl7-order-fetch.service.ts; processors/hl7-order.processor.ts; services/customer-detail-fetcher.service.ts; services/order-forms-delivery.service.ts

### A12
- customer_not_found: no LIVE ordering integration for that NPI, or for that NPI at that practice. The order goes to quarantine, is retried, and expires.
- vendor_mismatch (live since Oct 21): the vendor that sent the file is not a vendor this provider or practice has connected. Rejected, and `last_error` lists the provider's integrations.
- practice_not_found (live since Nov 10): the vendor sent a practice id the provider is not set up at. Held and retried.
- practice_id_missing: the vendor requires a practice id and it is missing or invalid. Held and retried.
- provider_not_in_clinic: terminal failure.
- emr_code_not_found: a test code we can't map. Fails.
- kit_delivery_rejected: bad ZKD value, more than one ZKD, kit and payment conflict, or bad address. Terminal failure.
- Parse errors (bad dates, empty OBR): fail.

Every failure is in `hl7_file_input.last_error` and raises a Sentry alert to #emr-orders-bot.

Where: processors/hl7-order.processor.ts:309,344,365,447; quarantine/quarantine.service.ts; services/kit-delivery.service.ts

### A13
No. The EMR gets nothing back for a failed order (no ACK/NAK). On our side: `hl7_file_input` (status, last_error), the quarantine table, and the Sentry alert in #emr-orders-bot.
ChARM is the one exception on the result side: results to ChARM are also sent by HTTP POST, and that call returns an acknowledgement.

### A14
- The test code in OBR-4.1 is matched to our catalog codes: single tests, official bundles, and practice-created custom panels, which have their own codes. The mapping is cached and refreshed every 30 minutes.
- There is no partner-facing API for the code list. Partners get a static list; the current one is attached (`VP-19305_test-code-list.csv`).

Where: services/order-mapping-cache.service.ts:50

### A15
- ZKD segment (PH-947): `ZKD|1|<blood>|<nonblood>`, values SHIP_TO_PATIENT or SUPPLIED_BY_OFFICE. Empty means the integration default is used. No partner has sent ZKD in prod yet.
- Practice id: see A4 for which vendors send it and where.
- PID-2 EMR patient id: Nextech. We echo it back on results.
- IN1-2.1 billing option: optional. If missing, the patient pays later.

Where: docs/hl7-order-spec-kit-delivery.md; services/kit-delivery.service.ts

### A16
- When: a result is sent when LIS reports that a report is finished. Per integration, `result_push_level` decides whether we send once for the whole order, once per report, or once per report group (at most twice per order).
- Corrected reports: a redrawn report triggers a new delivery automatically, and a manual resend sends the current content. Both go out marked Final (ORC-1 = RE, ORC-5 / OBR-25 / OBX-11 = F). We never mark a correction.
- Canceled orders: we send nothing when an order is canceled. There is no cancel message, and the result path does not check whether the order was canceled. A result that was sent before the cancel stays with the partner. If a report finishes after the cancel, it is still sent.
- Prod check (last 180 days): 9 samples whose order is now canceled had results delivered. 7 were delivered before the cancel, and 2 were delivered after it.

Where: kafka/services/kafka-report-finished-listener.service.ts:334 (report_finished / redraw_report_finished), :436; hl7-encoder.service.ts:294-312, :377; prod lis_emr.result_transmission_records joined to lis_core_v7.order_info (order_status = order_canceled_order), checked 2026-11-12

### A17
- The PDF is embedded in the last OBX as Base64 (`OBX-5 = ^AP^^Base64^...`). Large PDFs are compressed to stay under vendor size limits (Cerbo: under 15 MB per message).
- Options per integration: one PDF for the whole order (default); one HL7 and PDF per report; Classic or Personalized style (`report_option`). Who uses which is in B7.
- Order Summary PDF: written as a separate file when the order arrives. Only FOLLOWTHATPATIENT has it on.

Where: hl7-encoder.service.ts:676-691; result/services/file-size-validation.service.ts; result-attachment.service.ts

### A18
- More than one EMR integration: each LIVE integration with results on for that provider gets a copy. If the provider works at several practices, the integration for the practice the order was placed under is used first.
- Portal orders: results still go to the provider's EMR integration for that practice, if one is LIVE with results on. Where the order came from doesn't matter.
- Practice-wide integrations are used only for samples of that practice. A provider's own integration wins over the practice-wide one.

Where: kafka-report-finished-listener.service.ts:436 (findEligibleResultIntegrations); customer-detail-fetcher.service.ts:548

### B7
- One PDF per report: only Maristany Medical (Cerbo). Resilience Code (Cerbo) gets results per report group and holds GUT5 back. Set by `result_push_level` and the split flag on `ehr_integrations`.
- Total Tox combined message: Cerbo only.
- Order Summary PDF on order arrival: FOLLOWTHATPATIENT only. No vendor has the "with result" Order Summary turned on.
- Classic or Personalized: `report_option` on the integration.
- Result folder must contain only .hl7 files: Cerbo/MDHQ.
- PID-2 and per-test OBR-2 echo: Nextech only.
- Results also sent by HTTP POST: ChARM only.

All of these are set on the integration or vendor row; see the B6 export.

Where: result-attachment.service.ts; result-generation.service.ts; hl7-encoder.service.ts

### B13
- Add a provider: the clinic admin adds the provider to the practice's integration on the Website. This creates a pending row that the Sales director approves in the Unimod panel.
- Remove a provider: suspend that provider's integration. Removing a provider from the clinic also deactivates their EMR integration automatically.
- Practice-wide create, suspend and withdraw exist in the API but have no screen. Integration statuses in use are LIVE, PENDING and REJECTED.

Where: auto-integrate/services/integration-request.service.ts:1514-1619 (deactivateOne); practice integration API

### B14
- The practice can stop the old integration itself with the Disconnect link on the Website page (B2 screenshot). Engineering can do the same by deactivating the old vendor's integration rows for that practice. Either way the rows become REJECTED, and result delivery only uses LIVE rows, so results stop.
- The old vendor's order folder is still polled. Polling is controlled only by `sftp_folder_mapping`, so turning off integrations or the vendor row does not stop it.

Where: integration-request.service.ts:1619 (deactivateOne); hl7-order-fetch.service.ts:204 (folders from sftp_folder_mapping where use_v2_pipeline = true)

### B15
Use the manual resend: `POST /result/generate/:sampleId`, or the batch endpoint. Every resend produces a new delivery. There is no duplicate check, so resend only when needed.

Where: result/controllers/result.controller.ts:133,159

### B16
- One practice leaves: the practice clicks Disconnect on the Website, or engineering suspends or withdraws the integration through the API (practice-wide suspend covers every active row for that practice and vendor). Results stop.
- A vendor leaves: suspend all its integration rows so results stop. To stop picking up its orders, engineering sets `use_v2_pipeline` to false on its `sftp_folder_mapping` rows. Deactivating the vendor row alone does not stop polling.

Where: integration-request.service.ts:1586,1619; hl7-order-fetch.service.ts:204

### B17
- One practice: suspend that practice's integration for the vendor. It takes effect on the next delivery, with no restart.
- The whole connection: suspend all integration rows for the vendor to stop results, and turn off its `sftp_folder_mapping` rows to stop order pickup.
- Neither has a screen. Both are API or database changes by engineering.

Where: integration-request.service.ts; hl7-order-fetch.service.ts:204

## Leo questions (18)

Answered from how things work in practice, checked against prod data where possible.

### A2
Attached: `VP-19305_sample-order-ORM.hl7` and `VP-19305_sample-result-ORU.hl7`. Both use placeholder data and follow the field positions the code reads and writes. The PDF in the result is truncated.
There is no ACK sample. We do not send ACKs and do not read them.

### A7
Both. Many vendors put files on an SFTP server we host:
- Our server 45.24.217.155: ChARM, eClinicalWorks, OptiMantra, PraxisEMR, HealthMatters, THM (Gundry), YHL, GLO, Unprescribed, Aprima, Meditab, NICHOLS, ZymeBalanz.
- Our server 45.24.217.150 (port 2222): Practice Fusion.
- Vendor-hosted: 64.124.9.100 (Breathermae, FollowThatPatient, DocVilla on separate ports), Cerbo/MDHQ, Power2Practice, Athena, Elation, OptimalDX, Nextech, BioInsights, Greenway, Harris, Health Fusion, INSYNC, Marqi, Cascades.

See the `sftp_host` column in `VP-19305_vendor-config-export.csv`.

### A10
We need from the partner: host, port, username, and either a password or an SSH private key; the order folder and the result folder.
Where it is stored: `lis_emr.ehr_vendors`, one row per vendor (host, port, user, password or private key, folders). Credentials sit in that table as plain text. A practice-level override exists on `ehr_integrations` but is rarely used.
The order folders we poll are in a separate table, `lis_emr.sftp_folder_mapping`.
There is no screen for vendor or folder setup. Engineering edits the database.

### A19
- There is no staging SFTP for partners. Our staging service points at our production SFTP server, so it cannot be used for partner tests either.
- Partners test in production. The test order goes under the integration's own provider account.
- If there is no provider account to test with, use our test provider: customer 999997 at practice 10136 ("Vibrant IT3 Practice 1233"), NPI 1234567893. It exists on staging and in production.
- Test patient name: TEST^ZZZTEST.
- To avoid a charge, leave IN1 out or send anything other than "C". No card is charged and the patient gets a pay-later email. A test patient with no email gets nothing.
- A test order has no physical sample. To send a test result back, ops have to receive the sample manually and release a result.
- Never place test orders on another practice's account. That is how the JAG incident happened.

### A20
Before go-live:
1. The practice created the integration on the Website, it was approved, and its practice and NPIs match the practice that asked for it.
2. The vendor's SFTP connects, and the order folder is in `sftp_folder_mapping`.
3. A test order (A19) showed up under the right practice and provider.
4. A test result reached the vendor's result folder, and the vendor confirmed they can match it to the order.
5. Report option (Classic or Personalized), kit delivery and billing match what the practice wants.

### B1
From the vendor: SFTP host, port, user, password or key, the order and result folders, a sample order file, and which field carries the practice id (if any).
From the practice: Vibrant practice id, providers' names and NPIs, report option (Classic or Personalized, one PDF or one per report), kit delivery default, billing (card on file or patient pays).

### B2
- The practice requests it on https://intelligence.vibrant-wellness.com/my-practice/practice-setting/third-party-integrations . The same page is embedded in the provider portal at https://www.vibrant-america.com/lis/patientpage/#/setting/third-party-integrations . The card is shown only to accounts in the auto-EMR-integration beta.
- The Sales director reviews and approves it in the Unimod panel, page VA Portal > EHR Auto Integration (route /Portal/EHRAutoIntegration). Accounts with the UNIMOD-EMR-ONLY permission see only this page.
- Data: `lis_emr.ehr_integrations`, one row per provider per practice per vendor. Vendor settings: `lis_emr.ehr_vendors`. Order folders: `lis_emr.sftp_folder_mapping`.
- No screen exists for vendor settings, order folders, or suspend. Those are database or API changes by engineering.
- Screenshot of the practice page attached: `VP-19305_B2_customer-ehr-integrations-page.png` (test account 999997). Each integration shows its request id, its status, and a Disconnect link. No screenshot of the approval page.

### B3
1. New vendor only: engineering adds the vendor row and the order folder.
2. The practice requests the integration on the Website.
3. The Sales director reviews and approves the request in the Unimod panel (EHR Auto Integration).
4. The vendor sends a test order; we confirm it landed under the right practice; we send a test result.
5. Go live.

### B4
Before the first real order:
- In EHR Auto Integration, check that the practice id and NPIs on the request match the practice that asked. Do not link a vendor to a practice because a vendor email or another ticket names it.
- Place a test order (A19) and confirm it lands under that practice.
- Since Oct 21, an order is rejected if the provider has not connected that vendor (vendor_mismatch). For vendors that send a practice id, an order for a practice the provider is not set up at is held (practice_not_found).

### B5
See A19: use the integration's own provider account (or test provider 999997), patient TEST^ZZZTEST, no IN1 "C". Ops release the result manually.

### B6
Attached:
- `VP-19305_vendor-config-export.csv`: one row per vendor (host, port, login type, folders, special settings, number of live practices and polled order folders). No credentials.
- `VP-19305_vendor-practices-live.csv`: one row per vendor and practice, with report option, push level, kit delivery and overrides.

### B8
Not sure. Engineering has no vendor contact list, and `ehr_vendors.support_email` / `support_phone` are empty for every vendor. Support does not receive vendor emails either; the CAMs forward them.
Contacts found in past email threads:
- Nextech: j.marshall@nextech.com
- devcom (BioInsights): olena.momotko@devcom.com
- ChARM (MedicalMine): lab-requests@medicalmine.com
- Cerbo: support@cer.bo

Some vendors take requests only through a ticket form on their website. For other vendors, ask the CAMs. The 2025 vendor IP whitelist work may also list contacts (Confluence page "Whitelist IPs").

### B9
Look up the file in `lis_emr.hl7_file_input` by file name, or by vendor (`emr_service`) and date.
- `sample_id` filled: the order was placed.
- `last_error` filled: it was rejected or held, and the text says why (see B11).
- Not in the table: we never picked it up. Usual causes: wrong folder, the name does not end in .hl7, or the same file name was used before.

Every failure also raises an alert in #emr-orders-bot.

### B10
Look up `lis_emr.result_transmission_records` by `sample_id`:
- `transmission_status` = TRANSMITTED, with `file_name`, `sftp_remote_path` and `transmission_completed_at`.
- TRANSMISSION_ERROR: `error_message` says why.

`generated_hl7_content` holds the HL7 text without the PDF. The full file sent is kept on the emr-v2 pod at `file_path`.
"Transmitted" means the file reached the vendor's folder. It does not mean the vendor imported it. Most vendors remove the file after pickup, so an empty folder is normal.

### B11
Last 90 days, orders (688 files, 654 placed):
1. Unknown or retired test code (`error_codes=...`, 18): the vendor's menu has a code we don't have or have retired. Fix: the vendor sends a valid code (test code list), or we add the code. Retired codes never place.
2. Our own service errors (`parse failed: ...`, 13): a downstream service was down. Fix: engineering retries after it is back.
3. Provider not connected (`customer_not_found=<provider name>`, 11): the provider has no live integration for that vendor. Fix: the practice adds the provider on the Website. Once approved, the order is retried automatically.
4. Wrong practice (`practice_not_found=<NPI>@<practice id>`, 5, all since Nov 10): the vendor sent a practice id the provider is not set up at. Fix: add the provider at that practice, or the vendor corrects the practice id.
5. Vendor mismatch (`vendor_mismatch`, 2): the provider is connected through a different vendor. Fix: check which EMR the practice uses.
6. Order not created at the last step (`finalize returned no sampleId`, 2): one had billing "C" with no card on file (fix: the practice adds a card). The other gave no reason and needs engineering.

Results (90 days): 37 delivery failures, almost all "SFTP upload failed" after retries. Fix: the vendor fixes their server, then we resend (B15).

### B12
Support could check these alone with read access to `hl7_file_input` and `result_transmission_records` (a simple lookup screen would do):
- B9: was the order received, and why it failed.
- B10: was the result delivered.
- B11 #3, #4, #5: they can tell the practice what to fix on the Website without engineering.

Code problems (#1) and service errors (#2) still need engineering.

### B18
Attached: `VP-19305_B18_files-sent-to-connection.sql`. Inputs are vendor id and a date range. Run it on lis_emr.
Re-checked on 2026-11-11: with BioInsights (vendor 46) and 2026-07-29 to 2026-10-13 it returns the JAG list, 204 rows for 200 samples.

### B19
1. No ACK in either direction. A failed order is invisible to the EMR.
2. Corrected reports go out as Final. We never mark a correction.
3. Canceled orders are not communicated. A result can still be sent after the order is canceled (A16).
4. A resend has no duplicate check.
5. The vendor "test SFTP" endpoint only tries the password, so key-only vendors (BioInsights) always fail the test.
6. SFTP passwords and private keys are stored as plain text in `ehr_vendors`.
7. 179 live integration rows have no vendor.
8. A practice can overwrite a patient's phone and email when it sends its own office contact in PID-13 / PID-20.
9. Turning off an integration or a vendor does not stop polling the vendor's order folder. That is the separate `sftp_folder_mapping` table.
10. Suspend has no screen. It is an API call only.
