# Design self-review (Phase 6)

Scored against the checklist in [`brief.md`](brief.md), each criterion out of 10, on Chromium
screenshots at 1440 × 900 and 375 × 812 (light and dark). Awwwards weights: Design 40%, Usability
30%, Creativity 20%, Content 10% (awwwards.com/about-evaluation, checked 2026-10-29). Final
screenshots: [`docs/screenshots/`](../screenshots/).

## Round 1

| Criterion | Score | One honest sentence |
|---|---|---|
| Design | 6 | The desk/docket/stamp idea holds at 1440, but with `display=optional` the display face often failed to load and the hero fell back to a shouting Arial, and the mobile chat tabs stacked into five rows. |
| Usability | 7 | Lighthouse accessibility was 100 and keyboard paths worked, but the rules table forced a 6 px horizontal scroll at 375 px and the stacked tabs pushed the table off the first screen. |
| Creativity | 8 | The stamp landing on the real decider, the referent line from the follow-up to m011 and the rules lighting up from real data carry the concept. |
| Content | 8 | Everything shown is real pipeline output and the limits are stated, though some copy is engineer-flavoured. |
| **Weighted** | **6.9** | |

**Fixed (weakest two, Design and Usability):** fonts back to `display=swap` with width-matched
`size-adjust` fallbacks (no font loss, CLS kept low); hero top-aligned (desktop CLS 0.27 → 0.01);
rules table padding and scroll container (no page overflow); chat tabs become a scrolling strip
below 640 px.

## Round 2

| Criterion | Score | One honest sentence |
|---|---|---|
| Design | 8 | Type now carries the page in both themes; the dark docket loses some of the yellow-paper cue. |
| Usability | 7 | Desktop is strong, but on phones the six step captions came first and the content they describe sat far below them. |
| Creativity | 8 | Unchanged: one signature moment (the stamp), used sparingly. |
| Content | 7 | The drawer showed raw identifiers such as `time_unspecified` with no plain explanation. |
| **Weighted** | **7.6** | |

**Fixed (weakest two, Usability and Content):** below 861 px each step caption now sits directly
above the chat, docket, roster card, rules or log line it describes; uncertainty flags are shown in
plain words with the identifier in brackets, on dockets and in the drawer. Also: the hero stamp
moved off the message text and the Team heading alignment was fixed.

## Final

| Criterion | Score | One honest sentence |
|---|---|---|
| Design | 8 | A distinct, coherent look (blotter green, duplicate-book yellow, office-stamp violet, condensed display type) with polished hover and focus states. |
| Usability | 8 | Keyboard reachable throughout (tabs with arrow keys, `<dialog>` drawer, focusable rules), AA contrast in both themes, no horizontal scroll at 375/768/1440, reduced motion respected. |
| Creativity | 8 | The scroll story shows "the model describes, code decides" instead of saying it. |
| Content | 8 | Real data only, plain sentences, limitations (dev-only, no baseline, slot gap, missed target) on the page. |
| **Weighted** | **8.0** | |

**Lighthouse 12.8.2** (localhost, system Chromium): mobile Performance 88, Accessibility 100,
Best practices 100; desktop 100 / 100 / 100.

**Still weak:** the dark docket is less characterful than the light one; the architecture diagram
is the docs SVG (white sheet, small type) rather than a drawing made for the page; the mobile nav is
a scrolling strip rather than a menu.
