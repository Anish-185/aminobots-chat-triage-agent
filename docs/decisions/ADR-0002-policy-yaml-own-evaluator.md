# ADR-0002: Policy as YAML with an own evaluator, most-restrictive-wins

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
Autonomy must be decided by a short, numbered, auditable rulebook that every grade cites
(functional.md §3.4; SPEC §9).

## Decision
Rules live in `policy/policy_vN.yaml` (schema SPEC §9.3: `when` with operators `eq ne in not_in
contains_any lt lte gt gte is_null` and combinators `all any not`). `triage/policy.py` evaluates
every rule except the default R18; the grade is the minimum over matches, the cited rule is the
lowest-numbered rule with that grade, and no match yields R18 (`hand_off`). An unknown feature or
operator is a load error at startup, never a silent non-match.

## Alternatives considered
- **ZEN decision tables:** named in SPEC §17 as the migration path; not adopted in v1.

## Consequences
- Adding a rule can only lower autonomy (INV-3), checked by Hypothesis property tests for
  totality, determinism, monotonicity and the R2 safety floor (SPEC §9.5).
- Because ties go to the lowest rule number, a rule that must win its citation (e.g. R15 over
  R16) needs a lower number. Rule IDs are never reused or renumbered.
