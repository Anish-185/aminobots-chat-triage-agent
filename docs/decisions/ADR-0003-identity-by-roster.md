# ADR-0003: Identity by roster lookup only

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
Many senders cannot be confirmed: new numbers, shared counter phones, duplicate display names.
Trusting display names, self-introductions or in-chat vouching invites payment-diversion fraud
(functional.md §1.3, §3.3).

## Decision
`triage/identity.py` (code only) resolves the sender of `primary_msg_id` against the roster
(SPEC §6). A roster phone match to exactly one, unshared contact gives `CONFIRMED`; a shared or
multi-contact phone gives `SHARED_DEVICE`; otherwise fuzzy name matching (rapidfuzz, threshold
`name_match`) only flags `CLAIMED` (one match), `AMBIGUOUS` (several) or `UNKNOWN` (none). A
`security_code_changed` or `number_changed` event before the request downgrades `CONFIRMED` to
`CLAIMED`.

## Alternatives considered
- **Trusting display names or self-claims** ("idi naa kotha number, Suresh"): rejected as the
  impersonation path the brief warns about.

## Consequences
- A self-claim or vouching never yields `CONFIRMED`; authority is never inferred from candidates.
- Unconfirmed-sender recall = 1.0 is a hard eval gate (SPEC §14.4).
