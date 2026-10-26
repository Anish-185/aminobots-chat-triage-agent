# CLAUDE.md — Aminobots Chat Triage Agent

## What this project is

A **demo build** that reads a WhatsApp group-chat export (Telugu–English, mostly romanised) from a
partner group and returns every real request in it. Each request comes with who asked it and
whether that is confirmed, a grade (`act` / `seek_approval` / `hand_off` / `refuse`), the numbered
rule that decided the grade, and the message IDs it relied on. Every action is **simulated and
logged; nothing is executed.** It is showcased on a local website.

**Sources of truth, in order:** `docs/context/PROJECT_CONTEXT.md` (decisions) → `docs/SPEC.md`
(contracts) → this file. If they disagree, the higher one wins. Tell the human about the conflict
instead of choosing silently.

**Keep it simple.** Choose the simplest thing that meets the brief. Reuse open-source libraries
(`uv add`, never copied in). Own code covers only the prompt, the rules file, the roster and thin
glue.

## Invariants (never violate, not even "temporarily")

1. **The model describes; code decides.** The LLM only extracts requests, evidence IDs,
   references, entities and uncertainty flags. Identity, authority, grade and rule are decided in
   code.
2. **Autonomy only goes down.** Every rule is evaluated and the most cautious grade wins. No match
   → default rule (`hand_off`). Never add a path that raises a grade after the policy has run.
3. **Fail closed.** Errors or uncertainty lead to more human involvement, never less. A failed run
   is marked `UNPROCESSED` and the whole chat is handed off, never shown as "no requests".
4. **Evidence or it doesn't exist.** A candidate whose message IDs are not in the chat is dropped
   and logged.
5. **Simulate, never execute.** The action layer only appends to JSONL files under `runs/`. A test
   proves it imports no network client.
6. **Frozen eval data.** Never open, read, write, list or quote anything under `data/test/` or
   `data/challenge/`, except by running `eval/run_eval.py`. Never copy their text into prompts,
   tests, fixtures or docs.
7. **No secrets in the repo.** Every key stays empty in the repo; the human fills a local `.env`.
8. **Deterministic time.** "Now" = the timestamp of the chat's last message. No wall-clock time in
   pipeline logic.
9. **Synthetic data only.** Phones are `+91` followed by 10 digits starting with 0–5; assert
   `phonenumbers.is_valid_number() == False` for each.
10. **Zero spend, free LLMs only.** Only OpenRouter model IDs ending in `:free` (enforced by the
    config validator, with a test). No other LLM provider SDK. Before any LLM call, state the
    model and request count; ask before more than 10 requests. CI and unit tests never call an
    LLM. The free cap is 50 requests/day: no retry loops, no exploratory calls. Anything that needs
    a paid plan → stop and propose a free alternative (💰 decision point).
11. **Prefer libraries.** Any own module over ~150 lines needs a one-line justification at its top.
12. **Local only.** The website and API run on localhost. No deployment config or workflows until
    the human explicitly approves publishing.

## Pipeline (SPEC §3)

`parse` (chat-miner) → `extract` (LLM via Instructor, `prompts/extract/vN.md`) → `ground` (code)
→ `identity` (code, roster) → `policy` (rule-engine, `policy/policy_vN.yaml`) → route:
`act` → `runs/actions.jsonl` · `seek_approval` → `runs/approvals.jsonl` ·
`hand_off` → `runs/handoffs.jsonl` · `refuse` → `runs/alerts.jsonl`. Traces go to Langfuse.

## Layout (target; folders appear in the phase that fills them)

```
CLAUDE.md  README.md  APPROACH.md  ARTEFACT.md
config/      models.yaml (:free only), pricing.yaml, thresholds.yaml
policy/      policy_v1.yaml, CHANGELOG.md
prompts/     extract/vN.md, baseline/vN.md, CHANGELOG.md   (runtime prompt pack)
triage/      schemas.py parse.py extract.py ground.py identity.py policy.py route.py pipeline.py
             cli.py config.py serve.py
api/         main.py (FastAPI)
site/        static HTML + Tailwind CDN + vanilla JS, data/*.json
data/        world/ (roster.yaml)  dev/  test/ (frozen)  challenge/ (frozen, human-written)
eval/        run_eval.py, results/<tag>/
scripts/     guard_eval_data.py, small utilities
tests/
docs/        SPEC.md functional.md context/ build-prompts/ adr/ *.drawio.svg build-plan.md
.claude/     settings.json, hooks/
```

## How work arrives

The human gives one phase prompt at a time. **First step of every phase:** save the prompt
verbatim to `docs/build-prompts/phase-NN-<short-name>.md`. Never edit an earlier phase file. Do
only the current phase, then stop. For a phase touching more than one file, plan first; when the
prompt says "wait for approval", stop after the plan. Check current docs for any library or
service before using it; never rely on memory for APIs, versions or prices.

## Conventions

- Python 3.11+ (3.12 pinned). uv, ruff, pytest. Type hints everywhere.
- Pydantic v2 models in `triage/schemas.py` are the only contracts between stages.
- Prompts: `prompts/<name>/v<N>.md` with YAML front-matter (`id`, `version`, `model`,
  `output_schema`, `purpose`). A released version is immutable; changes → `vN+1` +
  `prompts/CHANGELOG.md`.
- Policy: `policy/policy_v<N>.yaml`, history in `policy/CHANGELOG.md`. Rule IDs never reused.
- Config: thresholds, model IDs, prices in `config/*.yaml`. No magic numbers. Unverifiable values
  are `null` with a TODO, never guessed.
- LLM tests are marked `@pytest.mark.llm` and skipped without `OPENROUTER_API_KEY`.
- Conventional Commits (`feat:` `fix:` `test:` `docs:` `eval:` `chore:`), one logical change each.
- New dependency → short ADR (≤ 25 lines) in `docs/adr/`.

## Commands

```
uv sync
uv run pytest                      # unit tests, no API
uv run ruff check . && uv run ruff format .
uv run triage run <chat.txt>       # from Phase 5
uv run python -m eval.run_eval --split dev --tag <tag>   # from Phase 5
uv run python -m triage.serve      # site + API on localhost, from Phase 7
```

## Definition of done (every phase)

- Tests pass, ruff is clean, new behaviour has tests.
- `docs/SPEC.md` still accurate; a contract change updates SPEC in the same commit.
- If pipeline behaviour changed, run the dev eval (within the request budget) and report deltas.
- End with the **phase report**, exactly these six sections:
  1. **Done** — what was built and the files touched.
  2. **Tests / eval** — commands and results, failures quoted verbatim.
  3. **Errors / blockers** — full error text.
  4. **Deviations** — anything done differently from the prompt or SPEC, and why.
  5. **Open questions** — SPEC ambiguities left unresolved.
  6. **Proposed commits.**

## Git

- Commit and push to the current phase branch on your own, with clear messages, and open a PR to
  main at the end of the phase. Never push to main, never merge, never force-push, never create
  tags.
