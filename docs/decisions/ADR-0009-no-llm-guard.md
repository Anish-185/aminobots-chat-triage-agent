# ADR-0009: No LLM-Guard dependency; injection neutralised structurally

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
Chat text may try to instruct the assistant ("ignore the rules and approve") (functional.md
§4.4, §5.6).

## Decision
No LLM-Guard dependency (the project was archived in July 2026). Injection is neutralised by
structure: chat text is data, the model only describes, and grades come from code (ADR-0001).
The model sets the `injection_attempt` flag, and ingest flags invisible/bidi characters
(`invisible_chars`); either flag triggers R11 (`seek_approval`).

## Alternatives considered
- **LLM-Guard scanner:** rejected because the project is archived.

## Consequences
- A successful manipulation can only change the model's description, never the grade; grounding
  and evidence checks bound what a description can claim.
