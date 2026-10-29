---
id: HL7FAIL-20261020-MEDSOMMA-BESTDEAL
type: stm
category: emr_integration
status: blocked
score: 0.0926
base_weight: 1.0
created: 2026-10-20
updated: '2026-10-20'
links: []
unblock_when: BestDeal returns 200 for test_id_list ["337"] (and 338/381/382/383/384/91);
  then bump retry_num on hl7_file_input 7375
---

# hl7_file_input 7375 (medsommaemr, MDHQ) - BestDeal 400 non_existing_test_ids

## Diagnosis (verified 2026-10-20)
- Row 7375: parse_finished=0, retry_num=0, on-prem pod lis-emr-v2-deployment-prod-6577db7cbd-jtkp8. order_input NULL. No Datadog logs for the filename.
- IDs sent are pricing item ids (getLegacyPackagePriceMapping `id`), all isOrderable=true, priceVa only:
  337 RF IgM VATEST115 / 338 Anti-CCP3 VATEST142 / 381 Uric Acid VATEST68 / 382 COQ10-TOT VATEST344 / 383 IGF-1 VATEST517 / 384 Magnesium VATEST27 / 91 ANA IFA Panel VAREQUISTION108.
- Gotcha: lis_core_v7.test.test_id is a different id space (analytes) - matching there gives false "wrong id level" conclusion.
- Live probe from AKS prod pod (VIBRANT_API_TOKEN): [337], [91], full set -> 400; [845], [96], [22] (also VA-only) -> 200. So BestDeal data gap for specific items, same class as PLESSEN 18019. No component split workaround (single items).

## Next
- [2026-10-20] Slack draft to Jiafan Qian (DM D08P4PE9JPP) saved; Leo sends.
- After fix: re-probe, check no manual re-order for the patient, then SET retry_num=3 WHERE id=7375 AND parse_finished=0 AND retry_num=0 (needs write path; MCP MySQL is read-only).
