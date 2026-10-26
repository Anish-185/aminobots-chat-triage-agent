#!/usr/bin/env python3
"""PreToolUse guard for Bash.

Blocks: `git push` with force flags, `git tag`, and any command that can reach
data/test/ or data/challenge/:
- a literal reference (cat/head/grep/python -c open(), ls, cp, >, ...);
- a glob right after data/ (`data/*`, `data/**`, `data/{test,dev}`, `data/t*`);
- a path that lands in a frozen set after `cd` (e.g. `cd data && cat test/x`);
- a recursive tool (grep -r, find, tree, du, ls -R, cp -r, tar, zip, rsync) aimed at a
  directory that contains a frozen set (`.`, `data`, `*`, the repo root, `/`), or run there
  with no path;
- rg with ignore-file bypass flags (rg honours the repo's .ignore otherwise).
data/dev and data/world stay allowed. Allows exactly the eval entry point, unchained.
Pattern matching is a speed bump, not a sandbox.
"""

import re
import shlex
from pathlib import Path

from _frozen import block, is_frozen_ancestor, rel_frozen, run

ALLOW = re.compile(r"^\s*uv run python -m eval\.run_eval(\s[^;&|`$<>()]*)?\s*$")
GIT = r"\bgit\s+(?:(?:-C|-c)\s+\S+\s+|--?[\w-]+(?:=\S+)?\s+)*"  # git + global options
FORCE_PUSH = re.compile(GIT + r"push\b[^;&|]*(\s--force(-with-lease)?\b|\s-[a-zA-Z]*f\b|\s\+\S)")
TAG = re.compile(GIT + r"tag\b")
FROZEN_REF = re.compile(r"data/+(test|challenge)\b")
DATA_GLOB = re.compile(r"data/+[^\s/'\"]*[*?\[{]")
GLOB_CHARS = re.compile(r"[*?\[{]")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*\n).*?\n[ \t]*\2[ \t]*(?=\n|$)", re.DOTALL)

ALWAYS_RECURSIVE = {"find", "tree", "du", "tar", "zip", "rsync"}
RECURSIVE_FLAG = {
    "grep": re.compile(r"^(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive|--dereference-recursive)$"),
    "egrep": re.compile(r"^(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)$"),
    "fgrep": re.compile(r"^(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)$"),
    "ls": re.compile(r"^(-[a-zA-Z]*R[a-zA-Z]*|--recursive)$"),
    "cp": re.compile(r"^(-[a-zA-Z]*[rRa][a-zA-Z]*|--recursive|--archive)$"),
}
GREPS = {"grep", "egrep", "fgrep"}
VALUE_OPTS = {"-e", "-f", "--regexp", "--file", "--include", "--exclude", "--exclude-dir"}
VALUE_OPTS |= {"-A", "-B", "-C", "-m", "-d", "-D", "--max-count", "--context"}
RG_BYPASS = re.compile(r"^(-[a-zA-Z]*u[a-zA-Z]*|--no-ignore\S*|--unrestricted)$")
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "\n"}
FROZEN_MSG = (
    "BLOCKED by guard_bash.py: command can reach frozen evaluation data "
    "(data/test, data/challenge; CLAUDE.md invariant 6). Only "
    "`uv run python -m eval.run_eval` may."
)


def _strip_heredocs(cmd: str) -> str:
    """Drop heredoc bodies: they are stdin data, not commands (literal checks already ran)."""
    return HEREDOC.sub(lambda m: m.group(3), cmd)


def _segments(cmd: str) -> list[list[str]]:
    # A newline separates commands like `;` (inside quotes it only changes the quoted text).
    text = _strip_heredocs(cmd).replace("\n", " ; ")
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
    lex.whitespace_split = True
    segs: list[list[str]] = [[]]
    for tok in lex:
        if tok in SEPARATORS:
            segs.append([])
        else:
            segs[-1].append(tok)
    return [s for s in segs if s]


def _glob_base(arg: str) -> str:
    """The literal directory part of a path that contains glob characters."""
    m = GLOB_CHARS.search(arg)
    if not m:
        return arg
    return arg[: m.start()].rpartition("/")[0] or "."


def _check_segment(seg: list[str], cwd: str) -> str:
    """Block if the segment reaches a frozen set; return the cwd after the segment."""
    while seg and re.match(r"^\w+=", seg[0]):  # leading VAR=value
        seg = seg[1:]
    if not seg:
        return cwd
    tool, args = Path(seg[0]).name, seg[1:]
    for a in args:
        if not a.startswith("-") and rel_frozen(a, cwd):
            block(FROZEN_MSG)
    if tool == "cd":
        return str((Path(cwd) / args[0]).resolve()) if args else cwd
    if tool == "rg" and any(RG_BYPASS.match(a) for a in args):
        block(FROZEN_MSG)
    flag = RECURSIVE_FLAG.get(tool)
    if tool in ALWAYS_RECURSIVE or (flag and any(flag.match(a) for a in args)):
        if tool == "find":  # starting points come before the first expression token
            paths = []
            for a in args:
                if a.startswith(("-", "(", "!")):
                    break
                paths.append(a)
        else:
            paths, skip = [], False
            for a in args:
                if skip:
                    skip = False
                elif a in VALUE_OPTS:
                    skip = True
                elif not a.startswith("-"):
                    paths.append(a)
            if tool in GREPS and not any(a in {"-e", "-f", "--regexp", "--file"} for a in args):
                paths = paths[1:]  # first positional is the pattern
        for p in paths or ["."]:
            if is_frozen_ancestor(_glob_base(p), cwd):
                block(FROZEN_MSG)
    return cwd


def check(event: dict) -> None:
    cmd = (event.get("tool_input") or {}).get("command") or ""
    if FORCE_PUSH.search(cmd):
        block("BLOCKED by guard_bash.py: force push is not allowed.")
    if TAG.search(cmd):
        block("BLOCKED by guard_bash.py: the human creates tags (CLAUDE.md, Git).")
    if ALLOW.match(cmd):
        return
    if FROZEN_REF.search(cmd) or DATA_GLOB.search(cmd):
        block(FROZEN_MSG)
    try:
        segments = _segments(cmd)
    except ValueError:  # unbalanced quotes: fail closed only if data/ is mentioned
        if "data" in cmd:
            block(FROZEN_MSG)
        return
    cwd = event.get("cwd") or "."
    for seg in segments:
        cwd = _check_segment(seg, cwd)


if __name__ == "__main__":
    run(check)
