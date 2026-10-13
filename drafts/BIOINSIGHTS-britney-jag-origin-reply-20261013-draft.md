# Reply to Britney (Vibrant Wellness CAM) -- where the JAG mapping came from, 2026-10-13

Outlook reply-all draft created 2026-10-13 on Britney's 18:09 UTC email (To: Leo, Keith, Kristina Banister). Not sent.

## Source of the JAG mapping (verified in Outlook 2026-10-13)

NOT BioInsights. Britney herself, in a DIFFERENT thread:

- Thread: "[Vibrant Wellness] Re: Integration" (Zendesk ticket 00WRYM-60YK0), about Canvas Medical wanting HTTP(S).
  - 07-23 Terry (support): yes, HTTP(S) supported.
  - 07-24 Britney: "Canvas would like to go ahead and use HTTP(S)." Terry CC's Leo.
  - **07-27 13:16 UTC Britney -> support, CC Keith, Leo, Payton Smith (payton.smith@canvasmedical.com)**:
    "Integration Details: Office Name: JAG Holdings Group, LLC / Provider ID: 30248 / Practice ID: 132493.
    Payton, please use this email thread if you have any questions."
    Outlook id: AAMkADU3N2M0NzRlLTg1YTItNDBjZi04MDU3LWI1YTNmNzhmYTZhZgBGAAAAAADQKnZ7JVJySJKtga25dQz1BwAmAQQbf377SYf7bnr2PTZ-AAAAAAEMAAAmAQQbf377SYf7bnr2PTZ-AAFTAaZnAAA=
  - 07-27 17:55 UTC Leo reply: "the integration for JAG Holdings Group, LLC (Provider ID 30248 / Practice ID 132493)
    has been configured and verified end-to-end -- SFTP connectivity, order file pickup from outgoing/, and result
    delivery into incoming/" -- i.e. the BioInsights SFTP setup, attached to the Canvas request.
  - 07-29 Terry (support): "The technical setup for the Canvas integration has been completed... existing P2P
    integration... disconnect and replace with Canvas, or keep both?" No answer from Britney found.
- The BioInsights thread ("Integration with Vibrant Wellness", from Kristine Legaspi 2026-05-19 onward) never names
  JAG, Canvas or Payton. Canvas Medical never wrote to us (0 emails from canvasmedical.com).
- First mention of JAG inside the BioInsights thread is OUR side: Keith 09-15, Leo 09-18 ("ORC-12 must carry NPI
  1730269200 (JAG Holdings Group, provider 30248, practice 132493)"). Britney's "you all mentioned them first" is correct.

## What happened after (already in STM)
devcom test file V00000417.hl7 (09-25) -> accession 2609256344, John Doe, Vitamin D + Gut Zoomer, $570 customerPay,
clinic 132493. Mingxi 10-01 asked BioInsights to confirm the order; Britney re-sent that 10-12 and 10-13; Kristina
escalated 10-07. Nobody has answered Britney's 10-07 "Why was Jag mapping information provided?" until this draft.

## Open for Leo
- (a) bracketed sentence: void order 2609256344 + charge -- needs someone with lis_re access.
- (b) "Removing JAG from the BioInsights connection" = set ordering_enabled=0 (and result_enabled=0) on
  ehr_integrations cms3icsz700010xlgywfuj8do, or delete the row. Prod change -> lis-prod-change-gate. Not done yet;
  the draft states it as in progress, so do it before sending or reword.
- (c) whether to answer BioInsights on their thread too (devcom is still testing against JAG's NPI).

---

Hi Britney,

You are right. JAG was never named by BioInsights. The mix-up is on our side.

Here is the trail:

- 27 July, thread "[Vibrant Wellness] Re: Integration" (the Canvas Medical / HTTP(S) request, Payton Smith from
  Canvas on CC): you sent the integration details for JAG Holdings Group, LLC, Provider ID 30248, Practice ID 132493.
- That same week we were setting up the BioInsights SFTP connection. The two requests were handled as one, and JAG's
  office was registered on the BioInsights connection instead of a Canvas one. My reply to you on 27 July already
  described it as an SFTP setup, which should have been the flag.
- Because JAG was the only office on that connection, we told BioInsights' developer (devcom) in September to use
  NPI 1730269200 on their test files. Their test order on 25 September ("John Doe", Vitamin D and Gut Zoomer)
  therefore landed in JAG's account, billed to the practice. No kit was shipped.

What we are doing:

- Removing JAG from the BioInsights connection, so nothing else from BioInsights can reach their account.
- [Voiding the 25 September test order and the charge.]

Two things I need from you:

- Does JAG still want the Canvas Medical integration? That was the original request and it was never built.
- BioInsights needs to tell us which office and provider their orders should go under. If you prefer, I can ask them
  directly on the BioInsights thread.

Best regards,
Leo
