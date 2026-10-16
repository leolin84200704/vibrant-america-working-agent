# Vibrant EMR HL7 Order (ORM^O01) - Field Reference

Version 2 (2026-10). Describes what Vibrant's order intake actually reads. Fields not listed
under a segment are ignored; you may send them, but they have no effect.

## Example message

```hl7
MSH|^~\&|EPIC|CLINIC001|IN OFFICE|LC|202501220952||ORM^O01|MSG20250122095201001|P|2.5|
PID|1|PAT123456|||Smith^John^Michael||19850315|M|||123 Main Street^^Anytown^CA^90210||5551234567|||||||john.smith@email.com|
IN1|1|C|
ORC|NW|ORD20250122001||||||||||1234567890^Johnson^Robert^^^^^^N|
OBR|1|ORD20250122001||VAREQUISTION463^Gut Zoomer 5.0^L|||202501220951||||N||Not Specified^||0|1234567890^Johnson^Robert^^^^^^N|||FASTING|
DG1|1||K59.00|
DG1|2||R19.7|
OBR|2|ORD20250122001||VATEST70^Vitamin D, 25-OH^L|||202501220951||||N||Not Specified^||0|1234567890^Johnson^Robert^^^^^^N|||NON-FASTING|
DG1|3||E55.9|
```

The test codes above are real, orderable codes. For your menu, use only codes from the
current Vibrant compendium.

## MSH - Message Header

| Field | Example | Meaning |
|---|---|---|
| MSH-3 | `EPIC` | Sending application. |
| MSH-4 | `CLINIC001` | Sending facility. Not used for routing unless your onboarding contact tells you otherwise. |
| MSH-5 | `IN OFFICE` | Fixed value. Send as shown. Not read. |
| MSH-6 | `LC` | Fixed value. Send as shown. Not read. |
| MSH-7 | `202501220952` | Message date/time, YYYYMMDDHHMM. |
| MSH-9 | `ORM^O01` | Message type. |
| MSH-10 | `MSG20250122095201001` | Message control ID. Must be unique per message: a control ID that already produced an order is not processed again. |
| MSH-11 / MSH-12 | `P` / `2.5` | Send as shown. Not read. |

## PID - Patient

| Field | Example | Meaning |
|---|---|---|
| PID-2 | `PAT123456` | Your patient ID. |
| PID-5 | `Smith^John^Michael` | `Last^First^Middle`. |
| PID-7 | `19850315` | Date of birth, YYYYMMDD. |
| PID-8 | `M` | Gender, M/F/U. |
| PID-10 | | Race (optional). |
| PID-11 | `123 Main Street^^Anytown^CA^90210` | `Street^^City^State^ZIP`. |
| PID-13 | `5551234567` | Phone. |
| PID-16 | | Marital status (optional). |
| PID-19 | (empty) | **SSN only.** Leave empty unless you are sending an SSN. Anything here is stored as the SSN. |
| PID-20 | `john.smith@email.com` | **Patient email.** The only field email is read from. |

Patients are matched within the practice on first name, last name, gender and date of birth.
PID-3 and PID-18 are not read.

## IN1 - Who pays

| Field | Example | Meaning |
|---|---|---|
| IN1-2 | `C` | `C` = charge the practice's default payment method on file. Any other value, or no IN1 segment = the patient receives a payment link. |

Insurance is not billed through the HL7 order.

## ORC - Common Order

| Field | Example | Meaning |
|---|---|---|
| ORC-1 | `NW` | New order. |
| ORC-2 | `ORD20250122001` | Your order number. |
| ORC-12 | `1234567890^Johnson^Robert^^^^^^N` | Ordering provider (XCN), see below. |

### Ordering provider (ORC-12, same value in OBR-16)

| Component | Example | Meaning |
|---|---|---|
| 1 | `1234567890` | **Provider NPI.** This is what identifies the order. (A value of 7 digits or fewer is read as a Vibrant customer ID instead.) |
| 2 | `Johnson` | Family name. Used in error messages only. |
| 3 | `Robert` | Given name. Used in error messages only. |
| 9 | `N` | Identifier type. Not read. |

The provider must have a Vibrant account **and** be set up on your integration before their
orders are accepted. Orders from a provider who is not set up are held as "customer not found".

## OBR - One per test

| Field | Example | Meaning |
|---|---|---|
| OBR-2 | `ORD20250122001` | Same as ORC-2. |
| OBR-4 | `VAREQUISTION463^Gut Zoomer 5.0^L` | `Code^Name^L`. Only component 1 (the code) is used. The code must exist in the current compendium and be orderable, otherwise the order is held. |
| OBR-7 | `202501220951` | Collection date/time, YYYYMMDDHHMM. Used as the sample's collection time. Leave empty to use the time we receive the file. |
| OBR-11 | `N` | Send as shown. Not used. |
| OBR-15 | `0` | Send as shown. Not read. |
| OBR-16 | | Same XCN as ORC-12. |
| OBR-19 | `FASTING` | FASTING / NON-FASTING. Optional; currently informational only. |

Code formats: `VAREQUISTION...` (panels), `VATEST...` (individual tests), `discountpanel...`
(bundles), `VACP...` (custom panels).

## DG1 - Diagnosis codes

| Field | Example | Meaning |
|---|---|---|
| DG1-1 | `1` | Sequence number. |
| DG1-3 | `K59.00` | ICD-10 code (component 1 is read). |

All DG1 segments in the message apply to the whole order. Grouping them under a specific OBR
is not preserved.

## File handling

- Place each order as one `.hl7` file in the order folder agreed for your integration. Files are
  picked up every 15 minutes.
- **A file name is processed only once.** To resend a corrected order, use a new file name and a new MSH-10.

## Set at onboarding, not in the HL7

- Kit delivery / draw location (kit shipped to the patient, or supplied by the office): set per provider.
- Order summary PDF: on request, a PDF is placed on your SFTP for every order we receive, in a folder you choose.
- Result delivery (ORU^R01) folder and format.
