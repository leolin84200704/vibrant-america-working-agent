# UpdatedExampleOrder_Explained vs lis-backend-emr-v2 parser

Verified 2026-10-15 against `lis-backend-emr-v2` origin/main 270f0b2
(`src/modules/hl7-order-processing/services/{parser,obr-parser,patient-detail-parser}.service.ts`).
Rows marked (09-23) come from the BioInsights audit against f52c6dd and were not re-read today.

"What to tell a partner" is the answer to give when a partner follows the spec on that row.

## Spec says something our code does NOT do (spec wrong or code wrong; ours to fix)

| Field | Spec | Code | Impact | What to tell a partner |
|---|---|---|---|---|
| IN1-2 | "Insurance plan ID - C=Commercial, O=Other, M=Medicare" | `C` -> customerPay (practice's card is charged); anything else -> patientPayLater (patient gets a payment link). `chargeMethodFromIn1` | **High.** A partner sending `C` for "commercial insurance" bills the practice. | `C` = bill the practice; any other value = patient pays via link. Insurance is not billed through HL7. |
| OBR-4 examples | `VAREQUISTION279 = Gut Zoomer 3.0`, `VATEST2270 = Vitamin D` | (09-23) 279 is Gut Zoomer 4.0 and not orderable; 2270 is Copper Serum and not orderable | **High.** devcom's first file used these codes verbatim and failed `emr_code_not_found`. | Use codes from the current compendium only; the examples are illustrative. |
| ORC-12 / OBR-16 XCN | comp1 NPI/customer id, **comp2 internal provider id**, comp3 family, comp4 given | XCN.1 id; **XCN.2 read as last name, XCN.3 as first name** (`parser.service.ts` ~L205) | Low. Names are only used in the `customer_not_found` message, so the message shows the wrong name. Routing uses XCN.1 only. | Only component 1 matters; put the NPI there. Do not ask partners to shift components (we did on 2026-09-23; the spec they hold says otherwise). |
| OBR-26 fasting | Fasting status in OBR-26 | Reads OBR-19 into `fastStatus`; spec's own "Complete Data Flow" step 5 also says OBR-19 | None today: `fastStatus` has no downstream consumer (09-23). | Keep OBR-26 as in the spec. |
| PID-39 email | "Alternative email field" | Not read; email comes only from PID-20.1 | Email lost if sent only in PID-39. | Use PID-20. |
| PID-18 MRN | "`^^^P` suffix is required" | Not read | None. "Required" is overstated. | Optional. |
| DG1 per OBR | Diagnosis codes grouped under each OBR | (09-23) All DG1 in the message are collected into one list for the order | Per-test grouping is lost. | Expected behavior; grouping is not preserved. |
| Customer lookup | <=7 digits -> customer id "in `order_clients`"; multiple matches -> "use first" | <=7 -> `fetchById`, else `fetchByNpi`; gate is `ehr_integrations` (LIVE + ordering) since VP-16968; practice-level match (VP-17827) and provider-clinic check (VP-18402) can reject | Internal detail is stale; the partner-visible rule (NPI in comp1) still holds. | NPI in comp1; the provider must be onboarded on the connection first. |
| File pickup | "File placed in SFTP `/Order/` folder" | Per-vendor path from `sftp_folder_mapping` (e.g. BioInsights `/outgoing/`) | Partner may drop files in the wrong folder. | Give the vendor's actual folder from `sftp_folder_mapping`. |

## Spec value our code ignores (send as the spec says; no action)

| Field | Spec | Code |
|---|---|---|
| MSH-5 / MSH-6 | `IN OFFICE` / `LC`, "Standard / Always for Vibrant" | Not read. Not a draw location. |
| MSH-12 | `2.5` | Not read (integration rows say 2.3; not enforced). |
| OBR-11 | `N` | Read into `obrActionCode`, no consumer. |
| OBR-15 | `0` | Not read. |
| PID-3 | (not in spec) | Not read; external id is PID-2. |

## Consistent

MSH-4 (PracticeFusion only, not re-verified), PID-2, PID-5, PID-7, PID-8, PID-11, PID-13, PID-20, ORC-12.1 / OBR-16.1 routing, OBR-4.1 test code, OBR-7 collection time.

## Not covered by the spec but live behavior a partner hits

- Draw location / kit delivery: not in HL7. Set per provider row (`ehr_integrations.kit_delivery_option`) at onboarding.
- Dedup: a file name is never read twice; resend under a new name. MSH-10 is checked once an `emr_sample` exists.
- Order summary PDF at order time: per vendor, `ehr_vendors.sftp_order_forms_path` (VP-18138).
