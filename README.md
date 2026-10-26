# Aminobots Chat Triage Agent

Reads a WhatsApp partner group chat (Telugu–English, mostly romanised) and lists every real
request. Each request shows who asked and whether that is confirmed, a grade (act / seek approval /
hand off / refuse), the numbered rule behind the grade, and the messages it relied on.

> Simulation only — no action is executed. Synthetic data only. Free LLMs only ($0).

**Status:** Phase 0: reset to simplified design. No runnable pipeline yet. The first attempt is
preserved on the `archive/first-attempt` branch.

## Docs

- [Functional document](docs/functional.md): problem, current process, interventions, user
  journey, tech construct
- [SPEC v2](docs/SPEC.md): contracts, policy, evaluation
- [Project context](docs/context/PROJECT_CONTEXT.md): decisions and the original brief
- [CLAUDE.md](CLAUDE.md): rules for the coding agent
- [Build prompts](docs/build-prompts/): how the project was built, phase by phase

## Setup (so far)

```
uv sync
cp .env.example .env    # fill OPENROUTER_API_KEY locally; never commit it
uv run pytest
```

The run and website commands arrive in later phases (see SPEC §13).

## Licence

Code: MIT ([LICENSE](LICENSE)). Synthetic data: CC BY 4.0 ([data/LICENSE](data/LICENSE)).
