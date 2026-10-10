Phase 1 — repository bootstrap: tooling, guardrails, CI and decision records. No pipeline logic yet.

## Step 0 — housekeeping (do first)
1. Read CLAUDE.md and docs/SPEC.md in full.
2. Save this prompt verbatim to `docs/build-prompts/phase-01-bootstrap.md`.
3. Verify phase 0:
   - working tree clean
   - `origin` remote set and `main` pushed (`git status -sb`)
   - .claude/agents (3 files) and .claude/commands (4 files) present
   - docs/functional.md and docs/SPEC.md present
   Fix anything missing before continuing, and list the fixes in your report.
4. Produce a plan for steps 1–9 and WAIT for my approval.

## 1. Python project
- `uv init` as a package project named `aminobots-triage`, Python >= 3.11, package directory `triage/`. If uv isn't installed, stop and give me the install command for my OS.
- Runtime deps: pydantic>=2, anthropic, instructor, pyyaml, rapidfuzz, phonenumbers, sqlalchemy, typer, python-dotenv, pandas, scipy, streamlit, faker.
- Dev deps (dependency group): pytest, hypothesis, ruff, pre-commit.
- Commit uv.lock. Use whatever versions resolve today; don't hand-pin.

## 2. Directory layout
- Create the tree from CLAUDE.md "Layout": config/, policy/, prompts/, triage/, triage/executor/, app/ui/, datagen/, data/{world,dev,test,challenge}/, eval/{baselines,results}/, scripts/, tests/, docs/{decisions,data,diagrams,policy}/.
- Add `__init__.py` to Python packages, and a one-line README.md in each otherwise-empty folder saying what will live there.
- data/test/README.md and data/challenge/README.md must each say: "Frozen evaluation data. Do not open, read or modify; only eval/run_eval.py may read it."

## 3. Config and typed loader
- Create config/models.yaml, config/pricing.yaml and config/thresholds.yaml with every key from SPEC §15, including the thresholds table and its defaults.
- pricing.yaml: look up current per-million-token prices for the model IDs in the official Anthropic docs. Record `checked_on` and `source_url`. If you cannot verify a price, set it to null with a TODO; never guess.
- models.yaml: add a `verified_on` field. Check in the Anthropic docs that the listed model IDs exist and support structured outputs. If an ID is wrong, stop and tell me rather than substituting one.
- triage/config.py: Pydantic-validated loaders that fail loudly on missing or extra keys.

## 4. CLI
- triage/cli.py using Typer, with console script `triage`.
- One command, `triage version`, printing the package version and placeholders for policy and prompt versions.

## 5. Quality gates
- pyproject ruff config: line-length 100; select E, F, I, B, UP, S. Allow `assert` (S101) in tests.
- pytest config: register marker `llm` ("calls the real API; skipped when ANTHROPIC_API_KEY is unset"). Default addopts: `-m "not llm"`.
- .pre-commit-config.yaml with:
  - ruff lint and ruff format
  - gitleaks
  - a local hook running scripts/guard_eval_data.py, which rejects any staged add or modify under data/test/ or data/challenge/ (README.md files excepted) unless env ALLOW_EVAL_DATA_COMMIT=1
- Install the hooks: `uv run pre-commit install`.
- .github/workflows/ci.yml on push and PR:
  - checkout
  - setup uv
  - `uv sync`
  - ruff check and format --check
  - `uv run pytest`
  - gitleaks
  No secrets needed; tests must not call the API.

## 6. Repo hygiene
- .env.example with:
  ANTHROPIC_API_KEY=
  DATABASE_URL=sqlite:///triage.db
- LICENSE: MIT for code. data/LICENSE: CC BY 4.0 for the synthetic data.
- Append any missing .gitignore entries for uv/pytest/ruff caches.

## 7. Claude Code guardrail hooks
- Before writing anything, read the current Claude Code documentation on hooks and settings. Use the documented format; don't rely on memory.
- Create .claude/settings.json plus scripts in .claude/hooks/ (executable) for:
  - (a) PreToolUse on file write/edit tools: block any path under data/test/ or data/challenge/, with a clear message (README.md files excepted).
  - (b) PreToolUse on Bash: block `git push --force`, `git tag`, and commands that read files under data/test/ or data/challenge/ (cat, head, tail, less, more, grep, sed, awk, python -c with open()). Allow `uv run python -m eval.run_eval` and `uv run python scripts/check_leakage.py`.
  - (c) PostToolUse after file edits: run `uv run ruff format` on edited .py files.
- Demonstrate (a) and (b): attempt one blocked write and one blocked read, and include the hook output in your report.
- Hooks may not apply inside subagents. Note this as a limitation in the ADR for this phase. The git pre-commit guard in step 5 is the backstop.

## 8. Architecture decision records
- Create docs/decisions/ADR-0001 … ADR-0012 from SPEC §17.
- Template: Title, Status (Accepted), Date, Context, Decision, Alternatives considered, Consequences. At most ~25 lines each.
- Base the content on SPEC and docs/functional.md only; don't invent facts.
- Add ADR-0013 "Claude Code guardrails": the hooks, the git-level backstop, and the subagent limitation.
- Add docs/decisions/README.md as an index table.

## 9. Smoke tests
- tests/test_smoke.py:
  - imports triage
  - loads all three config files
  - runs `triage version` through Typer's CliRunner
- tests/test_guard_eval_data.py: unit-test guard_eval_data.py against fake staged-path lists.

## 10. CLAUDE.md amendment
Under "Working style", replace "Do not create git tags or push." with:
"Do not create git tags. Push only when the human explicitly says 'push'."

## Acceptance criteria
- `uv run pytest` passes.
- `uv run pre-commit run --all-files` passes.
- `uv run triage version` prints.
- Hook demos are shown.
- Tree matches CLAUDE.md.
- No secrets in the repo.

## Finish
End with the phase report from CLAUDE.md (all six sections), including your proposed commits. Don't commit until I say "commit". Don't push until I say "push".
