# ADR-0008: Streamlit Community Cloud + Neon Postgres

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
The demo must be publicly reachable at no cost and keep runs, queues and the append-only action
log across restarts (SPEC §11; functional.md §5.7).

## Decision
Host the Streamlit app on Streamlit Community Cloud and use Neon Postgres via `DATABASE_URL`;
SQLite locally. Postgres also gets a trigger rejecting UPDATE/DELETE on `actions`.

## Alternatives considered
- **Hugging Face Spaces:** needs a paid plan for this use.
- **Free hosts with local SQLite:** their disks are ephemeral, so state would be lost.

## Consequences
- Two free services to configure; the app must handle DB unavailability by returning results
  marked `persisted: false` with a red banner (SPEC §10.3).
