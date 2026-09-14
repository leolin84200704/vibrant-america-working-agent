# Phase 0.1 附錄 — trans v1 / v2 全部端點（hits/7d ≥ 100）

> 主報告：`phase0-top20-endpoints.md`。資料窗 2026-09-04T23:20Z → 2026-09-11T23:20Z；peak = 2026-09-11 15:00–19:00Z（週五 08–12 PDT）。
> 來源與查詢方式見主報告 §1。數值為 Datadog trace metrics（`trace.express.request` / `trace.grpc.server` / `trace.graphql.execute`），百分位用 `.rollup(604800)`（peak `.rollup(14400)`）。
> v2 GraphQL 的 endpoint 欄是由完整 query 文字取出的 `<type> <OperationName>`。不含 PHI。

### v1 REST (trace.express.request, service:lis-trans-deployment) — hits/7d >= 100，依 p95×hits 排序（61 個）

| # | endpoint | hits/7d | p50 ms | p95 ms | p99 ms | err % | peak hits (4h) | peak p95 ms |
|---|---|---|---|---|---|---|---|---|
| 1 | `GET /dashboard/user/timeline` | 46,845 | 1,568 | 2,915 | 4,295 | 0.01 | 3,151 | 3,006 |
| 2 | `GET /utility/getSetting` | 310,636 | 190 | 333 | 1,831 | 0.01 | 20,138 | 289 |
| 3 | `POST /trans/findPatient` | 29,189 | 1,016 | 2,826 | 5,254 | 0.00 | 2,346 | 2,782 |
| 4 | `GET /proxy/old-report/downloadTestOrderPDF` | 7,284 | 6,629 | 11,230 | 13,738 | 0.01 | 404 | 11,058 |
| 5 | `GET /trans/patientTestResultnewrange` | 7,335 | 2,310 | 6,135 | 9,180 | 1.87 | 611 | 6,427 |
| 6 | `GET /utility/getUserInfoV2` | 65,090 | 252 | 468 | 1,948 | 0.01 | 4,704 | 420 |
| 7 | `POST /trans/getTimeLine` | 7,115 | 2,171 | 3,403 | 5,947 | 0.20 | 613 | 3,351 |
| 8 | `GET /trans/patientTestKitInfo` | 24,899 | 365 | 843 | 2,535 | 0.00 | 1,622 | 792 |
| 9 | `GET /setting/getPracticeInfo` | 44,828 | 182 | 313 | 1,363 | 0.01 | 3,012 | 244 |
| 10 | `POST /utility/GetSampleInfo` | 36,804 | 96 | 377 | 1,617 | 0.00 | 2,150 | 354 |
| 11 | `POST /valogin/login` | 15,291 | 521 | 733 | 2,870 | 0.02 | 1,072 | 711 |
| 12 | `GET /hubspot/announcements` | 22,096 | 272 | 498 | 599 | 0.00 | 1,392 | 490 |
| 13 | `GET /trans/GenerateBatchReqOrReportV2` | 680 | 7,164 | 13,738 | 15,313 | 0.00 | 40 | 13,114 |
| 14 | `POST /utility/createPatient` | 2,072 | 3,853 | 4,499 | 7,053 | 0.00 | 154 | 4,499 |
| 15 | `GET /trans/patientOrderInfo` | 8,308 | 120 | 1,031 | 2,274 | 0.93 | 667 | 1,186 |
| 16 | `GET /trans/listPatientByPatientId` | 6,807 | 413 | 1,115 | 2,420 | 0.12 | 599 | 1,132 |
| 17 | `GET /utility/ifConfirmAddressV2` | 8,364 | 581 | 856 | 1,694 | 0.31 | 520 | 1,204 |
| 18 | `GET /trans/downloadTestOrderPDF` | 544 | 6,527 | 11,058 | 14,392 | 0.00 | 60 | 10,887 |
| 19 | `GET /portal/bootstrap` | 14,267 | 146 | 401 | 911 | 0.64 | 1,015 | 401 |
| 20 | `GET /proxy/grpc/getKitStatus` | 13,467 | 206 | 401 | 1,115 | 0.00 | 1,175 | 359 |
| 21 | `GET /setting/getAccountInfo` | 16,091 | 215 | 308 | 1,302 | 0.02 | 1,153 | 289 |
| 22 | `GET /trans/listPatientBmi` | 6,852 | 109 | 475 | 1,115 | 0.12 | 600 | 447 |
| 23 | `PUT /utility/updatePatient` | 710 | 1,385 | 4,099 | 5,419 | 0.28 | 67 | 3,794 |
| 24 | `GET /proxy/grpc/getTestStatus` | 6,756 | 163 | 298 | 1,115 | 0.03 | 590 | 338 |
| 25 | `POST /utility/confirmAddress` | 1,541 | 505 | 1,081 | 1,948 | 0.00 | 106 | 1,150 |
| 26 | `GET /utility/getSettingToken` | 6,451 | 120 | 256 | 609 | 0.02 | 377 | 272 |
| 27 | `GET /setting/list-customer-by-id/:clinic_id` | 2,021 | 440 | 733 | 843 | 0.00 | 105 | 581 |
| 28 | `GET /health` | 273,664 | 2 | 5 | 7 | 0.00 | 8,645 | 5 |
| 29 | `GET /setting/getTimezoneSetting` | 15,585 | 49 | 75 | 483 | 0.00 | 1,118 | 72 |
| 30 | `POST /valogin/renewToken` | 41,610 | 10 | 26 | 985 | 0.00 | 3,431 | 23 |
| 31 | `GET /utility/skinCarePreviousOrder` | 5,584 | 43 | 173 | 513 | 0.00 | 405 | 168 |
| 32 | `POST /valogin/adminUserLoginSearch` | 1,883 | 338 | 513 | 2,040 | 0.05 | 121 | 420 |
| 33 | `GET /trans/deep-link/resolve/:token` | 640 | 394 | 1,451 | 3,913 | 0.00 | 55 | 2,239 |
| 34 | `OPTIONS` | 349,341 | 1 | 2 | 3 | 0.00 | 26,912 | 2 |
| 35 | `GET /trans/getUserInfo` | 2,057 | 73 | 348 | 1,918 | 0.05 | 78 | 308 |
| 36 | `POST /valogin/adminLogin` | 1,342 | 365 | 530 | 1,831 | 0.15 | 98 | 433 |
| 37 | `POST /events/samples/get-events` | 6,794 | 47 | 95 | 151 | 0.00 | 591 | 75 |
| 38 | `GET /proxy/grpc/getQuestionaireBySampleId` | 6,760 | 45 | 67 | 196 | 0.00 | 590 | 63 |
| 39 | `GET /setting/getPNSSettingV2` | 2,688 | 53 | 160 | 1,406 | 0.00 | 170 | 111 |
| 40 | `POST /setting/setTimezoneSettingCustomer` | 913 | 240 | 407 | 2,960 | 0.00 | 66 | 382 |
| 41 | `GET /trans/getTNPResult` | 178 | 120 | 1,948 | 3,853 | 1.12 | 20 | 505 |
| 42 | `GET /valogin/transferCustomerClinic` | 1,172 | 171 | 226 | 1,064 | 0.00 | 73 | 226 |
| 43 | `POST /trans/shareQuestionaireNotification` | 128 | 985 | 1,428 | 4,295 | 0.00 | 25 | 1,262 |
| 44 | `GET /utility/getCustomerInfo` | 218 | 149 | 817 | 1,262 | 0.00 | 19 | 1,262 |
| 45 | `POST /valogin/PnsSendCreateAccount2faAuthEmail` | 446 | 260 | 394 | 454 | 0.00 | 21 | 317 |
| 46 | `GET /setting/getUserInformation` | 2,007 | 42 | 76 | 182 | 0.00 | 124 | 76 |
| 47 | `GET /utility/getOrderStatusDisplayNames` | 13,333 | 5 | 11 | 20 | 0.00 | 936 | 10 |
| 48 | `GET /setting/getPracticeInfoApplySetting` | 1,358 | 50 | 92 | 628 | 0.00 | 112 | 98 |
| 49 | `post_/clinicians/first-available` | 193 | 505 | 609 | 609 | 0.00 | 9 | 542 |
| 50 | `POST /clinicians/find-specialties` | 194 | 121 | 440 | 897 | 0.00 | 9 | 348 |
| 51 | `GET /valogin/checkCustomerNPINumber` | 248 | 185 | 317 | 454 | 0.00 | 10 | 203 |
| 52 | `GET /setting/getBillingSetting` | 643 | 55 | 120 | 454 | 0.00 | 46 | 86 |
| 53 | `POST /valogin/listCustomerAllClinics` | 229 | 137 | 276 | 546 | 0.00 | 20 | 377 |
| 54 | `PUT /dashboard/user/events/archive` | 397 | 57 | 131 | 244 | 0.00 | 23 | 142 |
| 55 | `GET /clinicians/scheduling-options` | 284 | 96 | 129 | 196 | 0.00 | 11 | 140 |
| 56 | `GET /setting/getBillingApplySetting` | 258 | 57 | 131 | 182 | 0.00 | 19 | 85 |
| 57 | `GET /utility/getCustomerInvitation` | 181 | 58 | 160 | 163 | 0.00 | 16 | 158 |
| 58 | `GET /trans/listSamplesAccesionID` | 157 | 95 | 163 | 268 | 33.76 | 26 | 144 |
| 59 | `POST /utility/resolveSampleIds` | 166 | 42 | 69 | 69 | 0.00 | 6 | 62 |
| 60 | `GET /utility/checkDuplicatedEmail` | 192 | 41 | 56 | 59 | 0.00 | 14 | 47 |
| 61 | `GET /setting/getSpecificReportPreferSettings` | 619 | - | - | - | 0.00 | 0 | - |

### v1 gRPC server (trace.grpc.server, service:lis-trans-deployment) — hits/7d >= 100，依 p95×hits 排序（2 個）

| # | endpoint | hits/7d | p50 ms | p95 ms | p99 ms | err % | peak hits (4h) | peak p95 ms |
|---|---|---|---|---|---|---|---|---|
| 1 | `/listrans.TransService/GetSampleInfo` | 9,769 | 185 | 2,915 | 3,678 | 0.00 | 0 | - |
| 2 | `/listrans.TransService/GetPatientPageStatus` | 13,093 | 13 | 420 | 1,520 | 0.00 | 0 | - |

### v2 REST (trace.express.request, service:lis-transv2-deployment) — hits/7d >= 100，依 p95×hits 排序（13 個）

| # | endpoint | hits/7d | p50 ms | p95 ms | p99 ms | err % | peak hits (4h) | peak p95 ms |
|---|---|---|---|---|---|---|---|---|
| 1 | `POST /graphql` | 119,413 | 203 | 1,568 | 2,656 | 0.00 | 0 | - |
| 2 | `GET /health` | 409,910 | 1 | 3 | 6 | 0.00 | 0 | - |
| 3 | `GET /setting/getPracticeInfo` | 1,596 | 193 | 317 | 461 | 0.00 | 0 | - |
| 4 | `GET /setting/getAccountInfo` | 1,307 | 236 | 327 | 648 | 0.00 | 0 | - |
| 5 | `GET /setting/getOrderingTestsInfo` | 1,204 | 67 | 112 | 343 | 0.08 | 0 | - |
| 6 | `OPTIONS` | 55,749 | 1 | 2 | 4 | 0.00 | 0 | - |
| 7 | `POST /utility/refreshToken` | 1,838 | 12 | 22 | 371 | 0.00 | 0 | - |
| 8 | `GET /role/clinic-roles` | 122 | 59 | 276 | 388 | 0.00 | 0 | - |
| 9 | `GET /setting/getBillingSetting` | 374 | 59 | 82 | 114 | 0.00 | 0 | - |
| 10 | `POST /utility/exchangeTokenForRefresh` | 1,217 | 15 | 23 | 426 | 0.00 | 0 | - |
| 11 | `GET /setting/getTestResultSetting` | 216 | 56 | 92 | 127 | 0.00 | 0 | - |
| 12 | `GET /utility/criticalReadoutAuthorizedContacts` | 141 | 51 | 64 | 67 | 0.00 | 0 | - |
| 13 | `get_/setting/getpnssettingv2` | 103 | 52 | 76 | 76 | 0.00 | 0 | - |

### v2 GraphQL operations (trace.graphql.execute, service:lis-transv2-deployment) — hits/7d >= 100，依 p95×hits 排序（36 個）

| # | endpoint | hits/7d | p50 ms | p95 ms | p99 ms | err % | peak hits (4h) | peak p95 ms |
|---|---|---|---|---|---|---|---|---|
| 1 | `query PatientProfileSlow` | 6,993 | 1,496 | 3,101 | 4,641 | 1.07 | 602 | 3,101 |
| 2 | `query PatientProfileFast` | 6,989 | 689 | 1,918 | 3,457 | 1.03 | 601 | 1,888 |
| 3 | `query GET_ALL_OTHER_INFO_NEEDED_BY_IDS` | 5,015 | 1,282 | 1,978 | 4,036 | 0.08 | 234 | 1,859 |
| 4 | `query PatientPNS` | 5,065 | 1,262 | 1,747 | 2,383 | 0.04 | 248 | 1,747 |
| 5 | `mutation GetOrCreateCalendar` | 21,969 | 176 | 343 | 538 | 5.89 | 1,411 | 354 |
| 6 | `query GetQuestionnaireRequirements` | 6,657 | 377 | 940 | 1,592 | 0.87 | 580 | 940 |
| 7 | `query GET_ORDER_INFO_DATA_QUERY` | 5,741 | 153 | 679 | 1,242 | 0.00 | 269 | 733 |
| 8 | `query getAllRelatedOrdersByPatientId` | 6,186 | 244 | 433 | 700 | 8.07 | 282 | 440 |
| 9 | `query getBasicAndShippingInfoPageData` | 2,634 | 658 | 1,016 | 2,496 | 0.53 | 181 | 1,343 |
| 10 | `query getPaymentFormPageData` | 2,495 | 609 | 940 | 2,458 | 0.08 | 168 | 870 |
| 11 | `query getPaymentMediaPageData` | 2,303 | 388 | 955 | 1,186 | 0.00 | 146 | 856 |
| 12 | `query checkWhetherOrderIsCanceledViaSample` | 3,082 | 377 | 689 | 1,186 | 4.96 | 202 | 563 |
| 13 | `query getAllIdsAndOrderTypeDataViaSampleId` | 2,522 | 176 | 745 | 1,186 | 0.04 | 168 | 768 |
| 14 | `query getPaymentSucceedPageData` | 1,976 | 196 | 870 | 2,739 | 0.00 | 141 | 830 |
| 15 | `mutation patientGuestLogin` | 5,655 | 193 | 285 | 322 | 0.00 | 290 | 289 |
| 16 | `query GetEvents` | 20,501 | 14 | 51 | 81 | 0.01 | 1,290 | 49 |
| 17 | `query getAllIdsAndOrderRelatedDataViaSampleId` | 2,670 | 129 | 382 | 733 | 0.07 | 186 | 348 |
| 18 | `mutation patientAccountLogin` | 2,855 | 252 | 338 | 394 | 0.00 | 139 | 343 |
| 19 | `query getAllIdsAndOrderSourceViaSampleId` | 1,038 | 131 | 475 | 1,204 | 1.54 | 65 | 420 |
| 20 | `query GetRescheduleAvailability` | 217 | 1,428 | 1,694 | 1,775 | 0.00 | 12 | 1,568 |
| 21 | `mutation SendCreateAccountEmail` | 498 | 388 | 555 | 581 | 0.00 | 23 | 513 |
| 22 | `query GetEvents` | 198 | 546 | 1,204 | 1,223 | 0.00 | 22 | 1,204 |
| 23 | `query getBloodDrawSitePageData` | 1,143 | 131 | 203 | 371 | 0.09 | 77 | 196 |
| 24 | `query getAllIdsAndOrderSourceViaSampleId` | 399 | 365 | 572 | 911 | 1.25 | 25 | 538 |
| 25 | `mutation PatientSendResetPasswordEmail` | 540 | 95 | 401 | 555 | 0.00 | 22 | 317 |
| 26 | `query GET_ALL_OTHER_INFO_NEEDED_BY_IDS` | 102 | 1,385 | 1,948 | 1,948 | 0.00 | 2 | 1,363 |
| 27 | `query GetClinic` | 145 | 870 | 1,132 | 1,888 | 0.00 | 26 | 1,132 |
| 28 | `mutation verifyCreateAccount` | 410 | 327 | 354 | 420 | 0.00 | 20 | 354 |
| 29 | `query GetLabClinicianAvailability` | 264 | 260 | 407 | 756 | 0.00 | 11 | 343 |
| 30 | `mutation patientVerifyInfo` | 955 | 67 | 92 | 173 | 0.00 | 42 | 76 |
| 31 | `{get_oauth_connection_status{__typename calendarId isConnect` | 155 | 14 | 433 | 555 | 6.45 | 26 | 371 |
| 32 | `mutation verifyCreateAccount` | 421 | 42 | 50 | 163 | 0.00 | 22 | 44 |
| 33 | `query IsAccessionClaimable` | 357 | 6 | 16 | 85 | 0.00 | 23 | 9 |
| 34 | `query GetCanceledMeetingRequests` | 147 | 11 | 26 | 43 | 0.00 | 26 | 14 |
| 35 | `query GetPracticeEventTypes` | 141 | 7 | 19 | 61 | 0.00 | 26 | 11 |
| 36 | `query getMeetingRequestsForMe` | 148 | 10 | 14 | 17 | 0.00 | 26 | 12 |
