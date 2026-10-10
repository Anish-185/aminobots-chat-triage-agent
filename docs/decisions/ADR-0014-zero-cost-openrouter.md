# ADR-0014: Zero-cost operation with OpenRouter free models

- **Status:** Accepted
- **Date:** 2026-10-10

## Context
The project must run at $0 (phase 1b). The only possible spend is LLM usage.

## Decision
- **Provider:** OpenRouter only, models whose ID ends in `:free` (validator in `triage/config.py`;
  CLAUDE.md invariant 10). Client: `instructor.from_provider("openrouter/<id>")` (ADR-0004).
- **Limits** (OpenRouter limits docs, 2026-10-10): 20 requests/min; 50/day with < $10 credits
  ever purchased, 1,000/day at ≥ $10. Every request, including retries, counts against a persistent
  daily counter; one repair and one transport retry at most; a 429 waits once, then tries the next
  fallback. Iteration evals use the 10 dev seeds; milestone runs are budgeted (SPEC §14.6).
- **$10 credit purchase:** NOT taken. It is a human decision point.
- **Rotation:** free models come and go. Each role has an ordered `fallbacks` list; spans and eval
  results record the model ID that actually answered; the response cache (SPEC §15.1) makes reruns
  free and stable.
- **Data generation:** template renderer only (phrase banks + code noise). Zero requests consumed,
  and the extraction model is not also the data author. The LLM renderer and fidelity checker are
  removed.
- **Cost:** `cost_usd_billed: 0`; `cost_usd_notional` = tokens × list price of the model's paid
  OpenRouter variant, or null when none exists (`config/pricing.yaml`).

## Candidates (metadata only, `GET /api/v1/models`, 2026-10-10; no model was called)
| Model | Context | Max out | structured_outputs | response_format | Paid variant $/M in · out |
|---|---|---|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b:free` | 262,144 | 235,929 | yes | yes | 0.08 · 0.45 |
| `google/gemma-4-31b-it:free` | 262,144 | 32,768 | no | yes | 0.09 · 0.34 |
| `dots-studio/dots-3-note-preview:free` | 512,000 | 460,800 | yes | yes | none |

None of the descriptions states multilingual or Telugu support; the phase-4 bake-off on the dev
seeds decides. The config lists them in this order as model + fallbacks.

## Alternatives considered
- **Paid Claude / Gemini / Groq profiles:** dropped; they need paid keys or other providers.
- **LLM-rendered data:** dropped; it spends scarce requests and couples author and extractor.

## Consequences
- **Privacy:** free-model providers may log or train on prompts (OpenRouter has separate privacy
  settings for free models). Acceptable only because all data is synthetic; real partner chats
  must never be sent through a free model.
- Eval cadence is quota-bound; a run pauses at a resumable checkpoint instead of dropping work.
- **Paid credits would be worth considering if:** free models are too weak on romanised Telugu;
  the full eval matrix doesn't fit the daily cap; an optional Claude comparison is wanted.
