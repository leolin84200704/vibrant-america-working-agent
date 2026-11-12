# VP-19305 - Answers (DRAFT for Leo review)

Source: questions in VP-19305 comment 200608. Code answers checked against lis-backend-emr-v2 origin/main (69b55d0, 2026-11-11).
Items marked [Leo] are drafted from past tickets and need Leo's check. No patient data in this file.

## Part A

### A1
- Results: HL7 v2 ORU^R01. MSH-12 comes from the integration's `hl7_version` (default "2.3" for self-service integrations).
- Orders: ORM^O01 from most vendors. OML^O21 is also parsed.
- ACK: none. We do not send or expect an ACK/MSA in either direction. Delivery is a plain SFTP file drop.
Where: src/modules/hl7/services/hl7-encoder.service.ts (encode, buildMSH); integration-request.service.ts:303 (hl7_version default)

### A2 [Leo]
Samples attached: de-identified order (ORM), de-identified result (ORU, PDF payload truncated). No ACK, because we don't send one.

### A3
See the attached field list. In short:
- Order (inbound): MSH-5 vendor code; PID-3/PID-2 patient id; PID-5 name; PID-7 DOB; PID-8 sex; PID-11 address; PID-13 phone; PID-20.1 email (non-standard); ORC-12 ordering provider NPI (OBR-16 fallback); ORC-17.1 practice ID; OBR-4.1 test code; OBR-7 collection date; IN1-2.1 billing option; optional ZKD kit delivery.
- Result (outbound): MSH-6 receiving facility (per integration); PID echoes the order's patient id (Nextech: PID-2); ORC-2/OBR-2 placer order number; OBR-3 our accession; OBR-25 = F; ORC-5 = F; OBX result rows; last OBX = the PDF, Base64 (`^AP^^Base64^`).
Where: hl7-order-processing/services/parser.service.ts; hl7/services/hl7-encoder.service.ts

### A4
- Ordering provider NPI: ORC-12.1 (falls back to OBR-16). This is the main key that picks the integration.
- Practice ID: ORC-17.1, the numeric Vibrant practice id. Which field is read is configured per vendor in `ehr_vendors.order_practice_id_field`, and whether it is mandatory in `order_practice_id_required`. Today ORC.17 is enabled for FOLLOWTHATPATIENT, THM (Gundry), NEXTECH and MDHQ (Cerbo), all with required=0.
- Do not use MSH-4/MSH-6 for practice. Their meaning differs per vendor.
Where: parser.service.ts:240 (extractPracticeId); services/practice-id-field.ts:54; hl7-order.processor.ts:218

### A5
- Patient matching is done by the core patient service from name + DOB + sex within the customer (provider). The EMR patient id (PID-2) is stored on the sample, not used for matching. [verify in core before publishing]
- An order can update the patient's contact data: email (PID-20.1) and phone (PID-13.1) are written back through updateContactIfChanged. The address on the order is used as the order's shipping snapshot.
- Note: if a vendor sends the practice's phone/email instead of the patient's, every patient of that practice ends up with the practice contact.
Where: hl7-order-processing/services/patient-detail-parser.service.ts; grpc/services/grpc-client-v2.service.ts:945

### A6
- Field: IN1-2.1.
- "C" (uppercase, exact) = bill the provider's card on file (customerPay).
- Any other value, or no IN1 segment = patient pay later: the patient gets an email with a payment link.
- There is no per-integration default. A failed card charge does not stop the order; the reason is stored on the order.
Where: parser.service.ts:799 (chargeMethodFromIn1)

### A7 [Leo]
Usually the EMR vendor hosts the SFTP and we connect to it. [Leo: list any partner on a server we host, if any.]

### A8
- Each integration has an order path and a result path on the vendor's SFTP (stored on the integration / vendor row; paths end with "/").
- Orders: we read only files ending in .hl7 / .HL7 from the order folder. A file is read once per path+filename; a resend needs a new filename.
- Results: `{accession}.hl7`. Per-report delivery uses `{accession}_{report short name}.hl7`; Cerbo Total Tox uses `{accession}_TTB.hl7`. Order Summary / report PDFs (when enabled) are written next to the HL7 with the same base name.
Where: hl7-order-fetch.service.ts:95 (HL7_FILE_EXTENSIONS); result-generation.service.ts:367; result-attachment.service.ts:128,350

### A9
- Order folders are polled every 15 minutes.
- After pickup the file is moved to `{order folder}/archive` on the vendor SFTP (the folder name is fixed).
- Result files: we write and never delete. The partner removes them after pickup.
Where: hl7-order-fetch.service.ts:117 (cron '0 */15 * * * *'), :26-30, :103-109

### A10 [Leo]
We need: host, port, username, and a password or an SSH private key (ed25519 key preferred), plus the order and result folder paths and the vendor code they will send in MSH-5. Credentials are stored per vendor in `ehr_vendors` (secrets in Key Vault). Known gap: the "test connection" button only uses the password, so key-only vendors show a failed test even when transfer works.

### A11
1. Cron picks up the file, saves it in `hl7_file_input`, and queues it.
2. The worker parses it and finds the integration from the NPI (ORC-12), and the practice (ORC-17) when the vendor sends one.
3. It checks vendor, practice, test codes, kit delivery and payment.
4. It places the order through the Place Order API (order-management), which creates the order/sample in LIS. It then shows in the Portal under that provider and practice.
5. If enabled, the Order Summary PDF is written back to the vendor's SFTP right away.
6. Status and errors are written back to `hl7_file_input`.
Where: hl7-order-fetch.service.ts; processors/hl7-order.processor.ts; services/customer-detail-fetcher.service.ts; services/order-forms-delivery.service.ts

### A12
- customer_not_found: no LIVE ordering integration for that NPI (or for that NPI at that practice). The order goes to quarantine, is retried, and expires.
- vendor_mismatch (live since Oct 21): the vendor that sent the file is not a vendor this provider/practice has connected. Rejected with the list of the provider's integrations in last_error.
- practice_id_missing: the vendor requires a practice ID and it is missing or invalid. Held and retryable.
- emr_code_not_found: a test code we can't map. Fails.
- kit_delivery_rejected: bad ZKD value, more than one ZKD, kit/payment conflict, or bad address. Terminal failure.
- Parse errors (bad dates, empty OBR): fail.
Every failure is in `hl7_file_input.last_error` and raises a Sentry alert to #emr-orders-bot.
Where: processors/hl7-order.processor.ts:309,344,365,447; quarantine/quarantine.service.ts; services/kit-delivery.service.ts

### A13
No. The EMR gets nothing back for a failed order (no ACK/NAK). On our side: `hl7_file_input` (status, last_error), the quarantine table, and the Sentry alert in #emr-orders-bot.

### A14
- The test code in OBR-4.1 is matched to our catalog codes (single tests, official bundles, and practice-created custom panels, which have their own codes). The mapping is cached and refreshed every 30 minutes.
- There is no partner-facing API for the code list. Partners get a static code list file.
Where: services/order-mapping-cache.service.ts:50

### A15
- ZKD segment (PH-947): `ZKD|1|<blood>|<nonblood>`, values SHIP_TO_PATIENT or SUPPLIED_BY_OFFICE. Empty means the integration default is used. No partner has sent ZKD in prod yet.
- ORC-17.1 practice ID: FOLLOWTHATPATIENT sends it today; Gundry and others are starting.
- PID-2 EMR patient id: Nextech; echoed back on results.
- IN1-2.1 billing option: optional; if missing, the patient pays later.
Where: docs/hl7-order-spec-kit-delivery.md; services/kit-delivery.service.ts

### A16
- A result is sent when a report is finished. Partial delivery is configured per integration (`result_push_level`): whole order, per report, or per report group (the order is sent at most twice).
- Corrected reports: a manual or automatic resend sends the new content, but the message is still marked Final (OBR-25 = F). We don't mark corrections.
- Canceled orders: no result message is sent.
Where: kafka/services/kafka-report-finished-listener.service.ts:436; hl7-encoder.service.ts:377

### A17
- The PDF is embedded in the last OBX as Base64 (`OBX-5 = ^AP^^Base64^...`). Large PDFs are compressed to stay under vendor size limits (Cerbo: under 15 MB per message).
- Options per integration: one PDF for the whole order (default); one HL7 + PDF per report (split); Classic or Personalized style (`report_option`); Order Summary PDF written as a separate file when the order arrives.
Where: hl7-encoder.service.ts:676-691; result/services/file-size-validation.service.ts; result-attachment.service.ts

### A18
- More than one EMR integration: each LIVE integration with results on for that provider gets a copy. If the provider works at several practices, the integration for the practice the order was placed under is used first.
- Portal orders: results still go to the provider's EMR integration, if one is LIVE with results on, for that practice. Where the order came from doesn't matter.
- Practice-wide integrations are used only for samples of that practice. A provider's own integration wins over the practice-wide one.
Where: kafka-report-finished-listener.service.ts:436 (findEligibleResultIntegrations); customer-detail-fetcher.service.ts:548

### A19 [Leo]
Staging exists, but we don't give partners a staging SFTP today. Partners test in prod with a validation order (test code TEST^ZZZTEST) on a test provider account, which is not billed. The JAG incident came from testing on a real practice's account: test orders should only use an account we set up for the vendor.

### A20 [Leo]
Before go-live:
- The integration was created by the customer on the Website and belongs to the right practice and NPI.
- Folders exist and connect.
- A validation order was placed and showed up under the right practice.
- A test result reached their folder.
- Report option and kit delivery match what the practice wants.

## Part B

### B1 [Leo]
- Vendor: vendor code, HL7 version, SFTP details and folders, a sample order.
- Practice: practice ID, provider names and NPIs, report option (Classic or Personalized, split or not), kit delivery, billing preference.

### B2 [Leo]
The customer creates it on the Website (practice/provider settings > EHR integration). The Sales director reviews and approves it in the Unimod panel (EHR Auto Integration page). Data: `lis_emr.ehr_integrations`, with vendor settings in `ehr_vendors`. Screenshot: [Leo to add].

### B3 [Leo]
1. Vendor setup (once per vendor): engineering adds the vendor and SFTP.
2. The practice requests the integration on the Website (customer).
3. The Sales director reviews and approves it in the Unimod panel.
4. Validation order and result test (vendor + engineering).
5. Go live.

### B4 [Leo]
Before the first real order, check that the approved integration's practice ID and NPIs match the practice that asked for it, and place a validation order to confirm it lands in that practice. Never link a vendor to a practice because a vendor or another thread names it.

### B5 [Leo]
Use the validation test code (TEST^ZZZTEST) on a test provider account, not a real practice's account.

### B6 [Leo]
Export attached (vendors, practices linked, folders, report options, special handling). Credentials removed.

### B7
- Per-report PDF (split): `ehr_integrations` split flag + `result_push_level`; e.g. Cerbo practices and Maristany.
- Total Tox combined message: Cerbo only.
- Order Summary PDF: enabled per vendor (BioInsights).
- Classic vs Personalized: `report_option`.
- Results folder must contain only .hl7: Cerbo/MDHQ.
- PID-2 / per-test OBR-2 echo: Nextech only.
All set on the integration or vendor row; see the export.
Where: result-attachment.service.ts; result-generation.service.ts; hl7-encoder.service.ts

### B8 [Leo]
[Leo to fill from vendor threads.] Known: Nextech (Jessica), Gundry/THM (Rob), devcom/BioInsights (Olena), Cerbo (support contact).

### B9 [Leo]
Look up the file in `hl7_file_input` by file name or vendor/date: status, last_error, and the sample id if placed. If it's not there, it wasn't picked up (wrong folder, extension not .hl7, or a filename already used).

### B10 [Leo]
`result_transmission_records` per sample: status TRANSMITTED, file name, time. The file is also kept on the emr-v2 pod.

### B11 [Leo]
1. Provider has no integration / no account (customer_not_found): the customer connects on the Website, then we retry.
2. Unknown test code: send the right code or add the mapping.
3. Vendor mismatch: wrong vendor for that provider.
4. SFTP unreachable for results: the vendor fixes the server; we resend.
5. File too large: compressed or split.

### B12 [Leo]
Support could self-check B9 and B10 (order received and why it failed; result delivered) and B11 #1 and #3 with read access to an order-intake and result-delivery view.

### B13
- Add a provider: the clinic admin adds the provider to the practice's integration on the Website. This creates a pending row that the Sales director approves in the Unimod panel.
- Remove a provider: suspend that provider's integration. Removing a provider from the clinic also deactivates their EMR integration automatically.
Where: auto-integrate/services/integration-request.service.ts:1514-1619 (deactivateOne); practice integration API

### B14
Deactivate (reject) the old vendor's integration rows for that practice. Result delivery only uses LIVE rows, so results stop. Note: the old vendor's order folder is still polled until the vendor itself is turned off.
Where: integration-request.service.ts:1619 (deactivateOne)

### B15
Use the manual resend: `POST /result/generate/:sampleId` (or batch). Every resend produces a new delivery. There is no duplicate check, so only resend when needed.
Where: result/controllers/result.controller.ts:133,159

### B16
Suspend or withdraw the integration (practice-wide: suspends every active row for that practice and vendor). To stop a whole vendor, deactivate the vendor so its folders are no longer polled.
Where: integration-request.service.ts:1586,1619

### B17
- One practice: suspend that practice's integration for the vendor. Takes effect on the next delivery, no restart needed.
- The whole connection: deactivate the vendor or all its integration rows.
Where: integration-request.service.ts

### B18 [Leo]
Query attached (`result_transmission_records` joined to the integration and sample, filtered by vendor/folder and date range). The JAG list was built from the vendor folder listing joined to this table.

### B19 [Leo]
- No ACK, so failed orders are silent to the EMR.
- Corrected results are not marked as corrections.
- Resends have no duplicate check.
- The test-connection button fails for key-only SFTP.
- About 180 old integration rows have no vendor.
- Patient contact can be overwritten by practice contact data.
- A retired integration does not stop folder polling.
