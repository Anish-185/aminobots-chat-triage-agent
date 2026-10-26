#!/usr/bin/env python3
"""PreToolUse guard for Bash.

Blocks: `git push` with force flags, `git tag`, and any command that references
data/test/ or data/challenge/ (cat/head/grep/sed/awk/python -c open(), but also ls, cp, >).
Allows exactly the two eval entry points, and only when not chained with other commands.
Pattern matching is a speed bump, not a sandbox.
"""

import re

from _frozen import block, run

ALLOW = re.compile(
    r"^\s*uv run python (-m eval\.run_eval|scripts/check_leakage\.py)(\s[^;&|`$<>()]*)?\s*$"
)
GIT = r"\bgit\s+(?:(?:-C|-c)\s+\S+\s+|--?[\w-]+(?:=\S+)?\s+)*"  # git + global options
FORCE_PUSH = re.compile(GIT + r"push\b[^;&|]*(\s--force(-with-lease)?\b|\s-[a-zA-Z]*f\b|\s\+\S)")
TAG = re.compile(GIT + r"tag\b")
FROZEN_REF = re.compile(r"data/+(test|challenge)\b")


def check(event: dict) -> None:
    cmd = (event.get("tool_input") or {}).get("command") or ""
    if FORCE_PUSH.search(cmd):
        block("BLOCKED by guard_bash.py: force push is not allowed.")
    if TAG.search(cmd):
        block("BLOCKED by guard_bash.py: the human creates tags (CLAUDE.md working style).")
    if FROZEN_REF.search(cmd) and not ALLOW.match(cmd):
        block(
            "BLOCKED by guard_bash.py: command references frozen evaluation data "
            "(data/test, data/challenge; CLAUDE.md invariant 6). Only "
            "`uv run python -m eval.run_eval` and `uv run python scripts/check_leakage.py` may."
        )


if __name__ == "__main__":
    run(check)
