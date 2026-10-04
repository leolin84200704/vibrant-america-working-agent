# VP-18666 — ask to the order team (Fangyuan), English, Leo's voice; NOT sent

Subject: staging orderTest/getOrderPackageAndTest returns 500 for every sample

The staging order API answers 500 for `GET /v1/portal/order/staging/orderTest/getOrderPackageAndTest?sample_id=…` on every sample we tried (2454750, 2552840), with the generic Spring body `{"status":500,"error":"Internal Server Error","path":"/orderTest/getOrderPackageAndTest"}`. The same call on production for 2454750 returns 200 `{"single_test_id_list":[14],"package_id_list":[]}`.

emr-v2 staging uses this call to group result markers into OBR panels before it builds the HL7 / FHIR result, so on Sandbox every historical report comes back without results. Could you check what is failing on the staging instance? Repro: the request above with the staging order-API token, any sample_id, observed 4 October 02:32 UTC.
