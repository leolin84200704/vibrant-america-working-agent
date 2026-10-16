<!-- Verbatim copy of the partner-facing spec, from the source markdown (Oct 2025) behind UpdatedExampleOrder_Explained.pdf. Do not edit: this is what partners hold. Gaps vs our code: gap-table.md -->
# Vibrant EMR HL7 Order Example - Detailed Explanation

## Table of Contents
- [Complete Order Message](#complete-order-message)
- [Segment-by-Segment Explanation](#segment-by-segment-explanation)
- [Provider Identification System](#provider-identification-system)
- [Test Code Processing](#test-code-processing-and-mappings)
- [Complete Data Flow](#complete-data-flow)
- [Processing Result](#processing-result)

---

## Complete Order Message

```hl7
MSH|^~\&|EPIC|CLINIC001|IN OFFICE|LC|202501220952||ORM^O01|MSG20250122095201001|P|2.5|
PID|1|PAT123456|||Smith^John^Michael||19850315|M|||123 Main Street^^Anytown^CA^90210||5551234567|||||MRN789123^^^P||john.smith@email.com|
IN1|1|C|||^^^^||||||||||||||||||||||||||||||||||||||||||
ORC|NW|ORD20250122001||||||||||1234567890^DOC001^Johnson^Robert^^^^N|
OBR|1|ORD20250122001||VAREQUISTION279^Gut Zoomer 3.0^L|||202501220951||||N||Not Specified^||0|1234567890^DOC001^Johnson^Robert^^^^N|||||||||||^^^^^^FASTING|
DG1|0||K59.00|
DG1|1||K92.2|
DG1|2||R19.7|
DG1|3||K58.9|
DG1|4||R10.9|
OBR|2|ORD20250122001||VAREQUISTION259^Heavy Metals (Creatinine)^L|||202501220951||||N||Not Specified^||0|1234567890^DOC001^Johnson^Robert^^^^N|||||||||||^^^^^^NON-FASTING|
DG1|5||Z87.891|
DG1|6||T56.0X1A|
DG1|7||R68.89|
OBR|3|ORD20250122001||discountpanel289^Total Tox-burden^L|||202501220951||||N||Not Specified^||0|1234567890^DOC001^Johnson^Robert^^^^N|||||||||||^^^^^^NON-FASTING|
DG1|8||Z87.891|
DG1|9||T65.91XA|
DG1|10||R68.89|
```

---

## Segment-by-Segment Explanation

### MSH - Message Header

```hl7
MSH|^~\&|EPIC|CLINIC001|IN OFFICE|LC|202501220952||ORM^O01|MSG20250122095201001|P|2.5|
```

| Field | Value | Description |
|:------|:------|:------------|
| **Field 1** | `\|` | Field separator |
| **Field 2** | `^~\&` | Encoding characters |
| **Field 3** | `EPIC` | **Sending application** - Your EMR system name |
| **Field 4** | `CLINIC001` | **Sending facility** - Your practice/facility ID |
|  |  | **CRITICAL**: Used for customer identification in some EMR systems |
|  |  | **PracticeFusion**: This field overrides provider ID for customer lookup |
|  |  | **Other EMRs**: Used for facility identification and logging |
|  |  | **Format**: Alphanumeric identifier (no spaces recommended) |
| **Field 5** | `IN OFFICE` | **Receiving application** - Standard for Vibrant |
| **Field 6** | `LC` | **Receiving facility** - Always "LC" for Vibrant |
| **Field 7** | `202501220952` | **Date/time of message** - YYYYMMDDHHMM format |
| **Field 8** | *(empty)* | Security |
| **Field 9** | `ORM^O01` | **Message type** - Order message type |
| **Field 10** | `MSG20250122095201001` | **Message control ID** - Unique message identifier |
| **Field 11** | `P` | **Processing ID** - Production mode |
| **Field 12** | `2.5` | **Version ID** - HL7 version |

### PID - Patient Identification

```hl7
PID|1|PAT123456|||Smith^John^Michael||19850315|M|||123 Main Street^^Anytown^CA^90210||5551234567|||||MRN789123^^^P||john.smith@email.com|
```

| Field | Value | Description |
|:------|:------|:------------|
| **Field 1** | `1` | Set ID - Always 1 for single patient |
| **Field 2** | `PAT123456` | **Patient ID** - Your internal patient ID |
| **Field 5** | `Smith^John^Michael` | **Patient name** - Last^First^Middle format |
| **Field 7** | `19850315` | **Date of birth** - YYYYMMDD format |
| **Field 8** | `M` | **Gender** - M/F/U |
| **Field 11** | `123 Main Street^^Anytown^CA^90210` | **Patient address** - Street^^City^State^ZIP |
| **Field 13** | `5551234567` | **Phone number** - Patient contact |
| **Field 18** | `MRN789123^^^P` | **Medical Record Number** |
|  |  | **Format**: [MRN]^^^P (the ^^^P suffix is required) |
|  |  | **Usage**: Internal patient tracking and identification |
| **Field 20** | *(empty)* | **Patient Email Address** |
|  |  | **IMPORTANT**: Despite the field name "Driver's License", this contains patient email |
|  |  | **Usage**: Used for result notifications and patient communication |
| **Field 39** | `john.smith@email.com` | **Alternative Email Field** |
|  |  | **Usage**: Some EMRs place email here instead of Field 20 |

---

### IN1 - Insurance Information

```hl7
IN1|1|C|||^^^^||||||||||||||||||||||||||||||||||||||||||
```

| Field | Value | Description |
|:------|:------|:------------|
| **Field 1** | `1` | Insurance sequence number |
| **Field 2** | `C` | **Insurance plan ID** - C=Commercial, O=Other, M=Medicare, etc. |
| **Fields 3-47** | *(empty)* | Insurance details - Not used in basic integration |

---

### ORC - Common Order

```hl7
ORC|NW|ORD20250122001||||||||||1234567890^DOC001^Johnson^Robert^^^^N|
```

| Field | Value | Description |
|:------|:------|:------------|
| **Field 1** | `NW` | **Order control** - NW=New Order |
| **Field 2** | `ORD20250122001` | **Placer order number** - Your order number |
| **Field 12** | `1234567890^DOC001^Johnson^Robert^^^^N` | **Ordering provider** - **XCN Format** |

#### XCN Format Breakdown:
| Component | Value | Description |
|:----------|:------|:------------|
| **Component 1** | `1234567890` | **NPI Number or Customer ID** |
| **Component 2** | `DOC001` | **Internal Provider ID** (optional) |
| **Component 3** | `Johnson` | **Provider's Family Name** |
| **Component 4** | `Robert` | **Provider's Given Name** |
| **Component 5** | *(empty)* | **Provider's Middle Name** |
| **Component 6** | *(empty)* | **Name Suffix** (Jr., Sr., etc.) |
| **Component 7** | *(empty)* | **Name Prefix** (Dr., Mr., etc.) |
| **Component 8** | *(empty)* | **Professional Degree** (MD, DO, etc.) |
| **Component 9** | `N` | **Identifier Type Code** |

---

### OBR #1 - Test Panel Order (Gut Zoomer 3.0)

```hl7
OBR|1|ORD20250122001||VAREQUISTION279^Gut Zoomer 3.0^L|||202501220951||||N||Not Specified^||0|1234567890^DOC001^Johnson^Robert^^^^N|||||||||||^^^^^^FASTING|
```

| Field | Value | Description |
|:------|:------|:------------|
| **Field 1** | `1` | **Set ID** - Sequential OBR number |
| **Field 2** | `ORD20250122001` | **Placer order number** - Same as ORC-2 |
| **Field 4** | `VAREQUISTION279^Gut Zoomer 3.0^L` | **Test Identification** |
|  |  | **Component 1**: Test Code (VAREQUISTION279) - Vibrant's internal test code |
|  |  | **Component 2**: Test Name (Gut Zoomer 3.0) - Human-readable test name |
|  |  | **Component 3**: Coding System (L) - L=Local coding system |
|  |  | **Processing**: System extracts Component 1 to identify which test to order |
| **Field 7** | `202501220951` | **Observation date/time** - Collection time YYYYMMDDHHMM |
| **Field 11** | `N` | **Specimen action code** - N=Normal collection |
| **Field 13** | `Not Specified^` | **Relevant clinical info** - Clinical notes |
| **Field 15** | `0` | **Specimen source** - Default specimen type |
| **Field 16** | `1234567890^DOC001^Johnson^Robert^^^^N` | **Ordering provider** - Same XCN format as ORC-12 |
| **Field 26** | `FASTING` | **Fasting status** - FASTING/NON-FASTING for this test |

### DG1 - Diagnosis Codes (for Gut Zoomer)

```hl7
DG1|0||K59.00|    # Constipation, unspecified
DG1|1||K92.2|     # Gastrointestinal hemorrhage, unspecified  
DG1|2||R19.7|     # Diarrhea, unspecified
DG1|3||K58.9|     # Irritable bowel syndrome without diarrhea
DG1|4||R10.9|     # Unspecified abdominal pain
```

| Field | Value | Description |
|:------|:------|:------------|
| **Field 1** | `0,1,2...` | **Set ID** - Sequential diagnosis number |
| **Field 2** | *(empty)* | Diagnosis coding method |
| **Field 3** | ICD-10 code | **Diagnosis code** - Medical justification for test |

---

### OBR #2 - Test Panel Order (Heavy Metals)

```hl7
OBR|2|ORD20250122001||VAREQUISTION259^Heavy Metals (Creatinine)^L|||202501220951||||N||Not Specified^||0|1234567890^DOC001^Johnson^Robert^^^^N|||||||||||^^^^^^NON-FASTING|
```

| Field | Value | Description |
|:------|:------|:------------|
| **Field 1** | `2` | **Set ID** - Second test order |
| **Field 4** | `VAREQUISTION259^Heavy Metals (Creatinine)^L` | **Universal service ID** |
| **Field 26** | `NON-FASTING` | **Fasting status** - This test doesn't require fasting |

### DG1 - Diagnosis Codes (for Heavy Metals)

```hl7
DG1|5||Z87.891|   # Personal history of nicotine dependence
DG1|6||T56.0X1A|  # Toxic effect of lead and its compounds, accidental
DG1|7||R68.89|    # Other general symptoms and signs
```

---

### OBR #3 - Bundle Order (Total Tox-burden)

```hl7
OBR|3|ORD20250122001||discountpanel289^Total Tox-burden^L|||202501220951||||N||Not Specified^||0|1234567890^DOC001^Johnson^Robert^^^^N|||||||||||^^^^^^NON-FASTING|
```

| Field | Value | Description |
|:------|:------|:------------|
| **Field 1** | `3` | **Set ID** - Third test order |
| **Field 4** | `discountpanel289^Total Tox-burden^L` | **Universal service ID** |
|  |  | This is a discount bundle containing multiple related tests |

### DG1 - Diagnosis Codes (for Total Tox-burden)

```hl7
DG1|8||Z87.891|   # Personal history of nicotine dependence
DG1|9||T65.91XA|  # Toxic effect of unspecified substance, accidental
DG1|10||R68.89|   # Other general symptoms and signs
```

---

## Provider Identification System

### How the System Identifies Customers

The ordering provider field (ORC-12 and OBR-16) uses **XCN (Extended Composite ID Number and Name)** format:

```
1234567890^DOC001^Johnson^Robert^^^^N
```

### Provider ID Processing Logic

1. **Extract Provider ID**: System extracts Component 1 (1234567890)
2. **Determine ID Type**:
   - **If ID ≤ 7 digits**: Treated as **Vibrant Customer ID**
   - **If ID > 7 digits**: Treated as **NPI Number**
3. **Customer Lookup**:
   - **Customer ID**: Direct lookup in `order_clients` table
   - **NPI Number**: Lookup via gRPC service to find associated customer(s)

### Example Processing

**Input**: `1234567890^DOC001^Johnson^Robert^^^^N`

| Step | Processing Action | Result |
|:-----|:------------------|:-------|
| **Step 1** | Extract ID = "1234567890" | 10 digits |
| **Step 2** | Since length > 7, treat as NPI Number | NPI lookup required |
| **Step 3** | Call `fetchCustomerDetailsByNpi("1234567890")` | Find associated customers |
| **Step 4** | Find customer(s) associated with this NPI | Customer ID retrieved |
| **Step 5** | Use customer_id for order processing | Order linked to customer |

### Special Cases

#### PracticeFusion EMR
- Uses MSH-4 (Sending Facility) instead of provider ID
- Example: `MSH|^~\&|PracticeFusion|CLINIC001|...`
- System uses "CLINIC001" as customer identifier

#### YHL EMR
- Hardcoded to customer ID "6583"
- Ignores provider ID in XCN field

#### Standard EMRs
- Use XCN Component 1 as described above

### Customer Validation

| Scenario | Result | Action |
|:---------|:-------|:-------|
| **Customer Found** | Success | Process order normally |
| **Customer Not Found** | Error | Order rejected with error message |
| **Multiple Customers** | Success | Use first matching customer |
| **Invalid Provider ID** | Error | Order processing fails |

**Error Message Format**: "Customer not found: [FirstName] [LastName]"

### Provider Name Usage

- **Component 3 (Last Name)**: Used in error messages and logging
- **Component 4 (First Name)**: Used in error messages and logging
- **Names are NOT used for customer identification** - only for display/logging

---

## Test Code Processing and Mappings

### Test Code Validation

The system validates test codes against internal databases:

| Code Type | Description | Database Table | Example |
|:----------|:------------|:---------------|:--------|
| **VAREQUISTION codes** | Test panels | `package_price` | VAREQUISTION279 = Gut Zoomer 3.0 |
| **VATEST codes** | Individual tests | `package_price` | VATEST2270 = Vitamin D |
| **discountpanel codes** | Bundle packages | `package_price` | discountpanel289 = Total Tox-burden |
| **VACP codes** | Custom panels | `package_price` | VACP100 = Custom Thyroid Panel |

### Legacy Code Mappings

Some older test codes are automatically mapped to current codes:

| Legacy Code | Current Code | Description |
|:------------|:-------------|:------------|
| **VAREQUISTION240** | **VARequisition332** | Panel mapping |
| **VAREQUISTION241** | **VARequisition326** | Panel mapping |
| **VAREQUISTION252** | **VAREQUISTION330** | Panel mapping |
| **VATEST1529** | **VATEST2270** | Vitamin D mapping |

### Special EMR Mappings

**ClearSky EMR** uses numeric suffixes that map to full codes:

| Numeric Code | Full Code | Description |
|:-------------|:----------|:------------|
| **278** | **VAREQUISTION299** | ClearSky mapping |
| **308** | **VARequisition315** | ClearSky mapping |
| **320** | **VARequisition314** | ClearSky mapping |

### Error Handling

| Error Type | Action | Result |
|:-----------|:-------|:-------|
| **Invalid test codes** | Order rejected | Error code list returned |
| **Discontinued codes** | Automatic mapping | Converted to current equivalents |
| **Missing codes** | Error logging | Added to error_codes field |

---

## Complete Data Flow

### Step 1: Message Reception
- File placed in SFTP `/Order/` folder
- System retrieves file every 15 minutes
- HL7 format validation performed

### Step 2: Customer Identification
- Extract provider ID from ORC-12/OBR-16 Component 1
- If ≤7 digits: Lookup as Customer ID in `order_clients` table
- If >7 digits: Lookup as NPI in customer database via gRPC
- Special handling for PracticeFusion (uses MSH-4) and YHL (hardcoded)

### Step 3: Test Code Processing
- Extract test codes from OBR-4 Component 1
- Apply legacy code mappings if needed
- Validate against `package_price` table
- Build test list for order creation

### Step 4: Patient Processing
- Extract patient demographics from PID segment
- Create or update patient record
- Link patient to customer account

### Step 5: Order Creation
- Create order record with extracted information
- Add all tests from OBR segments
- Include diagnosis codes from DG1 segments
- Set fasting requirements from OBR-19

### Step 6: Database Updates
- Update `hl7_file_input` table with processing status
- Create sample record with unique sample_id
- Archive processed file to appropriate folder

---

## Processing Result

This message will create one order with three test components:

### Order Summary

| Test Component | Test Code | Fasting Status | Diagnosis Codes |
|:----------------|:----------|:---------------|:----------------|
| **Gut Zoomer 3.0 panel** | VAREQUISTION279 | ✅ FASTING | K59.00, K92.2, R19.7, K58.9, R10.9 |
| **Heavy Metals panel** | VAREQUISTION259 | ❌ NON-FASTING | Z87.891, T56.0X1A, R68.89 |
| **Total Tox-burden bundle** | discountpanel289 | ❌ NON-FASTING | Z87.891, T65.91XA, R68.89 |

### Order Details

| Field | Value |
|:------|:------|
| **Customer** | Identified by NPI 1234567890 |
| **Patient** | John Michael Smith (DOB: 03/15/1985) |
| **Provider** | Dr. Robert Johnson |
| **Collection Date** | 01/22/2025 09:51 |
| **Diagnosis Codes** | 10 ICD-10 codes supporting medical necessity |
| **Order Number** | ORD20250122001 |
| **Message Control ID** | MSG20250122095201001 |

### Result Delivery

All tests will be processed together and results delivered as:
- **Separate ORU^R01 messages** for each test panel, OR
- **Combined ORU^R01 message** with multiple OBR/OBX segments
- **Format depends on EMR preferences** and integration configuration

---

## Key Points Summary

1. **Multiple Tests**: This order contains 3 separate test orders (3 OBR segments)
2. **Test Types**: Demonstrates panel (VAREQUISTION), individual test panel (VAREQUISTION), and bundle (discountpanel)
3. **Fasting Requirements**: Shows both FASTING and NON-FASTING requirements
4. **Diagnosis Support**: Each test group has supporting ICD-10 diagnosis codes
5. **Provider Information**: Consistent ordering provider across all tests
6. **Order Tracking**: Same order number (ORD20250122001) links all tests together
7. **Customer Identification**: Provider ID (1234567890) determines which Vibrant customer account to use
8. **Email Handling**: Patient email can be in PID-20 or PID-39 depending on EMR system
9. **Error Prevention**: Comprehensive validation at each processing step
10. **Legacy Support**: Automatic mapping of older test codes to current equivalents

---

*This document provides a complete technical reference for implementing HL7 ORM^O01 order messages for Vibrant EMR integration.*

