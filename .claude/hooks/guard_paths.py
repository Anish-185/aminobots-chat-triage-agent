#!/usr/bin/env python3
"""PreToolUse guard for file tools: block paths under data/test/ or data/challenge/.

README.md files in those folders are exempt. Read/Grep/Glob are covered too, since
invariant 6 forbids reading the frozen sets, not only writing them.
"""

from _frozen import block, rel_frozen, run


def check(event: dict) -> None:
    ti = event.get("tool_input") or {}
    for key in ("file_path", "notebook_path", "path"):
        if not ti.get(key):
            continue
        rel = rel_frozen(ti[key], event.get("cwd"))
        if rel and not rel.endswith("/README.md"):
            block(
                f"BLOCKED by .claude/hooks/guard_paths.py: {rel} is frozen evaluation data "
                "(CLAUDE.md invariant 6). Only eval/run_eval.py may read it."
            )


if __name__ == "__main__":
    run(check)
