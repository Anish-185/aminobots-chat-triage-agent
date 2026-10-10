# ADR-0012: Eval sliced by script and code-mix density

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
Partner chat mixes Telugu script, romanised Telugu and English. SPEC §17 motivates slicing by a
published gap in model performance on romanised text (TODO: cite the source; SPEC names none).

## Decision
Every metric is also reported per slice: script (te_script / roman_te / en / mixed), code-mix
density bucket, template, intent and sender state (SPEC §14.2).

## Alternatives considered
None recorded in SPEC.

## Consequences
- A good aggregate cannot hide failure on romanised Telugu; slice sizes must be large enough to
  read, which constrains generation.
