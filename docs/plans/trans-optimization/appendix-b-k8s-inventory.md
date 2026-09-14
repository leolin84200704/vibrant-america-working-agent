# Appendix B — AKS read-only inventory (2026-09-11; transv2 `checkIfPersonalizedReportCanBeCreated` baseline updated 2026-09-14 after Phase 1.1)

> Source: kubectl (context lisportalprod), read-only. Values reduced to scheme://host[:port]/first-3-path-segments; no secrets, no query strings.
> Buckets: 'cloud-local-proxy' = value host is the proxy svc; 'onprem 192.168.*' = on-prem address; 'public api.vibrant-*' = public ingress hostname; 'in-cluster svc' = *.svc.cluster.local.

```

=============== ConfigMap default/lis-trans-config
  total keys: 154 | url/address-valued keys: 96
  -- cloud-local-proxy: 0
  -- onprem 192.168.*: 15
     Get_Requisition -> http://192.168.60.77:8081/secure/nologin/FetchScannedRequisition
     KAFKA_BROKER_carlos1 -> 192.168.60.9:9095
     KAFKA_BROKER_carlos2 -> 192.168.60.10:9095
     REDIS_ADDR -> 192.168.60.9
     SETTING_TO_DASHBOARD_RPC -> 192.168.60.6:30266
     checkIfPersonalizedReportCanBeCreated -> http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated
     consul_node -> 192.168.60.6
     oneClickPersonalizedReport -> http://192.168.60.77:8081/secure/nologin/OneClickPersonalizedReport
     url_GenerateBatchReqOrReportV2 -> http://192.168.60.77:8081/secure/nologin/GenerateBatchReqOrReportV2
     url_GenerateOnlineZipDownloadV2 -> http://192.168.60.77:8081/secure/nologin/GenerateOnlineZipDownloadV2
     url_GenerateOnlineZipDownloadV2_generateOnlineZipNoJWT -> http://192.168.60.77:8081/secure/nologin/GenerateOnlineZipDownloadV2
     url_GetSpecificReports -> http://192.168.60.77:8081/secure/nologin/patient_results
     url_downloadTestOrderPDF -> http://192.168.60.77:8081/secure/nologin/downloadTestOrderPD
     url_generateOnlineSummaryReport -> http://192.168.60.77:8081/secure/nologin/generateOnlineSummaryReport
     url_get_product_report -> http://192.168.60.77:8081/secure/nologin/GenerateOnlineReport
  -- public api.vibrant-*: 55
     CHARGE_INFO_URL -> https://api.vibrant-wellness.com/v1/lis/accounting
     CHART_NOTE_ENDPOINT -> https://www.vibrant-america.com/lisapi/v1/lis
     GET_SETTING_URL -> https://api.vibrant-wellness.com/v1/portal/trans-service
     GOOGLE_REDIRECT_URL -> https://portal.vibrant-wellness.com
     Get_Requisitionv2 -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     Get_product_report_map -> https://api.vibrant-wellness.com/v1/lis/base-report-service
     NutriProZ -> https://api.vibrant-wellness.com/v1/lis/interactive-report-service
     OAUTH2_TOKEN_ENDPOINT -> https://api.vibrant-wellness.com/v1/oauth2/token
     PNS_BASE_URL -> https://pns.vibrant-wellness.com
     ZOOM_API_URL -> https://www.vibrant-america.com/lisapi/v1/lis
     billing_detail -> https://api.vibrant-wellness.com/v2/accounting/charge
     dashboard_noti -> https://www.vibrant-america.com/secure/nologin/SendDashboardContent
     full_test_mapping -> https://api.vibrant-wellness.com/v1/lis/base-report-service
     getKitStatusV2 -> https://api.vibrant-wellness.com/v1/lis/samples
     getOrderRecept -> https://api.vibrant-wellness.com/v2/accounting/statement
     getReportStatusListV2 -> https://api.vibrant-wellness.com/v1/lis/base-report-service
     getReportStatusListV2Batch -> https://api.vibrant-wellness.com/v1/lis/base-report-service
     getReportStatusListV2WithInteractiveProducts -> https://api.vibrant-wellness.com/v1/lis/base-report-service
     getSubmittedBarcodesInfo_questionnaire -> https://api.vibrant-wellness.com/v1/lis/interactive-report-service
     getinvoice -> https://api.vibrant-wellness.com/v1/accounting/charge
     inventory_url -> https://api.vibrant-wellness.com/v1/lis/shipping
     inventory_url_skin -> https://api.vibrant-wellness.com/v1/lis/shipping
     oauth_url -> https://api.vibrant-wellness.com/v1/oauth2/token
     pdf_cache_download_url -> https://api.vibrant-wellness.com/v1/lis/base-report-service
     proxy_getQuestionaire -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     proxy_getTnpCode -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     proxy_getkit -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     proxy_getresult -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     proxy_getteststatus -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     questionnaire_status -> https://api.vibrant-wellness.com/v1/lis/interactive-report-service
     report_finish_time -> https://api.vibrant-wellness.com/v1/lis/base-report-service
     sample_url -> https://api.vibrant-wellness.com/v1/lis/samples
     sentry_dsn -> https://sentry1.vibrant-america.com/13
     shippin_address -> https://api.vibrant-wellness.com/v1/lis/shipping
     shipping_collection_status -> https://api.vibrant-wellness.com/v1/lis/shipping
     skin_placepatientorders -> https://www.vibrant-america.com/crmapi/placepatientorders
     skin_questions_data_getAnswer -> https://api.vibrant-wellness.com/v1/lis/interactive-report-service
     skin_questions_data_template_questions -> https://api.vibrant-wellness.com/v1/lis/interactive-report-service
     transaction -> https://api.vibrant-wellness.com/v1/charging/transaction
     url_GenerateBatchReqOrReportV2_new -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     url_GenerateOnlineZipDownloadV2_new -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     url_GenerateProducctSummaryReport -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     url_GetSpecificReportsv2 -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     url_downloadTestOrderPDFv2 -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     url_generateOnlineSummaryReportv2 -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     url_generateOnlineZipNoJWT -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     url_getCompleteReport -> https://www.vibrant-america.com/patient-portal-backend/receive-result/fetch
     url_getOrderSummaryReport -> https://www.vibrant-america.com/patient-portal-backend/ordersummary/fetch
     url_getPatientVerification -> https://www.vibrant-america.com/patient-portal-backend/patient-verification/token
     url_get_product_report1 -> https://api.vibrant-america.com/v1/report-pdf-engine/pdf
     url_get_product_reportv2 -> https://api.vibrant-america.com/v1/lis/cloud-proxy
     url_order_summary_new -> https://api.vibrant-wellness.com/v1/portal/order
     url_order_summary_new_redraw -> https://api.vibrant-wellness.com/v1/portal/order
     url_patientVerification -> https://www.vibrant-america.com/patient-portal-backend/patient-verification/verify
     va_events -> https://api.vibrant-wellness.com/v1/portal/calendar
  -- in-cluster svc: 24
     ACCOUNTING_BASE_URL -> http://lis-accounting-service.bkkeeping.svc.cluster.local:8084/v2/accounting
     AUDIT_RPC -> lis-auditlog-grpc-service.default.svc.cluster.local:30113
     CORE_RPC_STAGE -> lis-core-grpc-service.default.svc.cluster.local:30113
     CORE_SAMPLE_V2_RPC -> lis-coresamples-v2-service.coresamplesv2.svc.cluster.local:8084
     DASHBOARD_RPC -> lis-dashboard-prod-rpc-service.default.svc.cluster.local:5800
     GET_ORDER_CARLOS -> http://lis-order.default.svc.cluster.local:4242/orderTest/orderV2
     GET_ORDER_details_CARLOS -> http://lis-order.default.svc.cluster.local:4242/orderTest/orderTestDetails
     GET_ORDER_kit_CARLOS -> http://lis-order.default.svc.cluster.local:4242/orderTest/orderKitInfo
     GET_ORDER_non_batch_CARLOS -> http://lis-order.default.svc.cluster.local:4242/orderTest/order
     GET_ORDER_tube -> http://lis-order.default.svc.cluster.local:4242/nonBloodSampleTubeType
     ISSUE_RPC -> lis-issue-system-service.issue.svc.cluster.local:30071
     LAB_TEST_RPC -> lis-test-service.lis-test.svc.cluster.local:8084
     LOG_IN_VIA_SESSION -> http://lis-core-http-service.default.svc.cluster.local:30112/api/user/login_via_session
     SHIPPING_RPC -> lis-shipping-service-grpc.shipping.svc.cluster.local:63142
     TEST_RESULT_RPC -> lis-test-connect-grpc-service.results.svc.cluster.local:6889
     create_patient -> http://lis-core-http-service.default.svc.cluster.local:30112/api/patient/create-patient
     create_patientv2 -> http://lis-core-http-service.default.svc.cluster.local:30112/api/patient/create-patient-new
     getOrderItemsAndHistory -> http://lis-order.default.svc.cluster.local:4242/orderTest/orderItemsAndHistory
     getProviderAndClinicName -> http://lis-order.default.svc.cluster.local:4242/patientPage/getProviderAndClinicName
     getQuestionnaireRequiredMap -> http://lis-order.default.svc.cluster.local:4242/orderTest/getQuestionnaireRequiredMap
     list_customer_by_id_carlos -> http://lis-core-http-service.default.svc.cluster.local:30112/api/clinic/list-customer-by-id
     orderv2mini -> http://lis-order.default.svc.cluster.local:4242/orderTest/orderV2mini
     tnp_rpc -> lis-test-connect-grpc-service.results.svc.cluster.local:6889
     url_packageOldAndNewNameMapping -> http://lis-order.default.svc.cluster.local:4242/mapping/packageOldAndNewNameMapping
  -- other: 2
     Azure_kafka_host -> vibrant-notification-events.servicebus.windows.net:9093
     Azure_kafka_host_gen -> general-events.servicebus.windows.net:9093

=============== ConfigMap default/lis-trans-config-st
  total keys: 165 | url/address-valued keys: 100
  -- cloud-local-proxy: 0
  -- onprem 192.168.*: 23
     Get_Requisition -> http://192.168.10.153:8081/secure/nologin/FetchScannedRequisition
     KAFKA_BROKER_carlos1 -> 192.168.60.9:9095
     KAFKA_BROKER_carlos2 -> 192.168.60.10:9095
     REDIS_ADDR -> 192.168.60.10
     SETTING_TO_DASHBOARD_RPC -> 192.168.60.6:30266
     SHIPPING_RPC -> 192.168.60.6:31865
     TEST_RESULT_RPC -> 192.168.60.6:30600
     checkIfPersonalizedReportCanBeCreated -> http://192.168.10.153:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated
     consul_node -> 192.168.60.6
     getProviderAndClinicName -> http://192.168.10.214:14243/patientPage/getProviderAndClinicName
     getQuestionnaireRequiredMap -> http://192.168.10.214:14243/orderTest/getQuestionnaireRequiredMap
     getinvoice -> http://192.168.60.6/v1/accounting/staging
     inventory_url -> http://192.168.60.6/v1/lis/inventory-dev-http
     oneClickPersonalizedReport -> http://192.168.10.153:8081/secure/nologin/OneClickPersonalizedReport
     sample_url -> http://192.168.60.6/v1/lis/sample-dev
     tnp_rpc -> 192.168.60.6:30600
     url_GenerateBatchReqOrReportV2 -> http://192.168.10.153:8081/secure/nologin/GenerateBatchReqOrReportV2
     url_GenerateOnlineZipDownloadV2 -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineZipDownloadV2
     url_GenerateOnlineZipDownloadV2_generateOnlineZipNoJWT -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineZipDownloadV2
     url_GetSpecificReports -> http://192.168.10.153:8081/secure/nologin/patient_results
     url_downloadTestOrderPDF -> http://192.168.10.153:8081/secure/nologin/downloadTestOrderPDF
     url_generateOnlineSummaryReport -> http://192.168.10.153:8081/secure/nologin/generateOnlineSummaryReport
     url_get_product_report -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineReport
  -- public api.vibrant-*: 50
     CHARGE_INFO_URL -> https://api.vibrant-wellness.com/v1/lis/accounting
     CHART_NOTE_ENDPOINT -> https://www.vibrant-america.com/lisapi/v1/lis
     GET_ORDER_tube -> https://api.vibrant-wellness.com/v1/portal/order
     GET_SETTING_URL -> https://api.vibrant-wellness.com/v1/portal/trans-service-st
     Get_Requisitionv2 -> https://www.vibrant-america.com/lisapi/v1/lis
     Get_product_report_map -> https://api.vibrant-wellness.com/v1/lis/base-report-staging-service
     NutriProZ -> https://www.vibrant-america.com/lisapi/v1/lis
     OAUTH2_TOKEN_ENDPOINT -> https://api.vibrant-wellness.com/v1/oauth2/staging
     ZOOM_API_URL -> https://www.vibrant-america.com/lisapi/v1/lis
     ZOOM_REDIRECT_URI -> https://www.vibrant-america.com/lisapi/v1/lis
     billing_detail -> https://api.vibrant-wellness.com/v2/accounting/staging
     dashboard_noti -> https://www.vibrant-america.com/secure/nologin/SendDashboardContent
     full_test_mapping -> https://api.vibrant-wellness.com/v1/lis/base-report-staging-service
     getKitStatusV2 -> https://www.vibrant-america.com/lisapi/v1/lis
     getOrderRecept -> https://api.vibrant-wellness.com/v2/accounting/staging
     getReportStatusListV2 -> https://api.vibrant-wellness.com/v1/lis/base-report-staging-service
     getReportStatusListV2Batch -> https://api.vibrant-wellness.com/v1/lis/base-report-staging-service
     getReportStatusListV2WithInteractiveProducts -> https://api.vibrant-wellness.com/v1/lis/base-report-staging-service
     getSubmittedBarcodesInfo_questionnaire -> https://www.vibrant-america.com/lisapi/v1/lis
     inventory_url_skin -> https://www.vibrant-america.com/lisapi/v1/lis
     oauth_url -> https://api.vibrant-wellness.com/v1/oauth2/staging
     pdf_cache_download_url -> https://api.vibrant-wellness.com/v1/lis/base-report-staging-service
     proxy_getQuestionaire -> https://www.vibrant-america.com/lisapi/v1/lis
     proxy_getTnpCode -> https://www.vibrant-america.com/lisapi/v1/lis
     proxy_getkit -> https://www.vibrant-america.com/lisapi/v1/lis
     proxy_getresult -> https://www.vibrant-america.com/lisapi/v1/lis
     proxy_getteststatus -> https://www.vibrant-america.com/lisapi/v1/lis
     questionnaire_status -> https://www.vibrant-america.com/lisapi/v1/lis
     report_finish_time -> https://api.vibrant-wellness.com/v1/lis/base-report-staging-service
     sentry_dsn -> https://sentry1.vibrant-america.com/13
     shippin_address -> https://api.vibrant-wellness.com/v1/lis/shipping
     shipping_collection_status -> https://www.vibrant-america.com/lisapi/v1/lis
     skin_placepatientorders -> https://www.vibrant-america.com/crmapi/placepatientorders
     skin_questions_data_getAnswer -> https://api.vibrant-wellness.com/v1/lis/interactive-report-staging-service
     skin_questions_data_template_questions -> https://www.vibrant-america.com/lisapi/v1/lis
     transaction -> https://www.vibrant-america.com/lisapi/v1/charging
     url_GenerateBatchReqOrReportV2_new -> https://www.vibrant-america.com/lisapi/v1/lis
     url_GenerateOnlineZipDownloadV2_new -> https://www.vibrant-america.com/lisapi/v1/lis
     url_GenerateProducctSummaryReport -> https://www.vibrant-america.com/lisapi/v1/lis
     url_GetSpecificReportsv2 -> https://www.vibrant-america.com/lisapi/v1/lis
     url_downloadTestOrderPDFv2 -> https://www.vibrant-america.com/lisapi/v1/lis
     url_generateOnlineSummaryReportv2 -> https://www.vibrant-america.com/lisapi/v1/lis
     url_generateOnlineZipNoJWT -> https://www.vibrant-america.com/lisapi/v1/lis
     url_getCompleteReport -> https://www.vibrant-america.com/patient-portal-backend/receive-result/fetch
     url_getOrderSummaryReport -> https://www.vibrant-america.com/patient-portal-backend/ordersummary/fetch
     url_getPatientVerification -> https://www.vibrant-america.com/patient-portal-backend/patient-verification/token
     url_get_product_report1 -> https://www.vibrant-america.com/lisapi/v1/lis
     url_get_product_reportv2 -> https://www.vibrant-america.com/lisapi/v1/lis
     url_patientVerification -> https://www.vibrant-america.com/patient-portal-backend/patient-verification/verify
     va_events -> https://www.vibrant-america.com/lisapi/v1/lis
  -- in-cluster svc: 20
     ACCOUNTING_BASE_URL -> http://lis-accounting-service-staging.bkkeeping.svc.cluster.local:8084/v2/accounting
     AUDIT_RPC -> lis-auditlog-grpc-service-staging.default.svc.cluster.local:30117
     CORE_RPC_STAGE -> lis-core-staging-grpc-service.default.svc.cluster.local:30115
     CORE_SAMPLE_V2_RPC -> lis-coresamples-v2-service-staging.coresamplesv2.svc.cluster.local:8084
     DASHBOARD_RPC -> lis-dashboard-st-rpc-service.default.svc.cluster.local:5800
     GET_ORDER_CARLOS -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderV2
     GET_ORDER_details_CARLOS -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderTestDetails
     GET_ORDER_kit_CARLOS -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderKitInfo
     GET_ORDER_non_batch_CARLOS -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/order
     ISSUE_RPC -> lis-issue-system-service-staging.issue.svc.cluster.local:30072
     LAB_TEST_RPC -> lis-test-service.lis-test.svc.cluster.local:8084
     LOG_IN_VIA_SESSION -> http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/user/login_via_session
     create_patient -> http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/patient/create-patient
     create_patientv2 -> http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/patient/create-patient-new
     getOrderItemsAndHistory -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderItemsAndHistory
     list_customer_by_id_carlos -> http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/clinic/list-customer-by-id
     orderv2mini -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderV2mini
     url_order_summary_new -> http://lis-order-dev.lis-order.svc.cluster.local:14242/patientPage/generateNormalOrderPdf
     url_order_summary_new_redraw -> http://lis-order-dev.lis-order.svc.cluster.local:14242/patientPage/generateRedrawOrderPdf
     url_packageOldAndNewNameMapping -> http://lis-order-dev.lis-order.svc.cluster.local:14242/mapping/packageOldAndNewNameMapping
  -- other: 7
     Azure_kafka_host -> vibrant-notification-events.servicebus.windows.net:9093
     Azure_kafka_host_gen -> general-events.servicebus.windows.net:9093
     GOOGLE_BASE_URL -> https://accounts.google.com/o/oauth2/v2
     GOOGLE_REDIRECT_URI -> https://staging.va-portal.pages.dev
     GOOGLE_REDIRECT_URL -> https://staging.va-portal.pages.dev
     PNS_BASE_URL -> https://staging.pns-singlepage.pages.dev
     ZOOM_BASE_URL -> https://zoom.us/oauth/authorize

=============== ConfigMap transv2/lis-transv2-config
  total keys: 152 | url/address-valued keys: 89
  -- cloud-local-proxy: 1
     checkIfPersonalizedReportCanBeCreated -> http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated  [changed 2026-09-14 Phase 1.1; was cloud-local-proxy-service.cloud-local.svc.cluster.local:3047/old-report/...]
  -- onprem 192.168.*: 12
     Get_Requisition -> http://192.168.10.153:8081/secure/nologin/FetchScannedRequisition
     KAFKA_BROKER_carlos1 -> 192.168.60.9:9095
     KAFKA_BROKER_carlos2 -> 192.168.60.10:9095
     SETTING_TO_DASHBOARD_RPC -> 192.168.60.6:30266
     consul_node -> 192.168.60.6
     url_GenerateBatchReqOrReportV2 -> http://192.168.10.153:8081/secure/nologin/GenerateBatchReqOrReportV2
     url_GenerateOnlineZipDownloadV2 -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineZipDownloadV2
     url_GenerateOnlineZipDownloadV2_generateOnlineZipNoJWT -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineZipDownloadV2
     url_GetSpecificReports -> http://192.168.10.153:8081/secure/nologin/patient_results
     url_downloadTestOrderPDF -> http://192.168.10.153:8081/secure/nologin/downloadTestOrderPDF
     url_generateOnlineSummaryReport -> http://192.168.10.153:8081/secure/nologin/generateOnlineSummaryReport
     url_get_product_report -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineReport
  -- public api.vibrant-*: 13
     CALENDAR_CHART_NOTE_ENDPOINT -> https://www.vibrant-america.com/lisapi/v1/lis
     MYPRACTICE_CHAT_METRICS_BASE_URL -> https://api.vibrant-wellness.com/v1/ehr/chat
     MYPRACTICE_FORM_METRICS_BASE_URL -> https://api.vibrant-wellness.com/v1/ehr/file
     PNS_BASE_URL -> https://pns.vibrant-wellness.com
     WEBHOOK_BASE_URL -> https://api.vibrant-america.com/v2/portal/trans-service
     ZOOM_API_URL -> https://api.vibrant-wellness.com/lis-sure-script/zoom
     ZOOM_REDIRECT_URI -> https://api.vibrant-wellness.com/lis-sure-script/routing
     dashboard_noti -> https://www.vibrant-america.com/secure/nologin/SendDashboardContent
     sentry_dsn -> https://sentry1.vibrant-america.com/13
     url_getCompleteReport -> https://www.vibrant-america.com/patient-portal-backend/receive-result/fetch
     url_getOrderSummaryReport -> https://www.vibrant-america.com/patient-portal-backend/ordersummary/fetch
     url_getPatientVerification -> https://www.vibrant-america.com/patient-portal-backend/patient-verification/token
     url_patientVerification -> https://www.vibrant-america.com/patient-portal-backend/patient-verification/verify
  -- in-cluster svc: 49
     AUDIT_RPC -> lis-auditlog-grpc-service.default.svc.cluster.local:30113
     CORE_RPC_STAGE -> lis-core-grpc-service.default.svc.cluster.local:30113
     CORE_SAMPLE_V2_RPC -> lis-coresamples-v2-service.coresamplesv2.svc.cluster.local:8084
     DASHBOARD_RPC -> lis-dashboard-prod-rpc-service.default.svc.cluster.local:5800
     GET_ORDER_CARLOS -> http://lis-order.default.svc.cluster.local:4242/orderTest/orderV2
     GET_ORDER_details_CARLOS -> http://lis-order.default.svc.cluster.local:4242/orderTest/orderTestDetails
     ISSUE_RPC -> lis-issue-system-service.issue.svc.cluster.local:30071
     LOG_IN_VIA_SESSION -> http://lis-core-http-service.default.svc.cluster.local:30112/api/user/login_via_session
     NutriProZ -> http://lis-interactive-report.report.svc.cluster.local:30900/report-data/getResultZoneInOut
     OAUTH2_TOKEN_ENDPOINT -> http://oauth-service.oauth.svc.cluster.local:8000/token
     OAUTH_SERVICE_BASE_URL -> http://oauth-service.oauth.svc.cluster.local:8000
     SHIPPING_RPC -> lis-shipping-service-grpc.shipping.svc.cluster.local:63142
     TEST_RESULT_RPC -> lis-test-connect-grpc-service.results.svc.cluster.local:6889
     create_patient -> http://lis-core-http-service.default.svc.cluster.local:30112/api/patient/create-patient
     create_patientv2 -> http://lis-core-http-service.default.svc.cluster.local:30112/api/patient/create-patient-new
     fedx_shipments -> http://lis-shipping-service.shipping.svc.cluster.local:16256/shipments/status
     getQuestionnaireRequiredMap -> http://lis-order.default.svc.cluster.local:4242/orderTest/getQuestionnaireRequiredMap
     getReportStatusListV2 -> http://lis-base-report.report.svc.cluster.local:30800/result/getReportStatusListV2
     getReportStatusListV2WithInteractiveProducts -> http://lis-base-report.report.svc.cluster.local:30800/result/getReportStatusListV2WithInteractiveProducts
     getSetting -> http://lis-trans-service.default.svc.cluster.local:3146/utility/getSetting
     get_check_shipping_address -> http://lis-shipping-service.shipping.svc.cluster.local:16256/orders/samples/kits
     get_getCountryList -> http://lis-pricing-service.pricing.svc.cluster.local:8099/shipping/getCountryList
     get_pns_charge_type -> http://lis-accounting-service.bkkeeping.svc.cluster.local:8084/v1/accounting/charge
     get_pns_confirm_address -> http://lis-shipping-service.shipping.svc.cluster.local:16256/orders/samples/shipping-address
     get_pns_info -> http://lis-order.default.svc.cluster.local:4242/orderTest/patient
     get_pns_invoice -> http://lis-accounting-service.bkkeeping.svc.cluster.local:8084/v1/accounting/charge
     get_pns_kit_status -> http://lis-sample-service.sample.svc.cluster.local:16300/patients/v2/kits
     get_pns_questionnaire_required_map -> http://lis-order.default.svc.cluster.local:4242/orderTest/getQuestionnaireRequiredMap
     get_pns_sample_status -> http://lis-sample-service.sample.svc.cluster.local:16300/status
     get_setting -> http://lis-trans-service.default.svc.cluster.local:3146/utility/getSetting
     get_setting_tokne -> http://lis-trans-service.default.svc.cluster.local:3146/utility/getSettingToken
     get_single_merchandise -> http://lis-pricing-service.pricing.svc.cluster.local:8099/merchandise/getSingleMerchandise
     get_transaction -> http://lis-charging-service.charging.svc.cluster.local:8084/v1/charging/transaction
     inventory_url -> http://lis-shipping-service.shipping.svc.cluster.local:16256
     list_customer_by_id_carlos -> http://lis-core-http-service.default.svc.cluster.local:30112/api/clinic/list-customer-by-id
     nutriproz_shipping -> http://lis-interactive-report.report.svc.cluster.local:30900/admin-page/patientList
     orderv2mini -> http://lis-order.default.svc.cluster.local:4242/orderTest/orderV2mini
     proxy_getQuestionaire -> http://lis-trans-service.default.svc.cluster.local:3146/proxy/grpc/getQuestionaireBySampleId
     proxy_getkit -> http://lis-trans-service.default.svc.cluster.local:3146/proxy/grpc/getKitStatus
     proxy_getteststatus -> http://lis-trans-service.default.svc.cluster.local:3146/proxy/grpc/getTestStatus
     questionnaire_status -> http://lis-interactive-report.report.svc.cluster.local:30900/questions-data/getBarcodeQuestionnairesStatus
     report_finish_time -> http://lis-base-report.report.svc.cluster.local:30800/result/v1ReportGenerationTime
     sample_url -> http://lis-sample-service.sample.svc.cluster.local:16300
     shippin_address -> http://lis-shipping-service.shipping.svc.cluster.local:16256
     shipping_collection_status -> http://lis-shipping-service.shipping.svc.cluster.local:16256/orders/samples/collection-status
     skin_placepatientorders -> http://lis-trans-service.default.svc.cluster.local:3146/proxy/grpc/sendSkinPlacePatientOrders
     skin_questions_data_getAnswer -> http://lis-interactive-report.report.svc.cluster.local:30900/questions-data/getAnswer
     transaction -> http://lis-charging-service.charging.svc.cluster.local:8084/v1/charging/transaction
     va_events -> http://lis-trans-service.default.svc.cluster.local:3146/events/samples/get-events
  -- other: 14
     Azure_kafka_general_events -> general-events.servicebus.windows.net:9093
     Azure_kafka_notification_url -> vibrant-notification-events.servicebus.windows.net:9093
     GOOGLE_BASE_URL -> https://accounts.google.com/o/oauth2/v2
     GOOGLE_REDIRECT_URI -> https://staging.va-portal.pages.dev
     MYPRACTICE_AZURE_OPENAI_ENDPOINT -> https://vi-encounter-notes-resource.cognitiveservices.azure.com/openai/responses
     OUTLOOK_REDIRECT_URL -> https://staging.va-portal.pages.dev/oauth/outlook-web
     PUBLICBOOKING_GOOGLE_REDIRECT_URI -> https://vibrant-wellness.mypatienthubs.com
     VA_QUESTIONNAIRE_URL -> https://questionnaire.regenere.com/#
     ZOOM_BASE_URL -> https://zoom.us/oauth/authorize
     appConfigEndpoint -> https://portal-config-center.azconfig.io
     azureRedisToken -> https://redis.azure.com/.default
     keyVaultUri -> https://jwt-rsa-private.vault.azure.net
     pre_test_conditions_instructions -> https://api.hubapi.com/cms/v3/hubdb
     product_sample_type -> https://api.hubapi.com/cms/v3/hubdb

=============== ConfigMap transv2/lis-transv2-config-st
  total keys: 153 | url/address-valued keys: 89
  -- cloud-local-proxy: 0
  -- onprem 192.168.*: 16
     Get_Requisition -> http://192.168.10.153:8081/secure/nologin/FetchScannedRequisition
     KAFKA_BROKER_carlos1 -> 192.168.60.9:9095
     KAFKA_BROKER_carlos2 -> 192.168.60.10:9095
     SETTING_TO_DASHBOARD_RPC -> 192.168.60.6:30266
     SHIPPING_RPC -> 192.168.60.6:31865
     TEST_RESULT_RPC -> 192.168.60.6:30600
     consul_node -> 192.168.60.6
     inventory_url -> http://192.168.60.6/v1/lis/inventory-dev-http
     sample_url -> http://192.168.60.6/v1/lis/sample-dev
     url_GenerateBatchReqOrReportV2 -> http://192.168.10.153:8081/secure/nologin/GenerateBatchReqOrReportV2
     url_GenerateOnlineZipDownloadV2 -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineZipDownloadV2
     url_GenerateOnlineZipDownloadV2_generateOnlineZipNoJWT -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineZipDownloadV2
     url_GetSpecificReports -> http://192.168.10.153:8081/secure/nologin/patient_results
     url_downloadTestOrderPDF -> http://192.168.10.153:8081/secure/nologin/downloadTestOrderPDF
     url_generateOnlineSummaryReport -> http://192.168.10.153:8081/secure/nologin/generateOnlineSummaryReport
     url_get_product_report -> http://192.168.10.153:8081/secure/nologin/GenerateOnlineReport
  -- public api.vibrant-*: 17
     CALENDAR_CHART_NOTE_ENDPOINT -> https://www.vibrant-america.com/lisapi/v1/lis
     MYPRACTICE_FORM_METRICS_BASE_URL -> https://www.vibrant-america.com/lisapi/v1/ehr
     WEBHOOK_BASE_URL -> https://api.vibrant-america.com/v2/portal/trans-service-st
     ZOOM_API_URL -> https://www.vibrant-america.com/lisapi/v1/lis
     ZOOM_REDIRECT_URI -> https://api.vibrant-wellness.com/lis-sure-script-staging/routing
     checkIfPersonalizedReportCanBeCreated -> http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated  [changed 2026-09-14 Phase 1.1; was https://www.vibrant-america.com/lisapi/v1/lis/cloud-proxy-st/old-report/...]
     dashboard_noti -> https://www.vibrant-america.com/secure/nologin/SendDashboardContent
     fedx_shipments -> https://www.vibrant-america.com/lisapi/v1/lis
     get_check_shipping_address -> https://www.vibrant-america.com/lisapi/v1/lis
     sentry_dsn -> https://sentry1.vibrant-america.com/13
     shippin_address -> https://www.vibrant-america.com/lisapi/v1/lis
     shipping_collection_status -> https://www.vibrant-america.com/lisapi/v1/lis
     url_getCompleteReport -> https://www.vibrant-america.com/patient-portal-backend/receive-result/fetch
     url_getOrderSummaryReport -> https://www.vibrant-america.com/patient-portal-backend/ordersummary/fetch
     url_getPatientVerification -> https://www.vibrant-america.com/patient-portal-backend/patient-verification/token
     url_patientVerification -> https://www.vibrant-america.com/patient-portal-backend/patient-verification/verify
     va_events -> https://www.vibrant-america.com/lisapi/v1/lis
  -- in-cluster svc: 41
     AUDIT_RPC -> lis-auditlog-grpc-service-staging.default.svc.cluster.local:30117
     CORE_RPC_STAGE -> lis-core-staging-grpc-service.default.svc.cluster.local:30115
     CORE_SAMPLE_V2_RPC -> lis-coresamples-v2-service-staging.coresamplesv2.svc.cluster.local:8084
     DASHBOARD_RPC -> lis-dashboard-st-rpc-service.default.svc.cluster.local:5800
     GET_ORDER_CARLOS -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderV2
     GET_ORDER_details_CARLOS -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderTestDetails
     ISSUE_RPC -> lis-issue-system-service-staging.issue.svc.cluster.local:30072
     LOG_IN_VIA_SESSION -> http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/user/login_via_session
     MYPRACTICE_CHAT_METRICS_BASE_URL -> http://ehr-chat-service.ehr-chat-staging.svc.cluster.local:3000
     NutriProZ -> http://lis-interactive-report-staging.report.svc.cluster.local:30901/report-data/getResultZoneInOut
     OAUTH2_TOKEN_ENDPOINT -> http://oauth-staging-service.oauth-staging.svc.cluster.local:8000/token
     OAUTH_SERVICE_BASE_URL -> http://oauth-staging-service.oauth-staging.svc.cluster.local:8000
     create_patient -> http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/patient/create-patient
     create_patientv2 -> http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/patient/create-patient-new
     getQuestionnaireRequiredMap -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/getQuestionnaireRequiredMap
     getReportStatusListV2 -> http://lis-base-report-dev.report.svc.cluster.local:30802/result/getReportStatusListV2
     getReportStatusListV2WithInteractiveProducts -> http://lis-base-report-dev.report.svc.cluster.local:30802/result/getReportStatusListV2WithInteractiveProducts
     getSetting -> http://lis-trans-service-st.default.svc.cluster.local:3147/utility/getSetting
     get_getCountryList -> http://lis-pricing-service.pricing.svc.cluster.local:8099/shipping/getCountryList
     get_pns_charge_type -> http://lis-accounting-service-staging.bkkeeping.svc.cluster.local:8084/v1/accounting/staging
     get_pns_confirm_address -> http://lis-shipping-service-staging.shipping.svc.cluster.local:16256/orders/samples/shipping-address
     get_pns_info -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/patient
     get_pns_invoice -> http://lis-accounting-service-staging.bkkeeping.svc.cluster.local:8084/v1/accounting/staging
     get_pns_kit_status -> http://lis-sample-service-staging.sample.svc.cluster.local:16300/patients/v2/kits
     get_pns_questionnaire_required_map -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/getQuestionnaireRequiredMap
     get_pns_sample_status -> http://lis-sample-service-staging.sample.svc.cluster.local:16300/status
     get_setting -> http://lis-trans-service-st.default.svc.cluster.local:3147/utility/getSetting
     get_setting_tokne -> http://lis-trans-service-st.default.svc.cluster.local:3147/utility/getSettingToken
     get_single_merchandise -> http://lis-pricing-service-staging.pricing.svc.cluster.local:8098/merchandise/getSingleMerchandise
     get_transaction -> http://lis-charging-service-staging.charging.svc.cluster.local:8084/v1/charging/staging
     list_customer_by_id_carlos -> http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/clinic/list-customer-by-id
     nutriproz_shipping -> http://lis-interactive-report-staging.report.svc.cluster.local:30901/admin-page/patientList
     orderv2mini -> http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderV2mini
     proxy_getQuestionaire -> http://lis-trans-service-st.default.svc.cluster.local:3147/proxy/grpc/getQuestionaireBySampleId
     proxy_getkit -> http://lis-trans-service-st.default.svc.cluster.local:3147/proxy/grpc/getKitStatus
     proxy_getteststatus -> http://lis-trans-service-st.default.svc.cluster.local:3147/proxy/grpc/getTestStatus
     questionnaire_status -> http://lis-interactive-report-staging.report.svc.cluster.local:30901/questions-data/getBarcodeQuestionnairesStatus
     report_finish_time -> http://lis-base-report-dev.report.svc.cluster.local:30802/result/v1ReportGenerationTime
     skin_placepatientorders -> http://lis-trans-service.default.svc.cluster.local:3146/proxy/grpc/sendSkinPlacePatientOrders
     skin_questions_data_getAnswer -> http://lis-interactive-report-staging.report.svc.cluster.local:30901/questions-data/getAnswer
     transaction -> http://lis-charging-service-staging.charging.svc.cluster.local:8084/v1/charging/staging
  -- other: 15
     Azure_kafka_general_events -> general-events.servicebus.windows.net:9093
     Azure_kafka_notification_url -> vibrant-notification-events.servicebus.windows.net:9093
     GOOGLE_BASE_URL -> https://accounts.google.com/o/oauth2/v2
     GOOGLE_REDIRECT_URI -> https://staging.va-portal.pages.dev
     MYPRACTICE_AZURE_OPENAI_ENDPOINT -> https://vi-encounter-notes-resource.cognitiveservices.azure.com/openai/responses
     OUTLOOK_REDIRECT_URL -> https://staging.va-portal.pages.dev/oauth/outlook-web
     PNS_BASE_URL -> https://staging.pns-singlepage.pages.dev
     PUBLICBOOKING_GOOGLE_REDIRECT_URI -> https://staging.pns-portal.pages.dev
     VA_QUESTIONNAIRE_URL -> https://staging.report-questionnaire.pages.dev/#
     ZOOM_BASE_URL -> https://zoom.us/oauth/authorize
     appConfigEndpoint -> https://portal-config-center.azconfig.io
     azureRedisToken -> https://redis.azure.com/.default
     keyVaultUri -> https://jwt-rsa-private.vault.azure.net
     pre_test_conditions_instructions -> https://api.hubapi.com/cms/v3/hubdb
     product_sample_type -> https://api.hubapi.com/cms/v3/hubdb

=============== cloud-local namespace configmaps (URL hosts only)
  cloud-local-proxy-config: 55 keys; distinct hosts: 36
      192.168.60.10:9095
      192.168.60.6
      192.168.60.6:30266
      192.168.60.9
      192.168.60.9:9095
      http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated
      http://192.168.60.77:8081/secure/nologin/FetchScannedRequisition
      http://192.168.60.77:8081/secure/nologin/GenerateBatchReqOrReportV2
      http://192.168.60.77:8081/secure/nologin/GenerateOnlineReport
      http://192.168.60.77:8081/secure/nologin/GenerateOnlineZipDownloadV2
      http://192.168.60.77:8081/secure/nologin/OneClickPersonalizedReport
      http://192.168.60.77:8081/secure/nologin/downloadTestOrderPDF
      http://192.168.60.77:8081/secure/nologin/generateOnlineSummaryReport
      http://192.168.60.77:8081/secure/nologin/patient_results
      http://lis-core-http-service.default.svc.cluster.local:30112/api/clinic/list-customer-by-id
      http://lis-core-http-service.default.svc.cluster.local:30112/api/user/login_via_session
      http://lis-order.default.svc.cluster.local:4242/orderTest/order
      http://lis-order.default.svc.cluster.local:4242/orderTest/orderKitInfo
      http://lis-order.default.svc.cluster.local:4242/orderTest/orderTestDetails
      http://lis-order.default.svc.cluster.local:4242/orderTest/orderV2
      https://api.vibrant-america.com/v1/report-pdf-engine/pdf
      https://api.vibrant-wellness.com/v1/lis/base-report-service
      https://api.vibrant-wellness.com/v1/lis/statement
      https://api.vibrant-wellness.com/v1/oauth2/token
      https://api.vibrant-wellness.com/v1/portal/order
      https://www.vibrant-america.com/crmapi/placepatientorders
      https://www.vibrant-america.com/patient-portal-backend/ordersummary/fetch
      https://www.vibrant-america.com/patient-portal-backend/patient-verification/token
      https://www.vibrant-america.com/patient-portal-backend/patient-verification/verify
      https://www.vibrant-america.com/patient-portal-backend/receive-result/fetch
      lis-auditlog-grpc-service.default.svc.cluster.local:30113
      lis-core-grpc-service.default.svc.cluster.local:30113
      lis-dashboard-prod-rpc-service.default.svc.cluster.local:5800
      lis-issue-system-service.issue.svc.cluster.local:30071
      lis-shipping-service-grpc.shipping.svc.cluster.local:63142
      lis-test-connect-grpc-service.results.svc.cluster.local:6889
  cloud-local-proxy-config-st: 55 keys; distinct hosts: 32
      192.168.60.10:9095
      192.168.60.6
      192.168.60.6:30266
      192.168.60.6:30600
      192.168.60.6:30601
      192.168.60.6:31995
      192.168.60.9
      192.168.60.9:9095
      http://192.168.10.153:8081/secure/nologin/FetchScannedRequisition
      http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated
      http://192.168.60.77:8081/secure/nologin/GenerateBatchReqOrReportV2
      http://192.168.60.77:8081/secure/nologin/GenerateOnlineReport
      http://192.168.60.77:8081/secure/nologin/GenerateOnlineZipDownloadV2
      http://192.168.60.77:8081/secure/nologin/OneClickPersonalizedReport
      http://192.168.60.77:8081/secure/nologin/downloadTestOrderPDF
      http://192.168.60.77:8081/secure/nologin/generateOnlineSummaryReport
      http://192.168.60.77:8081/secure/nologin/patient_results
      http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/clinic/list-customer-by-id
      http://lis-core-staging-http-service.default.svc.cluster.local:30114/api/user/login_via_session
      http://lis-order-dev.lis-order.svc.cluster.local:14242/orderTest/orderV2
      https://api.vibrant-wellness.com/v1/oauth2/token
      https://api.vibrant-wellness.com/v1/portal/order
      https://www.vibrant-america.com/crmapi/placepatientorders
      https://www.vibrant-america.com/lisapi/v1/lis
      https://www.vibrant-america.com/patient-portal-backend/ordersummary/fetch
      https://www.vibrant-america.com/patient-portal-backend/patient-verification/token
      https://www.vibrant-america.com/patient-portal-backend/patient-verification/verify
      https://www.vibrant-america.com/patient-portal-backend/receive-result/fetch
      lis-auditlog-grpc-service-staging.default.svc.cluster.local:30117
      lis-core-staging-grpc-service.default.svc.cluster.local:30115
      lis-dashboard-prod-rpc-service.default.svc.cluster.local:5800
      lis-issue-system-service-staging.issue.svc.cluster.local:30072
  kube-root-ca.crt: 1 keys; distinct hosts: 0

=============== live deployments
--- default/lis-trans-deployment
   replicas: 3 | strategy: RollingUpdate {'maxSurge': '25%', 'maxUnavailable': '25%'}
   image: lis-transformer:f039348c72f349a59b1437d357959469ada400fb
   resources: {'requests': {'memory': '2Gi'}}
   liveness: True | readiness: True
   envFrom: ['lis-trans-config', 'lis-trans-secret'] | explicit env: 2
   containers: ['lis-trans']
--- default/lis-trans-deployment-st
   replicas: 1 | strategy: RollingUpdate {'maxSurge': '25%', 'maxUnavailable': '25%'}
   image: lis-transformer-staging:41a16d72bb9d816d52866da9ad572bb46542df03
   resources: {}
   liveness: True | readiness: True
   envFrom: ['lis-trans-config-st', 'lis-trans-secret'] | explicit env: 8
   containers: ['lis-trans-st']
--- transv2/lis-transv2-deployment
   replicas: 3 | strategy: RollingUpdate {'maxSurge': '25%', 'maxUnavailable': '25%'}
   image: lis-transformerv2:a8243deea06c50a917bd84b2c33ae185a94454fb
   resources: {'requests': {'memory': '1536Mi'}}
   liveness: True | readiness: True
   envFrom: ['lis-transv2-config'] | explicit env: 3
   containers: ['lis-transv2']
--- cloud-local/cloud-local-proxy-deployment
   replicas: 3 | strategy: RollingUpdate {'maxSurge': '25%', 'maxUnavailable': '25%'}
   image: cloud-local-proxy:latest
   resources: {}
   liveness: False | readiness: False
   envFrom: [] | explicit env: 57
   containers: ['cloud-local-proxy']
```
