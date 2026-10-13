# VP-18824 — Jira comment draft (English, not posted)

Root cause

The loose PDF files were the per-report PDF delivery shipped under VP-18194 (PH-907). Maristany Medical (Provider 28524 / Practice 127660) was the only practice with that option enabled, as the canary requested on that ticket. From 25 September every result pushed to /eduardomaristanymdemr/results/ came with one {accession}_{REPORT}.pdf per report next to the usual {accession}.hl7. The HL7 itself was unchanged and still carried the embedded combined PDF.

Cerbo's import stops at the first file in the folder that is not .hl7. Their archive shows it: before 25 September every HL7 was imported within hours; of the 14 results pushed since, 12 (including 2609166115, 2609246225 and 2609096410) sat unimported until Cerbo support cleared the folder by hand on 13 October around 16:14 ET. All 12 are now in Cerbo's archive with that import time, so no repush is needed. The clinic uploaded three of them manually before that, so those three may now exist twice in Cerbo.

What was changed

1. The per-report PDF option was switched off for Maristany Medical on 13 October (production, immediate). The next result goes out as one HL7 file with the combined PDF embedded, exactly as before 25 September.
2. A vendor-level guard is going out in code: Cerbo (MDHQ) is marked as an HL7-only partner, and no companion file of any kind (per-report PDF, order summary PDF) can be written to a Cerbo result folder again, regardless of how a practice is configured. The combined PDF always stays embedded for such a partner. Default is unchanged for every other partner. PR: {PR_URL}

Verification

After the code is live we will confirm the next Maristany result lands in Cerbo's archive with an import timestamp and nothing but .hl7 beside it.

Open question for the integration side

The per-report delivery PH-907 asked for cannot be done with separate files for Cerbo. The only shape left is several PDFs inside the one HL7 message, one per report. Before anyone builds that we need Cerbo to confirm, in writing:

- whether their parser accepts more than one embedded PDF (ED-type OBX) in a single ORU message;
- where each one has to sit for it to be filed against the right test (under that test's OBR, or on its own OBR with a specific identifier);
- any size limit per message when several PDFs are embedded.

Could the integration side put that question to Cerbo (Anne, Cerbo ticket 572378)? Until it is answered, Maristany receives the combined PDF inside the HL7 as before.
