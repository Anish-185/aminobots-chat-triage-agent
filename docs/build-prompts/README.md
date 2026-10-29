# Build log

Each phase prompt given to Claude Code is saved here verbatim as `phase-NN-<short-name>.md`, as the first step of that phase. Together these files are the record of how the project was built.

## Index

| Phase | Prompt | What it asked for |
|---|---|---|
| 0 | [phase-00-init.md](phase-00-init.md) | First attempt: create the repo with planning files only (superseded by the reset) |
| 0 | [phase-00-reset.md](phase-00-reset.md) | Restart from the simplified v2 context: free-only, website showcase, demo scope |
| 1 | [phase-01-bootstrap.md](phase-01-bootstrap.md) | First-attempt bootstrap: tooling, guardrails, CI, ADRs (superseded by v2) |
| 1 | [phase-01-bootstrap-v2.md](phase-01-bootstrap-v2.md) | Bootstrap for v2: dependencies, config, frozen-data guards, SPEC patch → PR #2 |
| 1b | [phase-01b-zero-cost.md](phase-01b-zero-cost.md) | Zero-cost amendment: OpenRouter `:free` models only, keys empty in the repo |
| 2 | [phase-02-submission-docs.md](phase-02-submission-docs.md) | APPROACH.md, architecture and workflow diagrams, build plan → PR #3 |
| 3 | [phase-03-data.md](phase-03-data.md) | Schemas, parser, roster, 15 dev chats + gold, gold validator → PR #4 |
| 4 | [phase-04-extraction.md](phase-04-extraction.md) | LLM extraction, grounding, cache, free-model bake-off; test set and B1 dropped → PR #5 |
| 5 | [phase-05-decisions.md](phase-05-decisions.md) | Slot contract, identity, policy v1, routing, pipeline, CLI, run_eval → PR #6, **v0.1** |
| 6 | [phase-06-website.md](phase-06-website.md) | `time_unspecified` fix, the Triage Desk website and local API → PR #7, **v0.3** |
| 7 | [phase-07-final.md](phase-07-final.md) | Policy v2, final eval, ARTEFACT, final docs, submission checklist → **v1.0** |
