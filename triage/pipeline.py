"""parse → render → extract → ground → identity → policy → route (SPEC §3), as one function.

Any failure before grading (parse error, ExtractionFailed, 429, timeout, unavailable model) makes
the run UNPROCESSED with a single hand-off record for the whole chat (fail closed, SPEC §3.5).
"""

import hashlib
from pathlib import Path
from typing import get_args

import diskcache
import instructor
import yaml

from triage import llm
from triage.config import Candidate, load_models, load_thresholds
from triage.extract import ExtractionFailed, extract, load_prompt
from triage.ground import ground
from triage.identity import identify
from triage.parse import parse_chat
from triage.policy import context, decide, load_policy
from triage.render import render
from triage.route import record, unprocessed, write
from triage.schemas import GradedRequest, Role, Roster, RunResult

WORLD = Path(__file__).resolve().parent.parent / "data" / "world"


def run(
    chat: Path,
    roster_path: Path = WORLD / "roster.yaml",
    contacts_path: Path = WORLD / "contacts.yaml",
    runs_dir: Path | None = None,
    candidate: Candidate | None = None,
    cache: diskcache.Cache | None = None,
    client: instructor.Instructor | None = None,
) -> RunResult:
    """Writes the JSONL logs only when runs_dir is given (the CLI passes RUNS; eval does not)."""
    models, th, policy = load_models(), load_thresholds(), load_policy()
    role = models.roles.extractor
    cand = candidate or next(c for c in models.candidates if c.id == role.model)
    meta, _ = load_prompt(role.prompt_version)
    prompt = f"{meta['id']}/v{meta['version']}"
    digest = hashlib.sha256(chat.read_bytes() + f"{llm.model_tag(cand)}|{prompt}".encode())
    run_id = digest.hexdigest()[:12]
    result = RunResult(
        run_id=run_id,
        chat=chat.name,
        status="OK",
        model=cand.id,
        prompt=prompt,
        policy_version=policy.version,
    )

    def fail(error: str) -> RunResult:
        result.status, result.error = "UNPROCESSED", error
        result.log = [unprocessed(run_id, result.now, error)]
        if runs_dir:
            write(result.log, runs_dir)
        return result

    try:
        result.messages = parse_chat(chat, contacts_path)
        if not result.messages:
            raise ValueError("no messages")
    except Exception as exc:  # any parse failure fails closed
        return fail(f"parse error: {exc}")
    result.now = max(m.ts for m in result.messages)
    result.rendered = render(result.messages)
    try:
        extraction, info = extract(
            result.messages, cand, role.temperature, role.prompt_version, cache, client
        )
    except (ExtractionFailed, llm.LLMError) as exc:
        spent = getattr(exc, "requests", 0) or getattr(exc.__cause__, "requests", 0)
        result.llm = {"requests": spent, "cached": False, "error": type(exc).__name__}
        return fail(f"{type(exc).__name__}: {exc}")
    result.extraction, result.llm = extraction, info.__dict__

    roster = Roster.model_validate(yaml.safe_load(roster_path.read_text(encoding="utf-8")))
    by_id = {m.id: m for m in result.messages}
    kept, result.rejected = ground(extraction, result.messages)
    for n, c in enumerate(kept, 1):
        allowed = set(policy.intents[c.intent]["roles"] or get_args(Role))
        ident, flags, internal = identify(c, result.messages, roster, allowed, th.name_match)
        c = c.model_copy(update={"flags": list(dict.fromkeys([*c.flags, *flags]))})
        ctx = context(c, ident, policy, result.now, th.slot_cutoff_hours)
        grade, rule_id, matched, checks = decide(ctx, policy)
        primary = by_id[c.primary_msg_id]
        graded = GradedRequest(
            request_id=f"{run_id}-r{n}",
            candidate=c,
            requester_phone=primary.phone,
            requester_name=primary.display_name,
            identity=ident,
            grade=grade,
            rule_id=rule_id,
            matched_rules=matched,
            rule_checks=checks,
            internal=internal,
        )
        (result.internal_requests if internal else result.requests).append(graded)
    graded_all = result.requests + result.internal_requests
    result.log = [record(run_id, r, result.now) for r in graded_all]
    if runs_dir:
        write(result.log, runs_dir)
    return result
