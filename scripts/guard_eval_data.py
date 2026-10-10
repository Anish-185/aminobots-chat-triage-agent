"""Pre-commit guard: reject staged changes under the frozen eval sets (CLAUDE.md invariant 6).

Any staged path under data/test/ or data/challenge/ (add, modify, delete, rename/copy source or
destination) is rejected, except README.md files. Set ALLOW_EVAL_DATA_COMMIT=1 to override.
"""

import os
import subprocess
import sys
from collections.abc import Iterable

FROZEN_DIRS = ("data/test/", "data/challenge/")


def violations(paths: Iterable[str]) -> list[str]:
    """Return the frozen, non-README paths among `paths` (repo-relative, '/' separated)."""
    return sorted(
        {p for p in paths if p.startswith(FROZEN_DIRS) and p.rsplit("/", 1)[-1] != "README.md"}
    )


def staged_paths() -> list[str]:
    """All paths touched by the index, including both sides of renames and copies."""
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z", "--no-renames"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    fields = [f for f in out.split("\0") if f]
    return fields[1::2]  # with --no-renames every entry is exactly <status>\0<path>


def main() -> int:
    bad = violations(staged_paths())
    if not bad:
        return 0
    if os.environ.get("ALLOW_EVAL_DATA_COMMIT") == "1":
        print(f"guard_eval_data: ALLOW_EVAL_DATA_COMMIT=1, allowing {len(bad)} frozen path(s)")
        return 0
    print("guard_eval_data: refusing to commit changes to frozen evaluation data:", file=sys.stderr)
    for p in bad:
        print(f"  {p}", file=sys.stderr)
    print("Set ALLOW_EVAL_DATA_COMMIT=1 only for a deliberate, reviewed freeze.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
