#!/usr/bin/env python3
"""PreToolUse guard for file tools: block paths under data/test/ or data/challenge/.

README.md files in those folders are exempt. Read/Grep/Glob are covered too, since
invariant 6 forbids reading the frozen sets, not only writing them. Grep/Glob are also
blocked when aimed at data/ itself or given a glob that starts with a data/ wildcard
(`data/*`, `data/**`, `data/{test,dev}`). Searches from the repo root rely on the
root .ignore file, which ripgrep (behind Grep/Glob) honours.
"""

import re
from pathlib import Path

from _frozen import ROOT, block, is_frozen_ancestor, rel_frozen, run

DATA_GLOB = re.compile(r"^data/+[^/]*[*?\[{]")
MSG = (
    "BLOCKED by .claude/hooks/guard_paths.py: {} can reach frozen evaluation data "
    "(CLAUDE.md invariant 6). Only eval/run_eval.py may read it."
)


def _search_target(ti: dict, cwd: str | None) -> Path:
    p = Path(ti.get("path") or cwd or ROOT)
    return (p if p.is_absolute() else Path(cwd or ROOT) / p).resolve()


def check(event: dict) -> None:
    ti = event.get("tool_input") or {}
    cwd = event.get("cwd")
    for key in ("file_path", "notebook_path", "path"):
        if not ti.get(key):
            continue
        rel = rel_frozen(ti[key], cwd)
        if rel and not rel.endswith("/README.md"):
            block(MSG.format(rel))
    if event.get("tool_name") not in ("Grep", "Glob"):
        return
    base = _search_target(ti, cwd)
    if base != ROOT and is_frozen_ancestor(str(base)):
        block(MSG.format(ti.get("path")))
    pattern = ti.get("pattern") if event.get("tool_name") == "Glob" else ti.get("glob")
    if pattern and base.is_relative_to(ROOT):
        full = (base / pattern).as_posix()
        rel = full[len(ROOT.as_posix()) :].lstrip("/")
        if DATA_GLOB.match(rel) or rel_frozen(rel):
            block(MSG.format(pattern))


if __name__ == "__main__":
    run(check)
