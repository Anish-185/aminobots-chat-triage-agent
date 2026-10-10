# ADR-0007: Own trace store with OTel GenAI attribute names

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
Every decision must be traceable step by step, with timing, token use and cost per stage
(functional.md §3.1 I6, §5.7).

## Decision
Each stage writes a span to the `spans` table (SPEC §11): run and parent IDs, stage, timing,
status, prompt ID and version, input/output JSON, error, cost, and model/usage columns named
after OpenTelemetry GenAI attributes (`gen_ai.request.model`, `gen_ai.usage.input_tokens`,
`gen_ai.usage.output_tokens`). Langfuse export is optional.

## Alternatives considered
- **Langfuse as the primary store:** SPEC keeps it as an optional export only.

## Consequences
- Traces live in the same DB as runs and requests; the UI's trace view needs no external service.
- Standard attribute names keep an OTel or Langfuse export straightforward.
