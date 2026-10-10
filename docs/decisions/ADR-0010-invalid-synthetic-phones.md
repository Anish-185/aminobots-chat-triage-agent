# ADR-0010: Synthetic phones in a provably invalid +91 range

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
All data is synthetic; no generated number may belong to a real person (CLAUDE.md invariant 9).

## Decision
Synthetic phones are `+91` followed by 10 digits whose first digit is 0–5, which can never be a
valid Indian mobile. Every number is asserted with `not phonenumbers.is_valid_number(n)` (INV-8,
`tests/test_datagen.py`). Identity code normalises format only and never requires validity.

## Alternatives considered
None recorded in SPEC.

## Consequences
- Numbers look realistic in transcripts yet are provably not dialable mobiles.
