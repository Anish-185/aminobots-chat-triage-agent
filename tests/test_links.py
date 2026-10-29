"""Every relative markdown link resolves (scripts/check_links.py)."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "check_links", Path(__file__).resolve().parent.parent / "scripts" / "check_links.py"
)
check_links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_links)


def test_no_broken_relative_links():
    assert check_links.check() == []
