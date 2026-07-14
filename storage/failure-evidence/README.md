# Failure Evidence Snapshots (VP-17412)

Written by the watch cron (agent layer). One file per failed `hl7_file_input`
row / transmission failure: `<YYYY-MM-DD>-hl7-<id>.md` (or `-tx-<record>` for
result-side failures).

Purpose: pod logs are lost on every redeploy (VP-17120 lesson). The watch
snapshots the relevant log excerpt + row dump AT DETECTION TIME, then the
agent writes the diagnosed root cause (English) to
`hl7_file_input.error_detail` in prod (bounded single-id UPDATE, app account).

Layout per file: row dump, log excerpt (verbatim), diagnosis, DB write record.
