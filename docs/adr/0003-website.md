# ADR 0003 — Website stack and design skills (2026-10-29)

**Decision:** static `site/` (HTML, CSS, vanilla JS, no build step) served with the API by one
FastAPI process (`api/main.py`, `uv run python -m triage.serve`, 127.0.0.1:8000).

**Front-end libraries (CDN, exact versions, ≥ 2 weeks old):**
- GSAP 3.15.0 + ScrollTrigger (cdnjs). Standard "No Charge" GSAP licence: free incl. commercial
  use (checked on gsap.com/licensing, 2026-10-29); restrictions only on competing no-code tools.
- Lenis 1.3.26 (jsDelivr), MIT. 1.3.27 is 14 days old, so it was not used.
- Google Fonts: Big Shoulders Display, Atkinson Hyperlegible Next, Noto Sans Telugu (SIL OFL).

**Design skills used** (already installed at user level, so nothing was installed under
`.claude/skills/`):
- `frontend-design` 1.1.1, Anthropic (github.com/anthropics/claude-plugins-official), Apache-2.0, free.
- `ui-ux-pro-max` 2.15.0, plugin `ui-ux-pro-max-skill` (github.com/nextlevelbuilder/ui-ux-pro-max-skill),
  MIT, free. Its generated design system (navy/Swiss) was rejected for this brief; its
  accessibility, motion and pre-delivery rules were applied (`docs/design/brief.md`).

**Tooling, not dependencies:** screenshots via `uv run --with playwright` driving the system
Chromium; Lighthouse via `npx lighthouse`. Neither is added to `pyproject.toml`.

**Consequences:** the API process never loads Langfuse (`llm.TRACING = False`), because its
drop-in patches the OpenAI SDK process-wide and a visitor's key must never be traced.
