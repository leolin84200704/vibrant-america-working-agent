# Reply to Olena (devcom) — ORC-12 / OBR-16 component 9 question, 2026-09-25

Question asked: "Component 1 = NPI Number or Customer ID; Component 9 = N. Will component 9
change if component 1 is Customer ID?"

Verified against lis-backend-emr-v2 origin/main (2026-09-25):
- parser.service.ts L201-216: ORC-12 XCN.1 only; `length <= 7` -> fetchById(customer id),
  otherwise fetchByNpi. Nothing else in the field influences the branch.
- parser.service.ts L202-203: XCN.2 / XCN.3 are read for the error label only.
- obr-parser.service.ts L131: OBR-16 XCN.8 -> `obrSourceTable`, which has zero downstream
  consumers (grep on origin/main). XCN.9 is not read anywhere in the repo.

---

Hi Olena,

No - component 9 does not change, and you do not need to set it differently for a Customer ID.

We never read component 9 of ORC-12 / OBR-16. The only component we use to identify the
ordering provider is component 1, and we decide how to interpret it purely by its length:

  - 8 characters or more -> treated as an NPI (an NPI is always 10 digits)
  - 7 characters or fewer -> treated as a Vibrant Customer ID

So component 9 can stay exactly as it is in either case. This is also why the placeholder
1234567 in your first file was not looked up as an NPI at all - at 7 characters we took it as
a Customer ID and found no provider under that id.

For this integration please keep sending the NPI, 1730269200. It is the value registered on
the JAG Holdings Group integration and it already resolved correctly in V00000416.hl7, so
there is nothing to gain by switching. If you ever do send a Customer ID instead, it must be
the Vibrant customer id of the ordering provider and it must be 7 characters or fewer.

Two related points from my previous email still stand, since they concern the same field:

  - Components 2 and 3 are family name and given name. With the extra empty component you are
    currently sending, we read the family name as empty and the given name as "Balandan".
    Please send 1730269200^Balandan^Paola^^^^^^N - that keeps the trailing N in component 9
    and puts the names where we read them.
  - The names only affect what we display and log; they never affect which provider the order
    is routed to. Component 1 alone decides that.

Best regards,
Leo
