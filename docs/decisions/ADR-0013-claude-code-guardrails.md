# ADR-0013: Claude Code guardrails

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
Claude Code builds this repo. Invariant 6 (never read the frozen eval sets) and the no-tag rule
must hold even when the agent errs.

## Decision
`.claude/settings.json` hooks (format checked against the Claude Code hooks docs, 2026-10-10):
- **PreToolUse Write|Edit|NotebookEdit|Read|Grep|Glob** → `guard_paths.py` blocks paths under
  `data/test/` or `data/challenge/` (README.md exempt).
- **PreToolUse Bash** → `guard_bash.py` blocks force push, `git tag`, and any command referencing
  the frozen folders, except unchained `uv run python -m eval.run_eval` / `scripts/check_leakage.py`.
- **PostToolUse Write|Edit** → `ruff format` on edited `.py` files.
Guards exit 2 to block and also exit 2 on any internal error (fail closed).

**Backstop:** the git pre-commit hook `scripts/guard_eval_data.py` rejects staged changes under
the frozen folders unless `ALLOW_EVAL_DATA_COMMIT=1`.

## Alternatives considered
- Relying on CLAUDE.md instructions alone: rejected; instructions are not enforcement.

## Consequences / limitations
- **Subagents:** the phase prompt assumed hooks may not apply in subagents; the current docs say
  settings hooks do fire inside subagents. Treat this as unverified here; the git hook is the backstop.
- `onFailure: "block"` needs Claude Code ≥ 2.1.295 (2.1.282 installed), so a missing interpreter
  fails open; hooks load only when the session's project root is this repo.
- The Bash guard is pattern matching: indirection (scripts, variables, globs) can bypass it, and it
  can block harmless commands that mention the paths.
