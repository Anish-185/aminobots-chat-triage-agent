PR #2 approved. Merge it yourself once CI is green (merge commit, delete the branch), then
start Phase 2 from the updated main.

## Standing rules (add to CLAUDE.md, replacing the plan/approval wording)
Work autonomously. For each phase: write a short plan into the phase prompt's build log, then
proceed without waiting. Fix CI failures, lint errors and broken tests yourself. When I write
"PR #N approved" in a prompt, merge that PR yourself once CI is green.
STOP and ask only if a step would: cost money or need a paid plan; make more than 10 LLM
requests; deploy or publish anything; read or change data/test or data/challenge (other than
through eval/run_eval.py); touch secrets; force-push, tag, or push directly to main; or break a
SPEC invariant. If network access blocks you, record it as a blocker and carry on with the rest.

## Decisions for this phase (apply to SPEC and config; add a v2.2 change-log entry)
- Assumptions: add A4 ("now" = timestamp of the chat's last message) and A5 (roster.yaml is the
  only source of identity). Keep A6.
- Roles are fixed: owner, manager, staff, accounts, aminobots_staff.
- models.yaml, verified by the planner on openrouter.ai on 2026-10-26:
  - nvidia/nemotron-3-super-120b-a12b:free: exists; context 262,144; tools + JSON-schema
    structured outputs (Instructor JSON_SCHEMA mode); free endpoint logs prompts (fine:
    synthetic data only). Make it the default model_id.
  - google/gemma-4-31b-it:free: exists; context 262K; structured outputs unverified, so use
    JSON / MD_JSON mode. Fallback.
  - dots-studio/dots-3-note-preview:free: REMOVE (marked for deprecation by end of 2026).
  - Paid-variant prices stay null + TODO until Phase 4 can reach openrouter.ai.
  The bake-off in Phase 4 becomes 2 models × ~10 chats ≈ 20 requests.
- chat-miner's ~800 MB footprint is accepted for a local demo. Add one line to ADR 0001.

# Phase 2 — Submission docs

Save this prompt verbatim to docs/build-prompts/phase-02-submission-docs.md. No LLM calls.
Demo build: keep it short and consistent with SPEC; link out rather than repeat.

1. APPROACH.md (repo root, ≤ 4 pages, ≈ 1,800 words of prose maximum; tables and diagrams are
   linked). Start with a 3-line preface: who it's for, the build-vs-reuse stance (link ADR 0001),
   and links to both diagrams. Then sections exactly as the brief requires:
   A. Problem scoping: user (partner-support agent + approver, finance, security), the input as
      it really arrives, capabilities built vs deferred (SPEC §1.4), measurable success (the
      pass rule).
   B. System design: the stage table (receives / returns / model or code), the agent pattern
      (fixed pipeline, one extraction call) vs the rejected ReAct tool-agent and why, where a
      person approves, the failure table.
   C. Data and knowledge: dev/test/challenge splits and who writes them, why they're a fair
      test (noise list, adversarial cases, both mandated scenarios verbatim), provenance and
      licences, how eval data is kept separate (hooks, pre-commit guard, .ignore), how knowledge
      is represented (roster.yaml + policy_v1.yaml, no retrieval needed).
   D. Evaluation framework: the metrics table and why each fits this problem, the must-refuse
      and must-hand-off cases, the pass rule, baseline B1, per-script slices.
   E. Risks and responsibility: what a wrong output does (fraudulent payout change vs annoyed
      partner), how "simulate, never execute" is enforced (JSONL-only action layer + no-network
      test), synthetic text sent to free providers that log prompts, and ONE deliberate
      trade-off: most-cautious-wins and fail-closed send more items to people, which costs
      reviewer time. We will measure that cost as the share of legitimate requests graded
      seek_approval.
   State plans as plans; measured results belong in ARTEFACT.md later.

2. docs/architecture.drawio.svg: components, models, data stores, tools, and how one request
   flows: WhatsApp .txt → parse (chat-miner) → render → extract (OpenRouter :free via
   Instructor, diskcache, Langfuse) → ground → identity (roster.yaml) → policy (rule-engine,
   policy_v1.yaml) → route → runs/*.jsonl; plus the FastAPI + static site (local) and eval/.

3. docs/workflow.drawio.svg: input → output, with model steps vs code steps visibly different
   (e.g. colour + legend), the human approval point (seek_approval → approver → approve/reject),
   the hand-off and refuse branches, and the failure path (validation fails twice / 429 →
   UNPROCESSED → whole chat handed off).

   Both diagrams: a real .drawio.svg, meaning an SVG with a white background whose root element
   carries the uncompressed mxfile XML (HTML-escaped) in its `content` attribute, with the drawn
   SVG matching that XML. Hand-write both parts, or use a permissive open-source helper if one
   genuinely saves effort (licence-check it; no paid tools). Validate that the SVG parses and
   that the embedded XML parses as an mxfile. List "open both files in diagrams.net to confirm
   they are editable" as a check for me to run.

4. docs/build-plan.md: phases P0–P9 (from context §4.12), each with deliverable, exit criterion
   and request budget; the 50/day budget and the declined 💰 $10 option; top 5 risks with
   mitigations (free models rotating out, rate limits, Telugu realism, chat-miner parsing,
   deployment requirement deferred); owners as placeholders (Member A–D).

5. README: link APPROACH.md, both diagrams and build-plan.md; update the status line.

6. Finish: run all checks, commit, push branch phase-02-submission-docs, open a PR, then give
   the six-part phase report with APPROACH.md's word count, and stop.

---

## Plan (Claude Code, written before starting)

1. Merge PR #2 (CI green) — done; remote branch delete blocked by the git proxy (HTTP 403).
2. CLAUDE.md: replace plan/approval wording and Git section with the standing rules.
3. SPEC v2.2 + config: A4, A5, fixed roles, models (nemotron default JSON_SCHEMA, gemma fallback
   JSON/MD_JSON, drop dots), pricing nulls, bake-off 2×10; ADR 0001 footprint line. Tests updated.
4. Diagrams: one small Python script (`scripts/make_diagrams.py`, stdlib only) that defines the
   boxes once and emits both the mxGraphModel XML and the matching SVG, so the two can't drift.
   Validate with xml.etree in a test.
5. APPROACH.md (≤ 1,800 words of prose), docs/build-plan.md, README links + status.
6. Checks (pytest, ruff, pre-commit), commit, push, PR, phase report.
