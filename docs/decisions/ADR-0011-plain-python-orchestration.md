# ADR-0011: Plain Python orchestration and a DB approval queue

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
The workflow is fixed (ADR-0001) and pauses for humans only at approval and hand-off
(SPEC §10.1, §11).

## Decision
Orchestrate stages as plain Python (`triage/pipeline.py`). Approvals are rows in the
`approval_queue` table (pending/approved/edited/rejected, approver, reason), not a suspended
graph.

## Alternatives considered
- **LangGraph with its interrupt pattern:** rejected; it is built for agent graphs, and this is a
  non-agent workflow.

## Consequences
- Approval constraints are enforced in storage code: only `seek_approval` items are approvable,
  edits stay within the action schema, rejection needs a reason, and no path creates an action for
  `hand_off` or `refuse`.
