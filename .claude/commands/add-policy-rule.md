---
description: Propose and add a new autonomy-policy rule safely, with tests and audit
argument-hint: <plain-English description of the rule and the case that motivates it>
---

Add a policy rule for this need: $ARGUMENTS

1. Restate the rule as one plain-English `statement` sentence and as a `when` condition over
   SPEC §9.2 features. If a needed feature doesn't exist, stop and propose the feature first.
2. Choose the next unused rule ID. Decide its position, remembering that among same-grade rules
   the lowest number wins the citation (SPEC §9.5). Explain the choice.
3. Say explicitly whether this rule can make any grade **more autonomous**. If yes, stop and ask
   me before proceeding.
4. Create `policy/policy_v{N+1}.yaml`; never edit a released version. Update
   `policy/CHANGELOG.md`, SPEC §9.4 and the rendered `docs/policy/POLICY.md`.
5. Add a scenario test proving the rule can decide, plus any worked check it affects.
6. Run the **policy-auditor** subagent, then `/run-eval dev pipeline wip-policy`. Report both.
