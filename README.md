# Aminobots Chat Triage Agent

Reads a WhatsApp partner group chat (Telugu–English, mostly romanised) and lists every real
request. Each request shows who asked and whether that is confirmed, a grade (act / seek approval /
hand off / refuse), the numbered rule behind the grade, and the messages it relied on.

> Simulation only — no action is executed. Synthetic data only. Free LLMs only ($0).

**Status:** v1.1 + Phase 10 integrations (Datasette audit trail, promptfoo red team) — complete demo (local): both mandated scenarios pass (on builder-generated,
no-longer-blind challenge chats). Results, limitations and ownership are in
[ARTEFACT.md](ARTEFACT.md). Tagged prototypes: v0.1, v0.3, v1.0 (v1.1 is tagged by the human). The first attempt is preserved on
the `archive/first-attempt` branch.

## Docs

- [ARTEFACT.md](ARTEFACT.md): what was built, prototypes, results, error analysis, limitations
- [APPROACH.md](APPROACH.md): problem scoping, system design, data, evaluation, risks
- Diagrams: [architecture](docs/architecture.drawio.svg) · [workflow](docs/workflow.drawio.svg)
  (editable in diagrams.net; regenerate with `uv run python scripts/make_diagrams.py`)
- [Build plan](docs/build-plan.md): phases, request budget, risks
- [Functional document](docs/functional.md): problem, current process, interventions, user
  journey, tech construct
- [SPEC v2.9](docs/SPEC.md): contracts, policy, evaluation
- [Policy v2](policy/policy_v2.yaml) and [prompt pack](prompts/CHANGELOG.md)
- [Screenshots](docs/screenshots/) and the [submission checklist](docs/submission-checklist.md)
- [Project context](docs/context/PROJECT_CONTEXT.md): decisions and the original brief
- [CLAUDE.md](CLAUDE.md): rules for the coding agent
- [ADRs](docs/adr/): build-vs-reuse decisions
- [Website design brief](docs/design/brief.md) and [self-review](docs/design/review.md)
- [Build prompts](docs/build-prompts/README.md): how the project was built, phase by phase

## Run the demo

Needs [uv](https://docs.astral.sh/uv/) and Python 3.12.

```
git clone https://github.com/Anish-185/aminobots-chat-triage-agent.git && cd aminobots-chat-triage-agent
uv sync
uv run python -m triage.serve     # → http://127.0.0.1:8000/
```

Optional, for **Try your own** on new chats: `cp .env.example .env` and fill `OPENROUTER_API_KEY`
locally (never commit it).

The story, the desk and the results run from precomputed pipeline output in `site/data/`, so
they need no key and make no LLM call. **Try your own** sends a chat to the local API, which runs
the real pipeline with the free model in `config/models.yaml`. It uses your `.env` key (capped at
10 new requests a day), or a key typed into the page, which is used once and never stored, logged
or traced. Rebuild the site data from the cache with `uv run python scripts/build_site_data.py`.

| Watch it work | The desk | Phone |
|---|---|---|
| ![Scenario 1 stamped by rule R6](docs/screenshots/1440-story-d01-6.jpg) | ![Request table](docs/screenshots/1440-desk.jpg) | ![Hero at 375 px](docs/screenshots/375-top.jpg) |

### Audit trail (Datasette)

Every simulated decision the CLI writes to `runs/*.jsonl` can be explored in one table, with
facets on grade, rule, identity state and team (the requester's partner). Local only; the site's
Results section links to it.

```
uv run python -m triage.audit                              # runs/*.jsonl → runs/audit.db
uv run datasette runs/audit.db -m config/datasette.yaml    # → http://127.0.0.1:8001/audit/records
```

![Audit trail in Datasette, faceted by rule, team, grade and identity state](docs/screenshots/1440-audit-trail.jpg)

### Red team (promptfoo)

Ten synthetic attack chats (injection, fake authority, self-claimed identity, a request hidden in
a forward, pure chatter) run through the real pipeline with promptfoo via `npx` (needs Node; no
project dependency). Details and assertions: [eval/redteam/README.md](eval/redteam/README.md);
results: [eval/results/redteam-v1/](eval/results/redteam-v1/).

```
PROMPTFOO_DISABLE_TELEMETRY=1 uv run npx -y promptfoo@0.125.1 eval -c eval/redteam/promptfooconfig.yaml \
  -j 1 --no-cache -o eval/results/redteam-v1/report.html -o eval/results/redteam-v1/results.json
```

Other commands:

```
uv run pytest                                          # unit tests, no API calls
uv run python -m triage.cli run data/dev/d01.txt       # one chat in the terminal
uv run python -m eval.run_eval --split dev --tag <tag> # eval (cached answers cost nothing)
```

## Licence

Code: MIT ([LICENSE](LICENSE)). Synthetic data: CC BY 4.0 ([data/LICENSE](data/LICENSE)).
