-- VP-18243 containment: stop result delivery for the Geyer 8246 integration that
-- carries Holistic Urgent Care's CHARM receiving facility (P00029HUC092017).
-- GATED: do not run without Leo's approval. Read-only evidence was gathered 2026-09-11.
--
-- Why status and not result_enabled: both delivery paths in lis-backend-emr-v2 filter
-- on status = 'LIVE' (kafka-report-finished-listener.service.ts:444-449 and
-- result-generation.service.ts:781-790). The manual/gRPC path additionally accepts
-- integration_type IN ('RESULT_ONLY','FULL_INTEGRATION') as an alternative to
-- result_enabled, so flipping result_enabled alone would NOT block a manual repush.
-- Configuration is preserved (row is not deleted; all delivery fields stay as-is).

START TRANSACTION;

-- 1. Pre-image (must return exactly 1 row, status LIVE)
SELECT id, customer_id, clinic_id, status, result_enabled, msh06_receiving_facility, updated_at, last_modified_by
  FROM ehr_integrations
 WHERE id = 'cmw3xyrkgmbn7urjkfj8myp27' AND customer_id = '8246' AND clinic_id = 11783 AND status = 'LIVE';

-- 2. Contain (expected: 1 row matched, 1 changed)
UPDATE ehr_integrations
   SET status = 'REJECTED',
       updated_at = NOW(),
       last_modified_by = 'VP-18243'
 WHERE id = 'cmw3xyrkgmbn7urjkfj8myp27' AND customer_id = '8246' AND clinic_id = 11783 AND status = 'LIVE';

-- 3. Audit trail (mirrors the LBS-1785 recipe)
INSERT INTO ehr_integration_status_history (integration_id, from_status, to_status, reason, additional_details, created_at, changed_by)
VALUES ('cmw3xyrkgmbn7urjkfj8myp27', 'LIVE', 'REJECTED',
        'VP-18243 containment: msh06 P00029HUC092017 is the CHARM receiving facility of practice 5144 Holistic Urgent Care, not of practice 11783; provider 8246 is not a member of clinic 5144 in core',
        'Row created 2026-09-05 01:02:17Z under VP-18055 as a copy of cmjklx3y400c30xfe9pljzmo9 (customer 6171, emr_result_customers.id=423, legacy PracticesEnum CHARM6171 dated 2017-10-12). 86 samples / 64 patients transmitted and acknowledged via this row 2026-09-05..09-10. Config preserved for evidence; do not delete.',
        NOW(), 'VP-18243');

INSERT INTO ehr_integration_notes (integration_id, content, is_internal, note_type, created_at, updated_at, created_by)
VALUES ('cmw3xyrkgmbn7urjkfj8myp27',
        'VP-18243: set LIVE -> REJECTED to stop report delivery to CHARM facility P00029HUC092017 (Holistic Urgent Care, practice 5144). Practice 11783 authorized CHARM destination still to be confirmed with the practice and CHARM before any re-enable or replay.',
        1, 'ISSUE', NOW(), NOW(), 'VP-18243');

-- 4. In-transaction verify (expect: status REJECTED, 1 row; and zero LIVE result rows left for customer 8246)
SELECT id, status, result_enabled, updated_at, last_modified_by FROM ehr_integrations WHERE id = 'cmw3xyrkgmbn7urjkfj8myp27';
SELECT COUNT(*) AS live_result_rows_for_8246 FROM ehr_integrations WHERE customer_id = '8246' AND status = 'LIVE';
SELECT id, from_status, to_status, changed_by, created_at FROM ehr_integration_status_history WHERE integration_id = 'cmw3xyrkgmbn7urjkfj8myp27';

COMMIT;

-- 5. Post-commit reverse audit (broader criterion): any LIVE result-capable row that would still
--    route customer 8246 or clinic 11783 to P00029HUC092017?
SELECT id, customer_id, clinic_id, status, result_enabled, integration_type, msh06_receiving_facility
  FROM ehr_integrations
 WHERE (customer_id IN ('8246','-1') AND clinic_id = 11783) OR customer_id = '8246';
-- Expected: only cmw3xyrkgmbn7urjkfj8myp27 (REJECTED). The 6171 row is LIVE but customer 6171 is a
-- closed account with no new samples, so it cannot be selected for 8246's reports (exact customer_id match).

-- 6. Consumer-layer readback (Gate 7): from the on-prem prod emr-v2 pod with its own DATABASE_URL,
--    run the same WHERE the listener uses for customer 8246 / clinic 11783 and confirm 0 rows.

-- OPTIONAL (separate approval, ticket item 5): the source row on closed account 6171 carries the same
-- facility and is LIVE + ordering_enabled=1 with NPI 1477734937. Same recipe, bounded:
-- UPDATE ehr_integrations SET status='REJECTED', updated_at=NOW(), last_modified_by='VP-18243'
--  WHERE id='cmjklx3y400c30xfe9pljzmo9' AND customer_id='6171' AND clinic_id=11783 AND status='LIVE';
