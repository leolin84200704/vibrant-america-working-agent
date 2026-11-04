# LIS-7993 Jira comment draft (reply to comment 199191, post as Leo)

@Yuchen Wang EMR order counts for #2, Q1-Q3 2026 (calendar quarters by receive date, queried read-only from the EMR intake table on 2026-11-04).

| Quarter | EMR orders received | Placed in LIS | Rejected or mapping error | Success rate |
| --- | --- | --- | --- | --- |
| Q1 2026 | 773 | 744 | 29 | 96.2% |
| Q2 2026 | 952 | 936 | 16 | 98.3% |
| Q3 2026 | 721 | 710 | 11 | 98.5% |

Rejected or mapping error by cause (Q1 / Q2 / Q3):

* Ordering provider not set up for EMR ordering: 9 / 7 / 3
* Test or bundle code not mapped: 18 / 8 / 8
* System error (parse exception, service call failure): 2 / 1 / 0

Notes

* One EMR order = one HL7 order file received on our SFTP (MDHQ, THM, OptiMantra, Practice Fusion, Follow That Patient). Placed = a LIS sample was created from it. Vendor test files and duplicate rows from manual reprocessing are excluded.
* Orders placed with a failed payment are counted as placed; that is a billing follow-up, not an intake rejection.
* Manual intervention after placement (results amended, unapproved or rerun) is not in these numbers; that comes from the result data Yuteng is using.

API orders: N/A. The API order channel had no production partner traffic in Q1-Q3 2026; the only 4 requests were internal test calls.
