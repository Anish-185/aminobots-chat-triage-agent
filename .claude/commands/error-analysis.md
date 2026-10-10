---
description: Run a dev-only failure analysis and propose at most two prompt fixes
argument-hint: [focus area, optional]
---

Run a failure analysis on the **dev split only**, with this optional focus: $ARGUMENTS

1. Run `/run-eval dev pipeline wip-analysis-before`.
2. Classify every dev failure into exactly one bucket: `missed_request`,
   `hallucinated_request`, `wrong_intent`, `split_merge_error`, `reference_error`, `wrong_flag`,
   `entity_error`, `identity_error`, `policy_disagreement`, `gold_error`.
3. Write `eval/analysis/<date>-dev-failures.md` with counts per bucket, per script slice and per
   template, plus 2 representative cases per bucket.
4. Propose at most two prompt changes, aimed at the prompt-caused buckets with the highest
   safety or volume impact, each tied to the cases it should fix. List code-caused issues
   separately.

Stop and wait for my approval. Never use test or challenge data.
