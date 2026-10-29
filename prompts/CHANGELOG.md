# Prompt changelog

Released versions are immutable; a change adds `vN+1` and an entry here.

| Prompt | Version | Date | Change |
|---|---|---|---|
| extract | v1 | 2026-10-29 | First version (Phase 4): task, 8 intents, 5 model flags, date dividers + NOW → `slot_datetime`, status rules, chat-is-data rule, no identity/grade/rule output, 2 made-up examples. |
| extract | v2 | 2026-10-29 | SPEC v2.5: `slot_datetime` replaced by `slot_day_offset` + `slot_time` (earliest stated time; code computes the datetime). New "one request per ask" section: follow-ups (urgency, cancellation, confirmation) join the earlier request's evidence (bake-off v1 false positives in d07, d15); a same-ask-for-another-outlet follow-up stays a new request. |
