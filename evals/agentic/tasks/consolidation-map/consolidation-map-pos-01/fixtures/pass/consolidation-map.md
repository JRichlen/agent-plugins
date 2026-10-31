Consolidation map: notification services
Before 8 | After 4 | Net -4   (kept 3, merged-away 4, retired 1, new 1)

## Unit: mail-relay, sms-relay and push-relay were built into a new notify-gateway
- new         notify-gateway
- merge-into  mail-relay -> notify-gateway
- merge-into  sms-relay -> notify-gateway
- merge-into  push-relay -> notify-gateway
Why: three relays shared one delivery path, so one gateway replaces them.
What's lost: per-channel retry settings; the gateway applies a single shared retry policy.

## Unit: event-trail was absorbed by audit-log
- absorb      audit-log
- merge-into  event-trail -> audit-log
Why: event-trail duplicated audit-log's write path.
What's lost: the 30-day replay endpoint, which audit-log does not offer.

## Unit: legacy-pager is retired
- retire  legacy-pager
Why: nothing has called it in 90 days and no replacement is planned.
What's lost: pager escalation for the old on-call rota.
Evidence: no inbound calls in 90 days.

## Unit: ops-console is deprecated
- deprecate  ops-console
Why: scheduled for removal once notify-gateway has its own admin view.
What's lost: nothing yet; removal will drop the manual resend button.

## Unchanged
- keep  status-page

## Reconciliation
N = K + X + R : 8 = 3 + 4 + 1   OK
M = K + W     : 4 = 3 + 1       OK
Every inventory entity appears once: OK
Every merge-into target survives:    OK
