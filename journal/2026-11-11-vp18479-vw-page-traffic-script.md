---
id: 2026-11-11-vp18479-vw-page-traffic-script
type: journal
date: 2026-11-11
tickets: [VP-18479, VP-19198, VP-18465]
tags: [vw-page, web-homepage-api, on-prem, traffic, trans-opt]
distilled: false
---
# VP-18479: the traffic count for vw-page has to be run by Leo on the on-prem host

Yekai settled the decision: vw-page stays out of trans. He rewrote the ticket around a traffic count, which
decides whether the CMS moves to AKS or is retired under VP-19198. The approved step was a read-only pull of the
vw-page pod logs. This machine cannot do it. kubectl here only knows AKS, and 192.168.60.5 takes password login
only, so the run belongs to Leo.

Reading the service before writing the counter changed what the counter may do. The logging middleware writes
the request body of every form post, so the pod logs hold names and emails from the sign-up and contact forms.
The script therefore counts on the host and prints numbers only; the raw logs are never saved or copied.

The fake-kubectl test caught one real bug: the status code sat at split index 4, not 5. Group totals summing to
the access-line count is the check to repeat on the real output.

Also found: another session left web-homepage-api's main checkout on feature/leo/VP-18479 with PR #69, a
Jenkinsfile credential change that the new ticket text marks out of scope. Left alone and reported.
