PR #6 approved: merge it yourself once CI is green, then report the merge commit SHA at the top
of your reply so I can tag v0.1. Then start Phase 6 from the updated main.

> **Free LLMs only.** Use only OpenRouter models whose ID ends in `:free`, as listed in
> `config/models.yaml`. Never call a paid model, never add a paid provider or SDK, and never use
> a key other than `OPENROUTER_API_KEY` from the local `.env`. Before making any LLM call, state
> which free model and how many requests you will use, and wait for my approval if it is more
> than 10.

Pre-approved: up to 5 LLM requests (live tests of "Try your own"). Everything else must come
from the cache.

## Part A — fix (SPEC change-log v2.6)
1. Add time_unspecified only when status == open. Closed requests (cancelled/handled) execute
   nothing, so a missing slot time is irrelevant to them; R8 then applies as intended. Add tests.
   Re-run run_eval on dev from cache only (0 new LLM requests; if anything would miss the cache,
   stop and report). Save it as eval/results/v0.1.1-dev/ and report the before/after table.

# Phase 6 — The website → v0.3

Save this prompt verbatim to docs/build-prompts/phase-06-website.md and append your plan.
Local only: no hosting files, no Pages, no deploy workflows. Free tools only.

## B. Skills and the quality bar (do this before any design work)
2. Skills:
   - Use the **frontend-design** skill.
   - Use the **UI UX Pro Max** skill.
   - If either is not installed, find its official source, check the licence is permissive and
     there's no cost, then install it at project level under .claude/skills/. Record the source
     and licence in docs/adr/0003-website.md (25 lines or fewer).
   - If one can't be installed (for example, blocked by the network), say so in the report and
     continue with the other.
   - Read each skill fully and follow it.
3. Awwwards bar:
   - Read Awwwards' evaluation criteria on awwwards.com. If it's unreachable, use the known
     weights: Design 40%, Usability 30%, Creativity 20%, Content 10%.
   - Study what typically earns Site of the Day: a strong concept, confident typography,
     purposeful motion, scroll storytelling, micro-interactions, a distinctive personality,
     polish down to hover states, and fast and accessible delivery.
   - Learn patterns, never copy any site's design or assets.
4. Write docs/design/brief.md (1 page) before coding:
   - the concept;
   - the audience (Aminobots support team + hackathon judges);
   - personality in 3 words;
   - palette, type scale and fonts;
   - motion principles;
   - a section-by-section storyboard;
   - a self-score checklist mapped to the four Awwwards criteria.

## C. Concept: "The Triage Desk"
The site should have personality, not bland SaaS defaults. Starting direction (refine it in the
brief):
- A busy Telugu–English WhatsApp group pours onto a sorting desk.
- Noise fades away and real requests lift out.
- Each request gets a bold **rubber stamp**: ACT / ASK APPROVAL / HAND OFF / REFUSE, plus its
  rule number.
- The visual language should be warm and Hyderabad-flavoured: chat bubbles, ink stamps, paper
  textures, and confident display type paired with Noto Sans Telugu for the Telugu lines.
- The tone is a little playful but trustworthy. It's still a safety tool.

## D. Pages and sections (one long-scroll site plus the demo app)
5. **Hero:** a striking opening; the problem in one line and the promise in one. Chat bubbles
   stream in on load.
6. **"Watch it work"**, a scroll-driven story that SHOWS what the system does. Each stage is
   pinned while scrolling and built from REAL precomputed pipeline data (site/data), never
   faked:
   1. the noisy chat arrives;
   2. noise dims and the request messages glow;
   3. "the model describes": annotation cards appear (intent, gloss, evidence IDs, the
      "alaage" link drawn as a line to the earlier message);
   4. "code decides": an identity card flips to show the roster lookup and the reason;
   5. the 10 rules light up one by one, and the most cautious matching rule stamps the request;
   6. the simulated log line types itself out, labelled "simulated".

   Then run scenario 2 the same way, ending with REFUSE (R2) and a security-alert card.
7. **How it works:** the architecture diagram (copy docs/architecture.drawio.svg in), "the model
   describes, code decides" in 3 lines, and an interactive rules table rendered from
   site/data/policy.json (hovering a rule highlights where it fired in the demo).
8. **Live demo dashboard:**
   - choose a precomputed chat;
   - a request table (gloss, sender + state badge, grade stamp, rule ID with the rule text on
     hover);
   - click a row to open the step-by-step drawer:
     1. the chat with evidence highlighted;
     2. the extraction;
     3. identity + reason;
     4. all-rules check with the decider highlighted;
     5. the route + simulated log record;
     6. a trace link if one exists.
   - Approve/Reject buttons on seek_approval rows write to a client-side log in sessionStorage,
     with a stamp animation and a visible "simulated" label.
9. **Try your own:**
   - paste or upload a .txt; an optional key field ("used once, never stored");
   - a characterful progress state, because runs take 1–4 min;
   - UNPROCESSED shown clearly, never as "no requests";
   - if the API is down, show the start command.
10. **Results:** animated counters and charts from results.json: hard gates, grade confusion
    matrix, approval load, latency, notional cost, and honest limitations (dev-only eval, no
    baseline).
11. **Team:** placeholders, plus a GitHub link.
12. **Footer on every view:** "Simulation only — no action is executed. Synthetic data only."

## E. Tech and motion
13. Static HTML/CSS/vanilla JS served by FastAPI.
    - Libraries via CDN, pinned to exact versions at least 2 weeks old: GSAP + ScrollTrigger
      (free licence, verify it) and Lenis (MIT) for smooth scroll. Tailwind is optional. No
      build step.
    - Motion must be purposeful: scroll-triggered reveals, pinned storytelling, stamp impacts,
      magnetic or hover micro-interactions, and a custom cursor only if it helps.
    - Respect prefers-reduced-motion: show the same content with static transitions.
14. Usability is 30% of the score:
    - keyboard accessible, visible focus, WCAG AA contrast;
    - semantic HTML and alt text;
    - works at 375 px, 768 px and 1440 px;
    - light and dark themes.
    - Run Lighthouse (free CLI via npx) and aim for Performance ≥ 85 and Accessibility ≥ 95.
      Report the scores.

## F. Backend (unchanged from the plan)
15. `uv run python -m triage.serve` runs one FastAPI process on 127.0.0.1:8000. It mounts site/
    at / and the API under /api; CORS comes from config (localhost only).
    - GET /api/health.
    - POST /api/triage takes chat text and an optional visitor key, runs in a worker thread with
      the 300 s timeout, and returns the full result with per-stage data.
    - A visitor key is used for that request only: never stored, logged, cached under the key,
      or sent to Langfuse. Add a test for this.
    - Without a visitor key, the server key is capped at demo_server_key_rpd (10/day).
16. scripts/build_site_data.py runs the real pipeline from cache (0 new LLM requests) on 4–5 dev
    chats that together show:
    - a scenario-1-like slot change, including the "alaage" follow-up;
    - a scenario-2-like payout change from an unknown number;
    - an AMBIGUOUS sender;
    - a cancellation;
    - an injection attempt.

    It also exports site/data/policy.json and results.json.
17. Tests:
    - TestClient tests with a mocked pipeline (no network);
    - the visitor-key test;
    - a check that every site/data/*.json loads and matches the result schema.

## G. Review loop and finish
18. Start the server and take Chromium screenshots of every section at 1440 px and 375 px.
    Score the site against your brief's Awwwards checklist (each criterion out of 10, with one
    honest sentence each). Fix the weakest two things, then repeat once. Save the final
    screenshots to docs/screenshots/ and the scores in docs/design/review.md.
19. Run Try-your-own once live on a short dev chat (1 request, or a cache hit).
20. README: a "Run the demo" section with clone, uv sync and serve, the .env note, and 2–3
    screenshots.
21. All checks green; commit; push phase-06-website; open a PR. Six-part report with:
    - the before/after eval table;
    - Lighthouse scores and the self-review scores;
    - skills used and their sources;
    - LLM requests used.

    Then stop. I tag v0.3 myself.

---

## Plan (Claude Code)

PR #6 merged as `13a16d40a5400435f55e0d007a9152762212aa0f`. LLM budget: 5 (Try your own only);
everything else from cache.

**Part A:** `ground.py` adds `time_unspecified` only for open slot changes (a model-set flag is
left alone: code never strips caution). Tests, SPEC v2.6, `run_eval` dev from cache with
`--max-requests 0` → `eval/results/v0.1.1-dev/`.

**B–C:** load frontend-design and ui-ux-pro-max (both installed at user level, so nothing to
install); check the Awwwards criteria page; write `docs/design/brief.md` and ADR 0003 (CDN libs,
licences, skill sources).

**D–E:** one `site/index.html` + `site/app.css` + `site/app.js`, GSAP + ScrollTrigger + Lenis
pinned from cdnjs/jsdelivr, no build step. Every story beat reads `site/data/*.json`.

**F:** `triage/serve.py` (FastAPI app + uvicorn) with `/api/health` and `/api/triage`; visitor key
passed straight to the LLM client, bypassing the cache; daily cap for the server key.
`scripts/build_site_data.py` (cache only). Tests with TestClient + mocked pipeline.

**G:** Playwright/Chromium screenshots at 1440 and 375, self-score, fix the two weakest, repeat
once; Lighthouse via npx; 1 live Try-your-own request; README; PR.
