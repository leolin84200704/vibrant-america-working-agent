# Partner-facing specs

Documents we hand to EMR vendors / integrators. A partner builds against THESE, not
against our code, so any review of a partner's file starts by diffing it against the
spec they hold. Where the spec and our code disagree, the gap is ours to fix, never
the partner's mistake (2026-10-15, BioInsights/devcom: we told them five values from
this spec were "invalid").

| Document | Source of truth | Copy here | Sent to |
|---|---|---|---|
| UpdatedExampleOrder_Explained.pdf | SharePoint `kristine_l` OneDrive: `EMR/Technical Documentation/UpdatedExampleOrder_Explained.pdf` (2025-10-15) | `UpdatedExampleOrder_Explained.md` (verbatim) | BioInsights/devcom, 2026-09-04 (Leo, share link to 5 addresses) |
| HL7_Technical_Reference.docx | **not located** (not found by SharePoint search 2026-10-15) | none | BioInsights/devcom, 2026-09-04 |
| Integration_Setup_Guide.docx | SharePoint `kristine_l` OneDrive: `EMR/Technical Documentation/Integration_Setup_Guide.docx` (2026-04-03) | none | unknown |

Spec vs code: `gap-table.md`. Update it whenever the parser changes a field it reads.

When onboarding a partner, record in its STM a "Shared with partner" line: which
documents, which version/date, sent by whom, to whom.
