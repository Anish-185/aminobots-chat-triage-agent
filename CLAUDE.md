# CLAUDE.md — Aminobots Request Triage

## What this project is

A system that reads a WhatsApp-style partner group-chat transcript (Telugu–English, code-mixed,
often romanised) and returns every real request in it. Each request is attributed to its sender,
with an explicit state when the sender cannot be confirmed. Each request is graded
`act` / `seek_approval` / `hand_off` / `refuse` by a numbered autonomy policy, citing the deciding
rule and the evidence message IDs. All actions are simulated and logged; nothing is executed.

**`docs/SPEC.md` is the source of truth.** If this file and SPEC disagree, SPEC wins. Tell the
human about the conflict instead of choosing silently.

## Non-negotiable invariants (never violate, not even "temporarily")

1. **Nothing executes for real.** `triage/executor/` only appends rows to the action log. No
   HTTP, SMTP, socket or messaging client may be imported anywhere under `triage/executor/`.
   `tests/test_no_network.py` enforces this.
2. **The model never decides identity, authority, grade or rule.** LLM output only *describes*
   the chat: intents, message IDs, entities, cues, uncertainty flags. Sender identity is a
   roster lookup in code. The grade comes from the policy engine in code.
3. **Autonomy can only go down.** The policy is most-restrictive-wins over all matching rules,
   and no match means the default rule (`hand_off`). Never add a code path that raises a grade
   after the policy engine has run.
4. **Fail closed.** Errors, invalid model output, unresolved references and unconfirmed senders
   must lead to more human involvement, never less. Never return an empty result to hide a
   failure; mark the run `UNPROCESSED` and hand off.
5. **Every request cites evidence.** Each request record carries message IDs that exist in the
   transcript. A candidate with no valid evidence is discarded and logged as a rejected
   hallucination.
6. **Evaluation data is sacred.** Never open, read, write, summarise or quote anything under
   `data/test/` or `data/challenge/`, except by running `eval/run_eval.py`. Never copy text from
   those sets into prompts, few-shot examples, tests, fixtures or docs.
7. **No secrets in the repo.** Keys come from environment variables: `.env` locally, host
   secrets in production. `.env` is gitignored.
8. **Deterministic time.** "Now" for a transcript is the timestamp of its last message. Pipeline
   logic never uses wall-clock time.
9. **No real personal data.** All names, numbers and outlets are synthetic. Every synthetic phone
   number must fail `phonenumbers.is_valid_number()`.
10. Zero spend. Only OpenRouter models whose ID ends in ':free' may be called. Before any task that
    would use more than 10 LLM requests, state the request count and wait for approval. CI and unit
    tests never call any LLM API. Free models have a daily request cap (50/day on an unfunded
    account), so treat every request as scarce: no retry loops, no exploratory calls.

## Architecture (one line per stage)

`ingest` (code) → `extract` (LLM, `prompts/extract/vN.md`) → `ground` (code) → `identity`
(code, roster) → `policy` (code, `policy/policy_vN.yaml`) → route to one of:

- `act` → simulated executor
- `seek_approval` → approval queue
- `hand_off` → team queue
- `refuse` → refusal record and security alert

Every route ends in the append-only action log. Every stage writes a span to the trace store.

## Layout

```
CLAUDE.md  README.md  APPROACH.md  ARTEFACT.md
config/          models.yaml, pricing.yaml, thresholds.yaml
policy/          policy_vN.yaml, action_catalogue.yaml, CHANGELOG.md
prompts/         RUNTIME prompt pack: extract/, baseline/, CHANGELOG.md
triage/          schemas.py ingest.py extract.py ground.py identity.py policy.py
                 pipeline.py trace.py storage.py approvals.py cli.py executor/
app/ui/          Streamlit multipage app
datagen/         world.py planner.py render.py noise.py split.py phrasebanks/
data/            world/  dev/  test/ (frozen)  challenge/ (human-written, frozen)  MANIFEST.json
eval/            matcher.py metrics.py run_eval.py slices.py baselines/ results/<tag>/
scripts/         one-off utilities (validate_gold.py, check_leakage.py, ...)
tests/
docs/            SPEC.md, functional.md, decisions/ (ADRs), build-prompts/ (phase prompt log), data/, diagrams/
.claude/         settings.json (hooks), hooks/, agents/, commands/
```

**How work arrives:** the human gives you one phase prompt at a time. Each phase prompt may
include fixes for errors reported from the previous phase. As the **first step of every phase**,
save the phase prompt verbatim to `docs/build-prompts/phase-NN-<short-name>.md`; this is the
project's record of how it was built. This log is **not** the runtime prompt pack, which lives in
`prompts/`. Never edit an earlier phase file.

## Conventions

- Python 3.11+. Use uv for the environment and dependencies, ruff for lint and format, pytest
  for tests, and Hypothesis for property tests. Type hints everywhere.
- The Pydantic v2 models in `triage/schemas.py` are the only data contracts between stages.
- **Prompts** live at `prompts/<name>/v<N>.md`, with YAML front-matter: `id`, `version`, `model`,
  `output_schema`, `purpose`. A released version is immutable. To change a prompt, add `vN+1`
  and an entry in `prompts/CHANGELOG.md`.
- **Policy** lives at `policy/policy_v<N>.yaml`, with history in `policy/CHANGELOG.md`. Rule IDs
  are never reused or renumbered.
- **Config:** thresholds, model IDs and prices live in `config/*.yaml`. No magic numbers in code.
- **LLM tests** are marked `@pytest.mark.llm` and skipped when `OPENROUTER_API_KEY` is unset. CI
  never calls the API; unit tests use recorded fixtures.
- **Commits** use Conventional Commits (`feat:` `fix:` `test:` `docs:` `eval:` `chore:`), one
  logical change per commit.
- **New dependency** → add a short ADR in `docs/decisions/`.

## Commands

```
uv sync
uv run pytest                      # unit tests, no API
uv run pytest -m llm               # live LLM tests, needs key
uv run ruff check . && uv run ruff format .
uv run triage run data/dev/seeds/<id>.json --roster data/world/roster_dev.yaml
uv run triage trace <run_id>       # step-by-step inspection
uv run python -m eval.run_eval --split dev --system pipeline --tag <tag>
uv run streamlit run app/ui/Home.py
```

## Definition of done (every task)

- Tests pass, ruff is clean, and new behaviour has tests.
- `docs/SPEC.md` is still accurate. If you changed a contract, update SPEC in the same commit and
  say so explicitly.
- If pipeline behaviour changed, run the dev-split eval and report the metric deltas.
- End with a **phase report** in this exact structure, so the human can bring it to the next
  phase:
  1. Done: what was built, and the files touched.
  2. Tests and eval: commands run and results, with failures quoted verbatim.
  3. Errors and blockers: anything that failed or was skipped, with the full error text.
  4. Deviations: anything you did differently from the prompt or SPEC, and why.
  5. Open questions: SPEC ambiguities you did not resolve.
  6. Proposed commits.

## Working style

- Plan first for any task touching more than one file. When a phase prompt says
  "wait for approval", stop after the plan.
- Work in small steps and run tests often. Do not refactor outside the task's scope.
- If SPEC seems wrong, ambiguous or incomplete, stop and ask. Never invent behaviour silently.
- Do not create git tags. Push only when the human explicitly says 'push'. The human tags
  prototypes after reviewing eval results.
