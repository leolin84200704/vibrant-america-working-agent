# VP-18666 — draft Jira comment (English, Leo's voice; NOT posted)

@Xiaoye Li The list status was right; the report endpoint in Sandbox was reading the wrong environment.

Sandbox's report lookups were pointed at the dev report service, which has no report rows for these samples, so every finished report came back as "No Finished Test". The order list reads the order record, which correctly said the report was ready. The Sandbox config now points at the staging report service.

Re-tested 2 October: GET /v1/report/fhir/2512106925 returns status final with the Vibrant America report marked Final, and GET /v1/orders?patientId=3161747 still shows report_available, so the two agree.

What is still missing for a full end-to-end backfill test in Sandbox: the FHIR body for these historical QA samples has no result observations and no PDF, because the staging lab-result store has no test results for them and the staging order service rejects the panel lookup. Those are Sandbox data gaps, not API logic. If you need a Sandbox accession with real results, we need one that was actually processed through the staging lab pipeline; tell me which accession you plan to use and I will check it before you test.
