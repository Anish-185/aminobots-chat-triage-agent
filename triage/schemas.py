"""Pydantic v2 contracts between stages (SPEC §5). The only shapes passed between modules."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

MsgId = Annotated[str, Field(pattern=r"^m\d{3,}$")]
Kind = Literal["text", "media", "system"]
Intent = Literal[
    "delivery_slot_change",
    "order_change",
    "status_query",
    "invoice_request",
    "payout_details_change",
    "refund_request",
    "complaint",
    "other",
]
Grade = Literal["act", "seek_approval", "hand_off", "refuse"]
IdentityState = Literal["CONFIRMED", "AMBIGUOUS", "UNCONFIRMED"]
Role = Literal["owner", "manager", "staff", "accounts", "aminobots_staff"]
Flag = Literal[
    "referent_unresolved",
    "outlet_ambiguous",
    "time_unspecified",
    "intent_unclear",
    "possible_forward",
    "injection_attempt",
]
Status = Literal["open", "cancelled", "handled"]
RuleId = Literal["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- parse ---------------------------------------------------------------------------------


class Message(_Model):
    id: MsgId
    ts: datetime
    author_raw: str | None  # as exported: a phone number or a saved name; None for system lines
    phone: str | None  # E.164, resolved in code (never sent to the model)
    display_name: str | None
    text: str
    kind: Kind
    subject_raw: str | None = None  # system lines: whose security code changed / who left / ...
    subject_phone: str | None = None  # subject_raw resolved like an author


# --- extract (LLM output) --------------------------------------------------------------------


class Entities(_Model):
    outlet: str | None = None
    # Slot changes (SPEC §3.3, v2.5): the model gives a day offset from the primary message's
    # date and a 24 h time; code computes slot_datetime (hidden from the model's schema).
    # No ge/pattern here: the free endpoint's strict decoder left these null when constrained
    # (bake-off v1, reasoning trial v2); grounding validates them in code instead.
    slot_day_offset: int | None = Field(
        default=None,
        description="Slot changes: days after the primary message's date "
        "(0 ivala/today, 1 repu/tomorrow, 2 ellundi); null only if no day is stated",
    )
    slot_time: str | None = Field(
        default=None,
        description='Slot changes: earliest time stated for that delivery, 24 h "HH:MM" '
        '("2 pm" -> "14:00"); null only if no time is stated',
    )
    slot_datetime: SkipJsonSchema[datetime | None] = None
    amount: float | None = None
    details: str | None = None


class Candidate(_Model):
    intent: Intent
    gloss: str
    primary_msg_id: MsgId
    evidence_msg_ids: list[MsgId] = Field(min_length=1)
    refers_to_msg_id: MsgId | None = None
    on_behalf_of: str | None = None
    entities: Entities = Entities()
    status: Status = "open"
    flags: list[Flag] = []


class ExtractionResult(_Model):
    candidates: list[Candidate]


class Rejected(_Model):
    """A candidate dropped by grounding (SPEC §3.4), kept for the run record."""

    candidate: Candidate
    reason: str  # "rejected_hallucination: ..."


# --- identity / policy / route ----------------------------------------------------------------


class Identity(_Model):
    state: IdentityState
    contact_ids: list[str] = []  # 1 if CONFIRMED; 2+ if AMBIGUOUS; 0-1 if UNCONFIRMED
    role: Role | None = None
    outlets: list[str] = []
    authorised: bool = False
    on_behalf: bool = False  # asks for someone else, or about another partner's outlet
    on_behalf_verified: bool = False  # sender is a roster delegate of the principal
    target_outlets: list[str] = []  # outlets the request is about, resolved in code
    reason: str


class RuleCheck(_Model):
    rule_id: RuleId
    matched: bool


class GradedRequest(_Model):
    request_id: str
    candidate: Candidate
    requester_phone: str | None
    requester_name: str | None
    identity: Identity
    grade: Grade
    rule_id: RuleId
    matched_rules: list[RuleId]
    rule_checks: list[RuleCheck]
    internal: bool = False  # aminobots_staff requests (A6): logged, not listed, not scored


class LogRecord(_Model):
    run_id: str
    request_id: str
    grade: Grade
    rule_id: RuleId | None  # None only for an UNPROCESSED whole-chat hand-off
    evidence_msg_ids: list[MsgId]
    now: datetime | None  # timestamp of the chat's last message (SPEC §2.8); None if unparsable
    action: str
    requester: str | None = None  # phone masked to the last 4 digits
    record_only: bool = False  # R8: cancelled / already handled
    internal: bool = False  # aminobots_staff request (A6)
    simulated: Literal[True] = True


class RunResult(_Model):
    """Everything one run produced, stage by stage; the CLI, eval and website all read this."""

    run_id: str
    chat: str
    status: Literal["OK", "UNPROCESSED"]
    error: str | None = None
    now: datetime | None = None
    model: str
    prompt: str
    policy_version: int
    messages: list[Message] = []
    rendered: str | None = None
    extraction: ExtractionResult | None = None
    llm: dict | None = None  # CallInfo: cached, requests, latency, tokens
    requests: list[GradedRequest] = []
    internal_requests: list[GradedRequest] = []  # aminobots_staff (A6): logged, not listed
    rejected: list[Rejected] = []
    log: list[LogRecord] = []


# --- world ------------------------------------------------------------------------------------


class Outlet(_Model):
    id: str
    name: str
    area: str


class Partner(_Model):
    id: str
    name: str
    outlets: list[Outlet]


class Contact(_Model):
    id: str
    name: str
    phone: str
    role: Role
    partner: str | None = None  # None for aminobots_staff
    outlets: list[str] = []
    shared: bool = False  # phone used by more than one person
    delegate_for: list[str] = []  # contact IDs this person may act for


class Roster(_Model):
    partners: list[Partner]
    contacts: list[Contact]


# --- gold -------------------------------------------------------------------------------------


class GoldSource(_Model):
    author: str
    method: str
    licence: str
    telugu_reviewed_by: str | None


class GoldFacts(_Model):
    """The policy inputs a human decided for this request (SPEC §9 context)."""

    authorised: bool
    on_behalf: bool = False
    on_behalf_verified: bool = False
    slot_datetime: datetime | None = None  # the slot asked to move; hours are taken from "now"


class GoldRequest(_Model):
    id: str
    intent: Intent
    gloss: str
    primary_msg_id: MsgId
    evidence_msg_ids: list[MsgId] = Field(min_length=1)
    requester_phone: str | None
    identity_state: IdentityState
    status: Status = "open"
    flags: list[Flag] = []
    facts: GoldFacts
    grade: Grade
    rule_id: RuleId


class GoldChat(_Model):
    chat_id: str
    partner: str
    source: GoldSource
    requests: list[GoldRequest]
    internal_requests: list[GoldRequest] = []  # aminobots_staff (A6): not scored
    notes: str = ""
