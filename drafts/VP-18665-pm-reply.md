# VP-18665 — draft Jira comment (English, Leo's voice; NOT posted). Supersedes the docs-only draft.

@Xiaoye Li Confirmed and fixed.

What Sandbox returned on 29 September was provider-account scope: only the orders placed by the authorized provider's own account, which is how VP-18030 launched. The docs promised the whole clinic, so the two disagreed.

Reproduced with the case you described. Clinic 125613, patient 557149: provider 3194 placed 3 orders in the clinic (plus one with no clinic), provider 35935 placed 2 in the same clinic. The 3194 token returned 4 orders; the Portal clinic view shows 6.

Change (deploying with the VP-18664 fix): the list now covers every order placed in the token's clinic by any provider, plus the account's own orders in other clinics. For patient 557149 the same token returns 6. Orders a peer placed through the API show null orderId and placerId under your token, since those identifiers belong to the other partner; use accessionId.

No docs change needed for the clinic statement. One line to add on the list-orders page under patientId: "Returns 404 PATIENT_NOT_FOUND when the patient is unknown or not linked to your clinic; 200 with an empty orders array when the patient is known but has no orders in scope."

Re-test in Sandbox after the staging deploy; I will comment here when it is live.
