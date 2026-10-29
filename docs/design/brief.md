# Design brief: The Triage Desk (Phase 6)

**Concept.** The dispatch desk of a Hyderabad produce supplier at the end of a long day. A partner
WhatsApp group spills onto a green desk blotter; a clerk reads every bubble, pulls the real asks
out onto yellow **duplicate-book dockets** (the carbon-copy receipt books every Indian office
keeps), checks the sender against the roster, and brings down a **violet rubber stamp**, the
colour of every office stamp pad in India. ACT, ASK APPROVAL, HAND OFF, REFUSE, and the rule number
inked beside it. Nothing leaves the desk: every docket says *simulated*.

**Audience.** Aminobots support staff, who must trust each stamp at a glance, and hackathon judges,
who have 3 minutes and need to *see* "the model describes, code decides".

**Personality:** sharp-eyed · warm · accountable.

**Palette** (all text pairs ≥ 6:1, checked; grade is always a word, never colour alone):

| Token | Light (day desk) | Dark (night desk) | Use |
|---|---|---|---|
| paper | `#FBF3D5` duplicate-book yellow | `#13221E` | page |
| card | `#FFFDF4` top sheet | `#1C2E29` | dockets, table |
| desk | `#1E4A3F` blotter green | `#0C1714` | hero + story surface |
| ink | `#1C1B2E` blue-black | `#F1E9CF` | text |
| carbon | `#2E3A8C` carbon-copy blue | `#9FB0FF` | message IDs, links |
| stamps | act `#17683F` · ask `#5A2EA6` · hand off `#8A4B00` · refuse `#B0201A` | lifted tints | grade stamps |

**Type.** Big Shoulders Display 900 (condensed, civic-signage confidence) for headlines and stamp
lettering; Atkinson Hyperlegible Next for everything read (a typeface designed for legibility suits
a safety tool); Noto Sans Telugu for Telugu-script lines. Scale: perfect fourth (1.333) from 16 px:
16 · 21 · 28 · 38 · 50 · 67 · 90, hero up to `clamp(4rem, 13vw, 11rem)`. Body measure ≤ 68ch, line
height 1.55. Uppercase only where the object is uppercase in life (stamps).

**Motion principles.** (1) Something moves only when a pipeline stage does work: bubbles arrive,
noise dims, a card appears, a stamp lands. (2) One signature moment: the **stamp impact** (drops
from 1.6×, rotates −8°, ink bleeds, desk shudders 2 px). Spend boldness there; everything else is
quiet. (3) The story is scroll-scrubbed and pinned (two pins only: scenario 1, scenario 2), on
desktop; below 768 px and under `prefers-reduced-motion` it becomes a static sequence with the same
content. (4) Responses to the user (drawer, approve/reject) animate to show what changed, ≤ 300 ms.

**Storyboard.**
1. **Hero (desk).** Left: "Thirty messages. Three real asks. One is a fraud." / "The Triage Desk
   finds each request, checks who sent it, and stamps what may happen next. It executes nothing."
   Right: real d01 bubbles stream onto the blotter; one lifts out and gets stamped.
2. **Watch it work** (pinned, d01): chat arrives → noise dims, request bubbles glow → docket cards
   with intent, gloss, evidence IDs and a drawn line from "alaage" to the earlier message → identity
   card flips to the roster lookup + reason → R1–R10 tick one by one, matches light, the most
   cautious stamps → the log line types itself, marked *simulated*.
   Then d07 the same way, ending REFUSE R2 and a security-alert docket.
3. **How it works.** Architecture diagram on a paper sheet; three lines; the rules table from
   `policy.json`; hovering a rule highlights the demo rows where it matched.
4. **The desk (demo).** Chat chooser as file tabs; request table; a side drawer (`<dialog>`) with
   six numbered steps (a real sequence); Approve/Reject stamps a client-side log.
5. **Try your own.** Paste/upload, optional key ("used once, never stored"), a clerk's progress
   note with elapsed time; UNPROCESSED is a red full-chat hand-off docket; API down → the command.
6. **Results.** Counters, hard gates as PASS stamps, a 4×4 confusion grid in ink density, approval
   load, latency, notional cost, and the limits written plainly.
7. **Team**, then the footer on every view: "Simulation only — no action is executed. Synthetic
   data only."

**Self-score checklist** (Awwwards weights; scored in `review.md`):
- *Design 40%*: one idea held throughout (desk/docket/stamp); type does the heavy lifting; no
  generic card grid; polished hover/focus states; both themes designed, not inverted.
- *Usability 30%*: keyboard path through story, table, drawer, form; visible focus; AA contrast;
  375/768/1440 layouts; reduced motion; Lighthouse Perf ≥ 85, A11y ≥ 95.
- *Creativity 20%*: stamp impact, the "alaage" thread line, rules lighting up from real data.
- *Content 10%*: real pipeline output only; plain sentences; limitations stated, not hidden.

**Rejected defaults (frontend-design review).** UI UX Pro Max proposed navy + Swiss minimal +
Outfit/Work Sans: correct for a generic SaaS, wrong for this brief, so only its accessibility,
motion and checklist rules were kept. Cream + terracotta was avoided by using duplicate-book yellow
and office-stamp violet; monospace data labels were replaced by carbon-blue IDs in the body face.
