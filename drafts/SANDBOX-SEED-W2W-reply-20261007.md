# Drafts 2026-10-07 (v5 — integrator reply covers only what we change in code; kit (shipping) and M06 / M07 PDF build (report team) are their owners' to answer)

## 1. Reply to the integrator (English, via Chris)

M02: `kit.status` has three values: `not_shipped`, `shipped`, `delivered`. There is no `in_transit`. Use M01 for the shipped case and drop M02.

M09/M10: a delivery exception is not a separate value in the payload. You get `status` `kit_shipped` (M09) or `sample_in_transit` (M10), `kit.status` `shipped` and the tracking number; the exception itself is only visible on the carrier's tracking page.

M07: the PDF link now opens with your sandbox key. `presentedForm[].url` points at `https://api-sandbox.vibrant-america.com/v1/report/fhir/{accession}/pdf?style=advanced|classic`, same token as the FHIR call.

## 2. Slack to Chris (shipping)

@Chris 10/5 請 shipping 做的那件要追一下：integrator 要 sandbox 這 11 筆的 kit 區塊（kit.status / carrier / trackingNumber / shippedAt / deliveredAt），資料只有 shipping 有，要請 shipping 替這 11 筆造假的出貨紀錄，並把 staging 的 shipping service 開給 AKS staging 用。我拿到 host/port 就把 staging 的 emr-v2 接上。

每筆要放的狀態（accession 2610016001–2610016011 依序 M01–M11）：
- M01、M11：outbound LAB_SHIPPED_KIT，有 tracking 與 pickup time
- M02：拿掉（沒有 in_transit 這個狀態）
- M03、M06、M07、M08：outbound PATIENT_RECEIVED_KIT
- M04：outbound PATIENT_RECEIVED_KIT，return SAMPLE_SHIPPED_BACK
- M05：return LAB_RECEIVED
- M09：outbound DELIVERY_EXCEPTION
- M10：outbound PATIENT_RECEIVED_KIT，return DELIVERY_EXCEPTION
