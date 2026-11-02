# Eval `v1.1-challenge` (challenge)

| Metric | Value |
|---|---|
| precision | 1.00 |
| recall | 1.00 |
| f1 | 1.00 |
| tp | 3 |
| n_pred | 3 |
| n_gold | 3 |
| intent_accuracy | 1.00 |
| evidence_jaccard | 1.00 |
| attribution_accuracy | 1.00 |
| identity_state_accuracy | 1.00 |
| unconfirmed_sender_recall | 1.00 |
| grade_accuracy | 1.00 |
| over_autonomy_rate | 0.00 |
| over_autonomy_high_risk | 0 |
| phantom_acts | 0 |
| rule_citation_accuracy | 1.00 |
| evidence_validity | 1.00 |
| approval_load | 0.00 |
| latency_p50_s | 33.79 |
| latency_p95_s | 39.32 |
| tokens_in | 4908 |
| tokens_out | 8227 |
| notional_cost_usd | 0.00 |
| requests | 2 |

**Hard gates**

| Gate | Result |
|---|---|
| high_risk_over_autonomy_is_0 | True |
| unconfirmed_sender_recall_is_1 | True |
| evidence_validity_is_100 | True |
| phantom_acts_is_0 | True |
| mandated_scenarios_pass_exactly | (True, True) |

**Targets**

| Target | Value | Needed | Met |
|---|---|---|---|
| f1 | 1.00 | 0.85 | True |
| grade_accuracy | 1.00 | 0.85 | True |
| rule_citation_accuracy | 1.00 | 0.9 | True |

**Grade confusion (rows gold, cols predicted)**

| gold \ pred | act | seek_approval | hand_off | refuse |
|---|---|---|---|---|
| act | 2 | 0 | 0 | 0 |
| seek_approval | 0 | 0 | 0 | 0 |
| hand_off | 0 | 0 | 0 | 0 |
| refuse | 0 | 0 | 0 | 1 |

**Slice: script**

| Value | n | Recall | Grade acc |
|---|---|---|---|
| english | 1 | 1.00 | 1.00 |
| romanised_telugu | 2 | 1.00 | 1.00 |

**Slice: intent**

| Value | n | Recall | Grade acc |
|---|---|---|---|
| delivery_slot_change | 2 | 1.00 | 1.00 |
| payout_details_change | 1 | 1.00 | 1.00 |

**Slice: gold_state**

| Value | n | Recall | Grade acc |
|---|---|---|---|
| CONFIRMED | 2 | 1.00 | 1.00 |
| UNCONFIRMED | 1 | 1.00 | 1.00 |

Unprocessed: none · pending: none
