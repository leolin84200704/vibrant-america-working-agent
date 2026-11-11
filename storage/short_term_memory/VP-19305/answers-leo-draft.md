# VP-19305 - Leo questions (DRAFT v2, 2026-11-11)

Checked against prod lis_emr (lisportalprod2), emr-v2 origin/main 69b55d0, ehr-frontend / va-portal / vibrant-wellness-portal origin/main, core-v2 patient service.
Lines marked [ASK LEO] still need Leo's input. Everything else is verified.
Materials are in ./materials/.

## Leo questions

### A2
Attached: `VP-19305_sample-order-ORM.hl7` and `VP-19305_sample-result-ORU.hl7`. Both use placeholder data and follow the field positions the code reads and writes. The PDF in the result is truncated.
There is no ACK sample. We do not send ACKs and do not read them.

### A7
Both. Many vendors put files on an SFTP server we host:
- Our server 45.24.217.155: ChARM, eClinicalWorks, OptiMantra, PraxisEMR, HealthMatters, THM (Gundry), YHL, GLO, Unprescribed, Aprima, Meditab, NICHOLS, ZymeBalanz.
- 45.24.217.150:2222: Practice Fusion. [ASK LEO: confirm this one is ours too]
- 64.124.9.100 (ports 2222/2224/2225): Breathermae, FollowThatPatient, DocVilla. [ASK LEO: ours or a third party's]
- Vendor-hosted: Cerbo/MDHQ, Power2Practice, Athena, Elation, OptimalDX, Nextech, BioInsights, Greenway, Harris, Health Fusion, INSYNC, Marqi, Cascades.
See the `sftp_host` column in `VP-19305_vendor-config-export.csv`.

### A10
We need from the partner: host, port, username, and either a password or an SSH private key; the order folder and the result folder.
Where it is stored: `lis_emr.ehr_vendors` (one row per vendor: host, port, user, password or private key, folders). Credentials sit in that table as plain text. A practice-level override exists on `ehr_integrations` but is rarely used.
Which folders we poll for orders is a separate table, `lis_emr.sftp_folder_mapping`. Cerbo has one order folder per practice (181 folders); other vendors have one.
There is no screen for vendor or folder setup. Engineering edits the database.

### A19
- No staging SFTP for partners. Our staging service points at our production SFTP server, so it cannot be used for partner tests either.
- Partners test in production. The test order goes under the integration's own provider account. If the practice has no account we can use, use the ZZZTEST account. [ASK LEO: is "ZZZTEST" a test provider account, or the test patient name TEST^ZZZTEST? Please give the account id if it is an account.]
- Test patient name: TEST^ZZZTEST.
- To avoid a charge, leave IN1 out (or send anything other than "C"). Then no card is charged and the patient gets a pay-later email. A test patient with no email gets nothing.
- A test order has no physical sample. To send a test result back, ops have to receive the sample manually and release a result.
- Never place test orders on another practice's account. That is how the JAG incident happened.

### A20
Before go-live:
1. The integration was created by the practice on the Website, approved, and its practice and NPIs match the practice that asked for it.
2. The vendor's SFTP connects, and the order folder is in `sftp_folder_mapping` (orders only).
3. A test order (A19) showed up under the right practice and provider.
4. A test result reached the vendor's result folder and the vendor confirmed they can match it to the order.
5. Report option (Classic or Personalized), kit delivery and billing match what the practice wants.

### B1
From the vendor: SFTP host, port, user, password or key, the order and result folders, a sample order file, and which field carries the practice id (if any).
From the practice: Vibrant practice id, providers' names and NPIs, report option (Classic or Personalized, one PDF or one per report), kit delivery default, billing (card on file or patient pays).

### B2
- The practice requests it: https://intelligence.vibrant-wellness.com/my-practice/practice-setting/third-party-integrations (the same page is embedded in https://www.vibrant-america.com/lis/patientpage/#/setting/third-party-integrations ). The card is shown only to accounts in the auto-EMR-integration beta.
- We review and approve it: vibrant-wellness-portal, VA Portal > EHR Auto Integration (route /Portal/EHRAutoIntegration). [ASK LEO: confirm the domain of vibrant-wellness-portal; the code suggests https://vibrant-wellness-portal.pages.dev/Portal/EHRAutoIntegration ]
- Data: `lis_emr.ehr_integrations` (one row per provider per practice per vendor). Vendor settings: `lis_emr.ehr_vendors`. Order folders: `lis_emr.sftp_folder_mapping`.
- No screen exists for vendor settings, order folders, or suspend. Those are database or API changes by engineering.
[Screenshots: Leo to take from the URLs above]

### B3
1. New vendor only: engineering adds the vendor row and the order folder.
2. Practice: requests the integration on the Website.
3. Review and approve in EHR Auto Integration. [ASK LEO: who approves today: Support, TPM, or engineering?]
4. Vendor sends a test order; we confirm it landed under the right practice; we send a test result.
5. Go live.

### B4
Before the first real order:
- In EHR Auto Integration, check that the practice id and NPIs on the request match the practice that asked. Do not link a vendor to a practice because a vendor email or another ticket names it.
- Place a test order (A19) and confirm it lands under that practice.
- Since Oct 21, an order is rejected if the provider has not connected that vendor (vendor_mismatch). For vendors that send a practice id, an order for a practice the provider is not set up at is held (practice_not_found).

### B5
See A19: the integration's own provider account (or the test account), patient TEST^ZZZTEST, no IN1 "C", and ops release the result manually.

### B6
Attached:
- `VP-19305_vendor-config-export.csv`: one row per vendor (host, port, login type, folders, special settings, number of live practices and polled order folders). No credentials.
- `VP-19305_vendor-practices-live.csv`: one row per vendor and practice with report option, push level, kit delivery and overrides.

### B8
We have no contact list on file. `ehr_vendors.support_email` and `support_phone` are empty for every vendor. Vendor threads run through Support's Zendesk (support@vibrant-wellness.com).
Known from recent threads: Nextech (Jessica Marshall), devcom for BioInsights (Olena), THM/Gundry (Rob).
[ASK LEO: OK to ask Zhenhe / Support to pull the contact for each vendor from Zendesk?]

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
3. Provider not connected (`customer_not_found=<provider name>`, 11): the provider has no live integration for that vendor. Fix: the practice adds the provider on the Website; once approved, the order is retried automatically.
4. Wrong practice (`practice_not_found=<NPI>@<practice id>`, 5, all since Nov 10): the vendor sent a practice id the provider is not set up at. Fix: add the provider at that practice, or the vendor corrects the practice id.
5. Vendor mismatch (`vendor_mismatch`, 2): the provider is connected through a different vendor. Fix: check which EMR the practice uses.
6. Order not created at the last step (`finalize returned no sampleId`, 2): one had billing "C" with no card on file (fix: the practice adds a card); the other gave no reason and needs engineering.
Results (90 days): 37 delivery failures, almost all "SFTP upload failed" after retries. Fix: the vendor fixes their server; we resend (B15).

### B12
Support could check these alone with read access to `hl7_file_input` and `result_transmission_records` (a simple lookup screen would do):
- B9: was the order received, and why it failed.
- B10: was the result delivered.
- B11 #3, #4, #5: they can tell the practice what to fix on the Website without engineering.
Code problems (#1) and service errors (#2) still need engineering.

### B18
Attached: `VP-19305_B18_files-sent-to-connection.sql`. Inputs are vendor id and a date range. Run on lis_emr.
Re-checked today: with BioInsights (46) and 2026-07-29 to 2026-10-13 it returns the JAG list, 204 rows for 200 samples.

### B19
1. No ACK in either direction. A failed order is invisible to the EMR.
2. Corrected reports go out as Final; we never mark a correction.
3. A resend has no duplicate check.
4. The vendor "test SFTP" endpoint only tries the password, so key-only vendors (BioInsights) always fail the test.
5. SFTP passwords and private keys are stored as plain text in `ehr_vendors`.
6. 179 live integration rows have no vendor.
7. A practice can overwrite a patient's phone and email when it sends its own office contact in PID-13 / PID-20.
8. Turning off an integration does not stop polling the vendor's order folder. That is a separate table.
9. Suspend has no screen; it is an API call only.
10. A real patient HL7 result file is committed to the emr-v2 repo root (`2601086695_20260202044208.hl7`, since 2026-03-02). [ASK LEO: list this in the doc, or report it separately and just remove it?]

## Corrections to the AI answers (draft v1)

- A3: the vendor is identified by the order folder the file came from, not by MSH-5.
- A4: ORC-17 is read for MDHQ, FOLLOWTHATPATIENT and THM. Nextech's practice id is read from MSH-4. FOLLOWTHATPATIENT sends our customer id in ORC-12, not an NPI.
- A5 (verified in core-v2): a returning patient is matched on exact first name, last name and sex plus DOB, among patients of the ordering provider and of providers in the same practice. The EMR patient id is not used. Only phone (PID-13) and email (PID-20) can change on an existing patient, and only when the new value is not blank and differs. Address is used for that order only.
- A10: credentials are in `ehr_vendors` as plain text, not in Key Vault.
- A12: add `practice_not_found` (held and retried: vendor sent a practice id the provider is not at) and `provider_not_in_clinic` (terminal).
- A13: ChARM is the only exception; results to ChARM are also sent by HTTP POST and that call returns an acknowledgement.
- A19 (old): TEST^ZZZTEST is a patient name, not a test code.
- B7: one PDF per report is set only for Maristany Medical (Cerbo). Resilience Code (Cerbo) gets results per report group and holds GUT5 back. Order Summary PDF is written on order arrival for FOLLOWTHATPATIENT only; no vendor has the "with result" Order Summary turned on. Add ChARM's HTTP POST.
- B13 / B16 / B17: practice-wide create, suspend and withdraw exist in the API but have no screen. Integration statuses in use are LIVE, PENDING and REJECTED.
