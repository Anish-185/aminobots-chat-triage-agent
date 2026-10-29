"""Check every relative link in the repo's markdown: the target exists and, for a .md target, the
#anchor matches a heading (GitHub slug rules). Skips URLs and the frozen eval folders.
Run: uv run python scripts/check_links.py  (exit 1 on any broken link)
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from guard_eval_data import FROZEN_DIRS as FROZEN  # noqa: E402  (CLAUDE.md #6: never read)

SKIP = {".git", ".venv", ".cache", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```.*?^```", re.S | re.M)


def slug(heading: str) -> str:
    s = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return s.replace(" ", "-")


def anchors(md: Path) -> set[str]:
    text = FENCE.sub("", md.read_text(encoding="utf-8"))
    return {slug(h) for h in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", text, re.M)}


def markdown_files() -> list[Path]:
    found = []
    for d, dirs, files in os.walk(ROOT):
        rel = Path(d).relative_to(ROOT).as_posix() + "/"
        # prune caches, tools and the frozen eval folders (never entered, never read)
        dirs[:] = [x for x in dirs if x not in SKIP and f"{rel}{x}/".lstrip("./") not in FROZEN]
        found += [Path(d) / f for f in files if f.endswith(".md")]
    return sorted(found)


def check() -> list[str]:
    errors = []
    for md in markdown_files():
        text = FENCE.sub("", md.read_text(encoding="utf-8"))
        for m in LINK.finditer(text):
            target = m.group(1) or m.group(2)
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):  # http:, mailto:, …
                continue
            path, _, anchor = target.partition("#")
            dest = (md.parent / path).resolve() if path else md
            rel = md.relative_to(ROOT)
            if path and not dest.exists():
                errors.append(f"{rel}: missing target {target}")
            elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
                errors.append(f"{rel}: no heading for #{anchor} in {dest.relative_to(ROOT)}")
    return errors


if __name__ == "__main__":
    errs = check()
    print("\n".join(errs) or f"links OK ({len(markdown_files())} markdown files)")
    sys.exit(1 if errs else 0)
