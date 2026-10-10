Phase 1b — zero-cost amendment: OpenRouter free models only. It applies on top of phase 1 and supersedes any earlier phase-1b text. First save this prompt verbatim to docs/build-prompts/phase-01b-zero-cost.md.

Project policy: the project runs at $0. LLM access is ONLY through OpenRouter free models (IDs ending in ":free"). No paid models and no other providers. All API keys stay EMPTY in the repo; I add mine to a local .env myself.

## 1. CLAUDE.md
Add invariant 10:
"10. Zero spend. Only OpenRouter models whose ID ends in ':free' may be called. Before any task that would use more than 10 LLM requests, state the request count and wait for approval. CI and unit tests never call any LLM API. Free models have a daily request cap (50/day on an unfunded account), so treat every request as scarce: no retry loops, no exploratory calls."

## 2. Dependencies and keys
- Remove the `anthropic` dependency if nothing uses it.
- Add the `openai` SDK (OpenRouter is OpenAI-compatible).
- Check Instructor's current docs for the recommended way to use OpenRouter (an OpenAI client with base_url, or `from_provider`), and note which modes work with models that lack native structured-output support (JSON mode / MD_JSON).
- .env.example contains ONLY:
  OPENROUTER_API_KEY=
  DATABASE_URL=sqlite:///triage.db
  Remove any other key lines. Do not create .env.

## 3. Models config (config/models.yaml and SPEC §15)
- Each role (extractor, baseline_b1) has:
  - `provider: openrouter`
  - `model` (must end in `:free`)
  - `fallbacks` (an ordered list of other `:free` IDs)
  - `temperature`
  - `verified_on`
- Use the OpenRouter models API or docs to find **3 candidate free models currently listed** that ideally support structured outputs or response_format (check each model's supported parameters) and handle multilingual text. Leave the final choice open: phase 4 runs a bake-off on the dev seeds.
- Record the candidates and their capabilities in `docs/decisions/ADR-0014`. Do NOT call the models now; read metadata only. If the metadata endpoint needs a key, list what you'd check and leave TODOs.
- A config validator rejects any model ID not ending in `:free`. Add a unit test for it.
- Remove the `renderer` and `fidelity` roles (see 5) and the Claude references from SPEC §15.

## 4. Limits and cost (config/thresholds.yaml, config/pricing.yaml, SPEC §10.3, §14.2)
- thresholds.yaml (do not guess other values):
  openrouter_rpm: 20
  openrouter_rpd: 50
  llm_max_repair_retries: 1
  llm_max_transport_retries: 1
- Specify an LLM limiter in SPEC §10.3:
  - It enforces rpm and rpd.
  - It counts EVERY request, including retries, in a persistent daily counter at `.cache/llm/quota.json`.
  - On a 429, wait once and then try the next fallback model; never loop.
  - When the daily quota runs out, it pauses with a resumable checkpoint (completed transcripts are saved and skipped on re-run). It never silently drops work.
  - A run stops early with a clear message if the remaining quota is smaller than the job.
- Cost metrics (SPEC §14.2): report input/output tokens, `cost_usd_billed: 0`, and `cost_usd_notional`. Notional cost = tokens × the list price of the same model's paid variant on OpenRouter, if one exists (with `checked_on` and `source_url` in pricing.yaml); otherwise null.

## 5. Data generation without an LLM (SPEC §13.3, §13.5)
- The renderer is template-based only: hand-written phrase banks per intent, script (roman_te, te_script, en) and formality in `datagen/phrasebanks/*.yaml`, filled with entities and then noised by code.
- Remove the LLM renderer and the fidelity checker from SPEC.
- Rationale for the ADR: zero requests consumed, and the extraction model is not also the data author.

## 6. Response cache (new SPEC §15.1, spec only; implemented in phase 4)
- A disk cache under `.cache/llm/` (gitignored).
- Key = sha256(model ID + prompt_id + prompt_version + rendered input + temperature).
- Always on for eval runs.
- Spans record `cache_hit` and the actual model ID that answered (a fallback may answer).
- Eval results record the model ID per transcript, because free models can rotate.

## 7. Evaluation budget (SPEC §14.6, new)
- Iteration runs: dev seeds only (10 requests).
- Milestone runs: pipeline on a fixed, seeded 30-transcript dev sample + all test + all challenge; B1 on test + challenge only.
- The eval CLI prints the projected request count before starting and asks for confirmation if it exceeds the remaining daily quota.

## 8. Live demo (SPEC §1 / UI note)
- The deployed app serves cached results for bundled samples.
- Live runs require the visitor to paste their own OpenRouter key into a session-only field. It is never stored or logged.
- An optional server key from Streamlit secrets is used only with a small daily cap from config.

## 9. ADR-0014 "Zero-cost operation with OpenRouter free models"
Cover:
- the provider choice and the `:free`-only rule
- rate limits (20/min, 50/day unfunded) and their effect on the eval cadence
- the one-time $10 credit purchase that would raise the cap to 1,000/day: NOT taken; it is a human decision point
- free-model rotation and how we record model IDs, use fallbacks and rely on the cache
- privacy: free providers may log prompts; acceptable only because all data is synthetic, and real partner chats must never be sent
- the template renderer
- notional cost

Update ADR-0004 so structured outputs go via Instructor with OpenRouter, falling back to JSON mode plus Pydantic validation when a model lacks native support.

## Finish
Bump SPEC's version line. Give the phase report from CLAUDE.md, plus:
- the 3 candidate free models, with their supported parameters and context length
- every config value you could not verify
