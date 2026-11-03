"""Red team v1 (Phase 10): the suite's chats and config, checked without any LLM call."""

import re
from pathlib import Path

import yaml

from triage import pipeline
from triage.parse import parse_chat

ROOT = Path(__file__).resolve().parent.parent
RT = ROOT / "eval" / "redteam"
CHATS = sorted((RT / "chats").glob("*.txt"))
CONFIG = yaml.safe_load((RT / "promptfooconfig.yaml").read_text(encoding="utf-8"))
NOTICE = "Messages and calls are end-to-end encrypted"


def test_every_chat_parses_and_is_in_the_config_once():
    assert len(CHATS) == 10
    used = [t["vars"]["chat"] for t in CONFIG["tests"]]
    assert sorted(used) == [p.relative_to(ROOT).as_posix() for p in CHATS]
    for path in CHATS:
        assert len(parse_chat(path, pipeline.WORLD / "contacts.yaml")) >= 3, path.name


def test_chats_are_fresh_not_copied_from_dev():
    def lines(p: Path) -> set[str]:
        body = (re.sub(r"^.*? - ", "", ln) for ln in p.read_text(encoding="utf-8").splitlines())
        # short acknowledgements ("Divya Aminobots: Noted madam") may repeat; content may not
        return {b for b in body if len(b.split(": ", 1)[-1]) > 20 and NOTICE not in b}

    dev = set().union(*(lines(p) for p in (ROOT / "data" / "dev").glob("*.txt")))
    for path in CHATS:
        assert not lines(path) & dev, path.name


def test_every_chat_is_checked_for_grades_and_act_and_one_attack_property():
    default = {a["value"] for a in CONFIG["defaultTest"]["assert"]}
    assert default == {"file://asserts.js:noGradesInModelOutput", "file://asserts.js:nothingActs"}
    for t in CONFIG["tests"]:
        assert len(t["assert"]) == 1 and t["assert"][0]["type"] == "javascript"


def test_provider_writes_no_run_logs():
    src = (RT / "provider.py").read_text(encoding="utf-8")
    assert "pipeline.run(chat, cache=cache)" in src and "runs_dir" not in src
