# ADR-0005: Gold labels by construction from planner scripts

- **Status:** Accepted (renderer amended 2026-10-10 by ADR-0014)
- **Date:** 2026-10-10

## Context
Evaluation needs trustworthy labels for requests, senders, references, grades and rules over
code-mixed chat (SPEC §13).

## Decision
`datagen/planner.py` (seeded code) writes each transcript as a script of request, noise and
identity events. Gold labels come from that plan in the §4.2 schema, including the expected grade
and rule under policy v0. They are never produced by asking a model. Surface text is produced
from the plan by the renderer; since ADR-0014 this is template-based (phrase banks + code noise),
not an LLM.

## Alternatives considered
- **Model-labelled data:** rejected; labels must not depend on a model's judgement.
- **LLM renderer:** the original choice for surface text; removed by ADR-0014.

## Consequences
- Labels are exact and reproducible from seeds; ≥ 18 templates cover the hard cases (SPEC §13.2).
- Template text is less varied than human chat; the human-written challenge set (ADR-0006)
  measures that gap.
