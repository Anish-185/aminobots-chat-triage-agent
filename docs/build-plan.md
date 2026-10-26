# Build plan

Phases follow [context §4.12](context/PROJECT_CONTEXT.md). One phase prompt at a time; each ends
with a phase report and a PR. Tags are created by the human after reviewing eval results.
Owners are placeholders until the team assigns them.

## Phases

| Phase | Deliverable | Exit criterion | LLM requests | Owner |
|---|---|---|---|---|
| P0 | Reset: CLAUDE.md, SPEC v2, functional.md, README | Old work archived; docs merged | 0 | Member A |
| P1 | Bootstrap: deps, config + `:free` validator, guards, CI | CI green; guard tests pass | 0 | Member A |
| P2 | Submission docs: APPROACH.md, two `.drawio.svg` diagrams, this plan | Diagrams parse and open in diagrams.net; APPROACH ≤ 4 pages | 0 | Member B |
| P3 | Schemas, parser (chat-miner), roster, ~15 dev chats + gold, gold validator | Every dev chat parses; gold validates; all phones invalid | 0 | Member C |
| P4 | Extract + ground + cache + Langfuse; free-model bake-off | Valid structured output on dev; default model chosen | ≈ 20 (bake-off: 2 models × ~10 chats) + ≈ 15 | Member B |
| P5 | Identity + policy + routing + CLI + eval script | All worked checks pass; dev eval runs end to end → **v0.1** | ≈ 15 | Member A |
| P6 | Human test/challenge sets, baseline B1, milestone eval | Pass rule evaluated on test + challenge → **v0.2** | ≈ 65 | Member D |
| P7 | Website + API, local only, one serve command | Demo opens on localhost; "try your own" works or explains → **v0.3** | ≤ 10 (precompute uses cache) | Member C |
| P8 | Error analysis, prompt iteration (dev only), hardening | Dev metrics improve without breaking hard gates | ≈ 45 (3 dev iterations) | Member B |
| P9 | ARTEFACT.md, final APPROACH/README, link check; publish decision | Final milestone eval committed → **v1.0** | ≈ 65 | Member D |

Total ≈ 250 requests over the project.

## Request budget

- OpenRouter free tier: **50 requests/day**, 20/minute. Free models only (`:free`); billed cost is
  $0. Retries count against the quota, so there are no retry loops and every request is cached.
- A dev iteration costs about 15 requests; a milestone eval about 65 (1–2 days of quota).
- Any step needing more than 10 requests is announced first and needs approval.
- 💰 **Declined option:** a one-time $10 OpenRouter credit purchase would raise the cap to 1,000
  requests/day (free models stay $0). Not taken; revisit only if the daily cap becomes the
  bottleneck.

## Top risks

| Risk | Impact | Mitigation |
|---|---|---|
| Free models rotate out or get rate-limited at peak times | Extraction stops; results not comparable | Two configured models (nemotron default, gemma fallback); response cache; strict-model mode for milestones; re-check models in P4 |
| Daily request cap (50/day) | Slow iteration; milestone evals take 1–2 days | Cache every response; small dev set; plan evals across days |
| Telugu realism of synthetic chats | Eval overstates real performance | Teammate reviews Telugu; humans write test/challenge; per-script slices |
| chat-miner parsing gaps (system lines, formats) | Lost messages or wrong IDs | Verify in P3; ≤ 30-line pre-pass for system lines; parser tests on edge cases |
| Deployment requirement deferred (brief asks for a public URL) | Submission gap | Site and API stay deploy-ready (relative paths, configurable API URL); publishing decided explicitly before P9 |
