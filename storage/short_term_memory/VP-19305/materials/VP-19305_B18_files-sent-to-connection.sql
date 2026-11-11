-- Files sent to one EMR connection over a date range (VP-19305 B18).
-- Database: lis_emr on lisportalprod2 (read-only replica is fine).
-- The JAG list (INCIDENT-20261013) is this query with ehr_vendor_id = 46 (BioInsights),
-- 2026-07-29 to 2026-10-13: 204 TRANSMITTED rows for 200 samples (4 resends reused the same file name).
-- generated_hl7_content keeps the HL7 text but the PDF OBX is replaced by
-- [PDF_CONTENT_REMOVED_FOR_DB_STORAGE]. The full sent file is on the emr-v2 prod pod at file_path.
SET @vendor_id = 46;                 -- lis_emr.ehr_vendors.id
SET @from = '2026-07-29 00:00:00';   -- UTC
SET @to   = '2026-10-14 00:00:00';   -- UTC, exclusive

SELECT r.id,
       r.sample_id,
       r.file_name,
       r.sftp_host,
       r.sftp_remote_path,
       r.file_path            AS copy_on_emr_v2_pod,
       r.transmission_status,
       r.transmission_completed_at,
       r.integration_request_id,
       i.clinic_id,
       i.clinic_name,
       i.customer_id
FROM lis_emr.result_transmission_records r
LEFT JOIN lis_emr.ehr_integrations i ON i.id = r.integration_request_id
WHERE r.ehr_vendor_id = @vendor_id
  AND r.transmission_status = 'TRANSMITTED'
  AND r.transmission_completed_at >= @from
  AND r.transmission_completed_at <  @to
ORDER BY r.transmission_completed_at;

-- To narrow to one folder instead of a whole vendor, add:
--   AND r.sftp_remote_path LIKE '/incoming/%'
