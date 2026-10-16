---
name: vendor-email-reply
description: Checklist to run BEFORE drafting any reply to an external party on an integration thread (EMR vendor, integrator such as devcom, practice, CAM/sales asking on a customer's behalf). Use when Leo pastes or forwards a partner email, says "幫我回這封", "起草回信", "這串在講什麼", or when an integration ticket needs an outgoing message. Forces: read the whole thread from Outlook, list every unanswered ask, diff partner files against the spec WE gave them, verify every claim about our system, and give every promised action a named owner. Drafting voice rules live in ~/.claude/CLAUDE.md; this skill is about getting the content right.
---

# Vendor email reply — pre-draft checklist

Built from the 2026-10-15 BioInsights retrospective: six errors in one thread, one root cause.
**We used our own memory and code as the reference instead of what the other side actually
has: their thread, the documents we sent them, and prod.** Each step below closes one of those errors.

Do the steps in order. Write the outputs of steps 1-5 into the ticket STM before drafting.

## 1. Read the whole thread from Outlook, not the pasted message

- Search Outlook (`outlook_email_search`, query = thread subject, no date filter, page to the end)
  and read every message, including the ones Leo sent. A pasted email is one message of a thread.
- Bodies are large HTML. Strip tags and read from the newest message's quoted chain down.
- Also search by each external participant's address. Side threads (a CAM forwarding a customer
  question, a second thread with the same integrator) carry asks too.

Output: chronological list of messages (date, sender, one line each).

## 2. List every open ask, with its age

For each question or request addressed to our side: who asked, date, owner on our side, answered?
An ask that has gone unanswered for days is the first thing the reply must address, even if the
latest message does not repeat it (2026-10-15: the requisition question was 9 days old and was missed).

## 3. List what we have sent this partner

Documents, links, sample files, earlier field-by-field notes. Check `reference/partner-specs/README.md`
and the thread itself. Record in STM under "Shared with partner".

## 4. Judge partner files against the spec THEY hold

- Diff the partner's file against the spec from step 3 first (`reference/partner-specs/`).
- Then read `reference/partner-specs/gap-table.md`. If the partner follows the spec on a row where
  our code differs, the gap is ours: tell them what to do, never that their value is wrong.
- Only a deviation from the spec they hold is the partner's to fix.

## 5. Verify every factual sentence about our system

For each sentence in the planned reply that states how our system behaves or what state it is in,
cite the evidence: code path, prod query result, or config row. Examples that went wrong without this:
- "we can place an order summary PDF": the feature exists, but only vendor 44 had it enabled. Check
  the vendor row before saying "can" or "already".
- "there is no field for the draw location": true for HL7, but incomplete (DBS test codes are the
  at-home versions).

No evidence means the sentence is either removed or turned into a question for Leo. It is never sent as is.

## 6. Every promised action has an owner and a verified precondition

- Before "we will register X / enable Y / send Z", check that the precondition holds (provider exists
  in `ehr_integrations`, Vibrant account exists, folder exists) and who owns the action.
- New provider on a connection = onboarding, owned by Mingxi / Keith (account, clinic/practice,
  integration type, kit delivery, billing). We do not promise registration; we @ the owner.
- Catalog / compendium / CPT / reference ranges = Zhenhe. Only @ the owner; do not restate or promise for them.
- Never use a real customer's NPI as a vendor test identity (INCIDENT-20261013 R3).

## 7. Draft

- Voice and length: `~/.claude/CLAUDE.md` section on drafting external text for Leo.
- No placeholders in the body ([TBD], TODO, [...]). Open decisions go in the "for Leo" part of the
  report. Enforced by `validate-outbound-placeholders.sh`.
- Outlook: create a reply-all draft on the latest message of the thread; never send.
  Check the recipient list after creating it: owners @-mentioned in the body belong in To.
- Report to Leo: draft link, the open-asks list from step 2, and every claim from step 5 that
  could not be verified.
