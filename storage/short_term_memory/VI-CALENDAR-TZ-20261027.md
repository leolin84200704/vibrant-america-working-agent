---
id: VI-CALENDAR-TZ-20261027
type: stm
category: technical
status: in_progress
base_weight: 0.9
created: 2026-10-27
updated: '2026-10-27'
links:
- VP-19009
tags:
- vi-calendar
- timezone
- dst
- anguilla
- practice-150105
- trans-v2
- availability
summary: 'VI Calendar DST report (Suzette Garcia 46594, clinic 150105): timezone setting
  was America/Anguilla (fixed UTC-4, June offset-dedupe artifact); she switched to
  America/New_York 2026-10-26 23:54Z. 13 provider-booked consults after 11/01 sit
  at Anguilla-derived instants = 1h earlier than her intended Eastern slots. Mary
  Beth Augustine 46604 still Anguilla.'
jira_status: none
score: 0.1158
---

# VI-CALENDAR-TZ-20261027 - Triage record (no ticket yet)

## Report (2026-10-27, forwarded by Leo)
Clinician: recurring meeting now works after adding end date + appointment type. New issue: after changing settings to Eastern,
provider-booked consults after 11/01 show one hour earlier; "back to Anguilla" defaulted to Central; pre-11/01 correct.

## Facts (ground truth, 2026-10-27 ~17:00Z)
- Reporter = Suzette Garcia (customer 46594, calendar 30787, clinic 150105). Audit log (lis_frontend_service setting,
  event customer_timezone, user 1123): 23:45:49Z Anguilla -> New_York; 23:49:14Z New_York -> Chicago; 23:54:15Z Chicago -> New_York.
  `setting.setting_value_updated_time` is NOT bumped by editCustomerClinicSettings (row still says 2026-06-24) - use audit log, not that column.
- Mary Beth Augustine (46604, calendar 30788) timezone setting still America/Anguilla; no audit entries. Only Anguilla row org-wide.
  Legacy v2_calendar.timezone = Anguilla for both (unused since VP-17190).
- Origin of Anguilla: 2026-06-24 21:50Z batch of 8 setting rows (VP-17190 migration from v2_calendar.timezone); pre-June dropdown
  deduped zones by current UTC offset (Anguilla = first -240 zone in summer; Jason Barker got America/Boise the same way).
- Mechanism: provider-availability.service calculateAvailableSlots expands v2_schedule wall-clock in the clinician's setting tz.
  Suzette Mon 12:00/13:30/15:00/16:00 in Anguilla = 16:00/17:30/19:00/20:00Z = exactly her 11/02 bookings (14730/14817/14813/14818).
  After 11/01 Eastern = UTC-5, so those instants display 11:00/12:30/14:00/15:00 Eastern. Pre-11/01 EDT = UTC-4 = Anguilla, no drift.
- Provider side (va-portal ScheduleAMeetingDialog) shows slots in the provider's browser local time, so providers were told the
  11:00-style times; bookings are internally consistent, just one hour off Suzette's intent.
- Affected Suzette "Provider Consult 30 Minutes" events on/after 11/02 created before the tz switch (13):
  11/02 14730 14817 14813 14818; 11/03 14800 14839 14668; 11/04 14819; 11/05 14786 14820; 11/06 14912; 11/11 14120 14624.
  Recurring 14929 "NEW Grand Rounds" created 23:42Z with timezone=America/Anguilla (before switch) - will also drift after 11/01.
  Mary: no v2_schedule rows, so no provider bookings; only her own OOO/VCT events after 11/01 (self-created in Anguilla display).
- Suzette's block 14930 (daily 13:00-23:00Z from 10/28, rrule, tz New_York) hides all slots until removed.
- Datadog request logs for /setting/* are sampled (1 GET in 7d), Sentry clean - not useful here; audit log is the evidence source.
- "Back to Anguilla defaulted to Central": frontend POSTed America/Chicago at 23:49Z (audit). SetupTimezoneCard injects the stored
  zone as an extra option only at mount; cause of the Chicago value not pinned down (SingleSelector resolution). Low priority.

## Options for Leo (not executed)
1. Keep bookings as-is (providers already confirmed the 11:00-style times); Suzette removes block; new bookings now Eastern-correct.
2. Shift the 13 events +1h: via UI reschedule (VP-19003 sends reschedule email on time change, which providers need) or data fix
   on calendar_prod (prod UPDATE -> Leo decision, lis-prod-change-gate; external sync ids google/outlook/zoom would need re-sync).
3. Mary must switch to Eastern before 11/01; her own post-11/01 events need a glance.

### [2026-10-27 18:10] "Back to Anguilla -> Central" reproduced: not a frontend value bug
- Audit user 1123 = Suzette's own internal_user_id (sgarcia); auto_update_timezone=0 for 46594/46604, so no login auto-sync. She did all three saves herself.
- Repro (scratchpad tz-repro, vitest + jsdom, real SetupTimezoneCard.vue + NewLibrary/SingleSelector.vue, vue 3.5.20 / element-plus 2.11.1 / moment-timezone 0.5.48 = ehr-frontend lock):
  A. same mount, stored Anguilla: pick Eastern -> POST New_York; pick the injected "America/Anguilla (UTC-4)" -> POST America/Anguilla. Values match the clicks.
  B. after the Eastern save and a remount (GET now returns New_York): the injected Anguilla option is gone; list is the curated one
     ("Central Time (US & Canada) (UTC-5)", "Eastern Time (US & Canada) (UTC-4)", ...). Nothing labeled Anguilla exists to click.
- Conclusion: the Chicago POST at 23:49Z was a click on "Central Time" in scenario B (old_timezone=New_York in the audit confirms the card
  was already on Eastern). Likely she tried to "undo" by picking the zone one step from Eastern. Design limitation only: a stored
  non-curated zone cannot be re-selected once changed away from. No code change recommended; Anguilla must not be selectable anyway.
