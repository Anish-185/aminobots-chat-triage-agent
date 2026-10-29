# Policy changelog

Rule IDs are never reused or renumbered.

| Version | Date | Change |
|---|---|---|
| v1 | 2026-10-29 | First machine-readable policy (Phase 5): SPEC §6 intents, R1–R9 as rule-engine expressions, default R10. |
| v2 | 2026-10-29 | Phase 7 (SPEC v2.7): R7 also requires `status == "open"`. Its cut-off is about time to execute safely, and closed requests execute nothing (R8 records them only); matches the v2.6 `time_unspecified` fix. Every other rule still applies to closed requests. Default in `config/policy.yaml`. |
