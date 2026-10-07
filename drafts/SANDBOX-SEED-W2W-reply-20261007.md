# Draft reply to the integrator (via Chris) — 2026-10-07

Sandbox orders never pass through our shipping service, so `kit` is null on every sandbox order. Only `status` is populated there. That will not change unless a staging shipping feed is set up; we will tell you if it is.

M02: `kit.status` has three values in production: `not_shipped`, `shipped`, `delivered`. There is no `in_transit`. Use M01 for the shipped case and drop M02.

M09/M10: a carrier delivery exception is not a separate value in the payload. Production returns `status` `kit_shipped` (outbound) or `sample_in_transit` (return), `kit.status` `shipped` and the tracking number; the exception itself is only visible on the carrier's tracking page.

M06: will be re-seeded to `analyzing` on the sandbox report side; we will confirm when it is done.

M07: the PDF link is the report service's own download endpoint and takes a Vibrant portal token, not an API key, in sandbox and in production. We are reviewing how partners should fetch the PDF and will come back to you. The order already has a full result set behind it.
