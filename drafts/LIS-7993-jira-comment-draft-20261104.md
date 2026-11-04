# LIS-7993 Jira comment draft (reply to comment 199191, post as Leo)

@Yuchen Wang EMR order counts for #2, Q1-Q3 2026 (calendar quarters by receive date, UTC; queried read-only from the EMR intake table on 2026-11-04).

| Quarter | EMR orders received | Placed in LIS | Rejected or mapping error (never placed) | Success rate |
| --- | --- | --- | --- | --- |
| Q1 2026 | 773 | 744 | 29 | 96.2% |
| Q2 2026 | 952 | 936 | 16 | 98.3% |
| Q3 2026 | 721 | 710 | 11 | 98.5% |

Never-placed orders by cause (Q1 / Q2 / Q3):

* Ordering provider not set up for EMR ordering (customer_not_found): 9 / 7 / 3
* Test or bundle code not mapped (emr_code_not_found): 18 / 8 / 8
* System error (parse exception, gRPC failure): 2 / 1 / 0

Orders placed only after a failure was fixed (manual intervention at intake):

* Q1: not measurable. The intake service running in Q1 did not keep failure history on orders that later succeeded, so 96.2% is an upper bound.
* Q2: 17 (16 after a bundle mapping was added and the file reprocessed, 1 after an automatic retry). Excluding them: 96.5%.
* Q3: 22 (14 after a manual fix: 2 provider set-ups, 8 replays after a gRPC outage on 9/7-9/8, 4 manual re-uploads of stranded files; 8 after an automatic retry). Excluding them: 95.4%. Failure history is complete from 7/29 only.

Definitions

* One EMR order = one HL7 order file received on our SFTP (MDHQ, THM, OptiMantra, Practice Fusion, Follow That Patient). Placed = a LIS sample was created from it.
* Excluded: 66 duplicate rows from a manual reprocessing run on 1/14 (7 orders), 4 vendor test files (Nichols test order, BioInsights devcom tests), and 4 rows superseded by a manual re-upload of the same file (counted once, under the re-upload).
* A rejected order that the practice re-sent is counted twice (once rejected, once placed on the re-send).
* Orders placed with a failed payment ("no payment method": 87 / 158 / 2) are counted as placed. That is a billing follow-up, not an intake rejection.
* Manual intervention after placement (results amended, unapproved or rerun) is not in these numbers. That part comes from the result data Yuteng is using.

API orders: N/A. The API order channel had no production partner traffic in Q1-Q3 2026; the only 4 requests were internal test calls.

A per-order list of the never-placed and recovered orders is available if QA wants it.
