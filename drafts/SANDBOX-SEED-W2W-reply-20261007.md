# Drafts 2026-10-07 (v2, after VP-18714 shipped to sandbox)

## 1. Reply to the integrator (English, via Chris)

Sandbox orders never pass through our shipping service, so `kit` is null on every sandbox order; only `status` is populated there. We are checking whether a sandbox shipping feed can be set up and will tell you if that changes.

M02: `kit.status` has three values in production: `not_shipped`, `shipped`, `delivered`. There is no `in_transit`. Use M01 for the shipped case and drop M02.

M09/M10: a carrier delivery exception is not a separate value in the payload. Production returns `status` `kit_shipped` (outbound) or `sample_in_transit` (return), `kit.status` `shipped` and the tracking number; the exception itself is only visible on the carrier's tracking page.

M06: not re-seeded yet. We will confirm when it is.

M07: the PDF link now opens with your sandbox key. `presentedForm[].url` points at `https://api-sandbox.vibrant-america.com/v1/report/fhir/{accession}/pdf?style=advanced|classic`, same token as the FHIR call; production uses the same path on `api.vibrant-america.com`. The PDF for M07 itself is not generated on sandbox yet, so the link returns 503 until it is; the FHIR response already carries the full result set for that order.

## 2. Slack to Chris (shipping only)

@Chris 10/5 問 shipping 的那件還沒回：integrator 要 sandbox 單的 kit 區塊（kit.status / carrier / trackingNumber / shippedAt / deliveredAt），這些資料只有 shipping 有，emr-v2 做不出來。需要 shipping 回兩件事之一：
- 可以：staging 的 shipping service 開給 AKS staging 用，並替 2610016001–2610016011 這 11 筆放 PO / tracking 資料
- 不行：我就回 integrator 說 kit 只在 production 有值

哪一邊都好，但要有答案才能回他們。
