# ADR-0004: Structured outputs via Instructor, with semantic-validation retry

- **Status:** Accepted (amended 2026-10-10 by phase 1b: provider-agnostic via OpenRouter)
- **Date:** 2026-10-10

## Context
The extractor's output (SPEC §4.1) must parse into a Pydantic schema and pass semantic checks:
evidence IDs exist and are not system messages, `primary_msg_id` ∈ `evidence_ids`, references
precede the primary message, intents and flags are in their enums, and no digit run ≥ 9.

## Decision
Extraction goes through Instructor with OpenRouter (`instructor.from_provider("openrouter/<id>")`,
key from `OPENROUTER_API_KEY`). Use `Mode.JSON_SCHEMA` for models whose OpenRouter metadata lists
`structured_outputs`; otherwise fall back to `Mode.JSON` (`response_format`) or `Mode.MD_JSON`,
with the same Pydantic validation. A validation failure gets at most one repair retry with the
error fed back (`llm_max_repair_retries: 1`).

## Alternatives considered
- **Anthropic native structured outputs** (the original v1 choice): replaced by the zero-cost
  OpenRouter-only rule (ADR-0014).

## Consequences
- The same contract holds whatever free model answers; weaker modes rely on validation, not
  constrained decoding, so invalid output is more likely and is handled fail-closed (SPEC §10.3).
- The mode is per model and must be chosen with the model in the phase-4 bake-off.
