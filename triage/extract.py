"""Extraction (SPEC §3.3): render the chat, one model call, output validated as ExtractionResult.

A schema failure after Instructor's one repair retry, or a transport error, raises
ExtractionFailed; the pipeline turns that into UNPROCESSED (SPEC §3.5). RateLimited and
ModelUnavailable propagate unchanged: strict mode stops cleanly and a re-run resumes from cache.
"""

from pathlib import Path

import diskcache
import instructor
import yaml

from triage import llm
from triage.config import Candidate
from triage.render import render
from triage.schemas import ExtractionResult, Message

PROMPTS = Path(__file__).resolve().parent.parent / "prompts" / "extract"


class ExtractionFailed(RuntimeError):
    """The chat could not be extracted; the whole chat is handed off as UNPROCESSED."""


def load_prompt(version: int) -> tuple[dict, str]:
    """Front-matter and body of prompts/extract/v<version>.md."""
    _, front, body = (PROMPTS / f"v{version}.md").read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(front), body.strip()


def user_message(messages: list[Message]) -> str:
    """NOW (SPEC §2.8: the last message's timestamp) followed by the rendered chat."""
    now = max(m.ts for m in messages)
    return f"NOW: {now:%Y-%m-%d %H:%M}\n\n{render(messages)}"


def extract(
    messages: list[Message],
    candidate: Candidate,
    temperature: float,
    prompt_version: int,
    cache: diskcache.Cache | None = None,
    client: instructor.Instructor | None = None,
) -> tuple[ExtractionResult, llm.CallInfo]:
    if not messages:
        raise ExtractionFailed("chat has no messages")
    meta, system = load_prompt(prompt_version)
    try:
        result, info = llm.call(
            candidate,
            f"{meta['id']}/v{meta['version']}",
            system,
            user_message(messages),
            ExtractionResult,
            temperature,
            cache=cache,
            client=client,
        )
    except (llm.RateLimited, llm.ModelUnavailable):
        raise
    except llm.LLMError as exc:
        raise ExtractionFailed(str(exc)) from exc
    return ExtractionResult.model_validate(result.model_dump()), info
