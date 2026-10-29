"""Policy engine (SPEC §9): every rule evaluated, most cautious grade wins, lowest-numbered rule
with that grade cited, all matches recorded, no match → default. Grades can only go down."""

from datetime import datetime
from pathlib import Path
from typing import get_args

import rule_engine
import yaml
from pydantic import BaseModel, ConfigDict

from triage.config import load_policy_config
from triage.schemas import Candidate, Grade, Identity, Intent, RuleCheck, RuleId

POLICY_DIR = Path(__file__).resolve().parent.parent / "policy"
POLICY = POLICY_DIR / f"policy_v{load_policy_config().version}.yaml"  # config/policy.yaml


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: RuleId
    grade: Grade
    text: str
    when: str | None = None  # None only for the default rule


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: int
    grades: list[Grade]
    intents: dict[str, dict]
    rules: list[Rule]
    default: Rule

    def caution(self, grade: Grade) -> int:
        return self.grades.index(grade)


def load_policy(path: Path = POLICY) -> Policy:
    policy = Policy.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    nums = [int(r.id[1:]) for r in [*policy.rules, policy.default]]
    if nums != sorted(nums) or len(set(nums)) != len(nums):
        raise ValueError(f"{path}: rules must be listed once each, in ID order: {nums}")
    if missing := set(get_args(Intent)) - policy.intents.keys():
        raise ValueError(f"{path}: no policy row for intents {sorted(missing)}")
    for r in policy.rules:
        rule_engine.Rule(r.when)  # fail at load time on a bad expression
    return policy


def context(
    c: Candidate, ident: Identity, policy: Policy, now: datetime, cutoff_hours: float
) -> dict:
    intent = policy.intents[c.intent]
    slot = c.entities.slot_datetime
    return {
        "intent": c.intent,
        "risk": intent["risk"],
        "discloses": intent["discloses"],
        "sender_state": ident.state,
        "authorised": ident.authorised,
        "on_behalf": ident.on_behalf,
        "on_behalf_verified": ident.on_behalf_verified,
        "flags": list(c.flags),
        "status": c.status,
        "slot_hours_ahead": (slot - now).total_seconds() / 3600 if slot else None,
        "slot_cutoff_hours": cutoff_hours,
    }


def decide(ctx: dict, policy: Policy) -> tuple[Grade, RuleId, list[RuleId], list[RuleCheck]]:
    checks = [
        RuleCheck(rule_id=r.id, matched=rule_engine.Rule(r.when).matches(ctx)) for r in policy.rules
    ]
    matched = [r for r, chk in zip(policy.rules, checks, strict=True) if chk.matched]
    if not matched:
        d = policy.default
        return d.grade, d.id, [d.id], [*checks, RuleCheck(rule_id=d.id, matched=True)]
    grade = max((r.grade for r in matched), key=policy.caution)
    cited = next(r.id for r in matched if r.grade == grade)  # rules are listed in ID order
    checks.append(RuleCheck(rule_id=policy.default.id, matched=False))
    return grade, cited, [r.id for r in matched], checks
