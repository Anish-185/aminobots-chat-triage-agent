# Eval `v0.1-dev` (dev)

| Metric | Value |
|---|---|
| precision | 0.83 |
| recall | 0.95 |
| f1 | 0.89 |
| tp | 35 |
| n_pred | 42 |
| n_gold | 37 |
| intent_accuracy | 1.00 |
| evidence_jaccard | 0.81 |
| attribution_accuracy | 1.00 |
| identity_state_accuracy | 1.00 |
| unconfirmed_sender_recall | 1.00 |
| grade_accuracy | 0.89 |
| over_autonomy_rate | 0.00 |
| over_autonomy_high_risk | 0 |
| extras_graded_act | 0 |
| rule_citation_accuracy | 0.80 |
| evidence_validity | 1.00 |
| approval_load | 0.44 |
| latency_p50_s | 62.68 |
| latency_p95_s | 239.45 |
| tokens_in | 41453 |
| tokens_out | 111481 |
| notional_cost_usd | 0.06 |
| requests | 11 |

**Hard gates**

| Gate | Result |
|---|---|
| high_risk_over_autonomy_is_0 | True |
| unconfirmed_sender_recall_is_1 | True |
| evidence_validity_is_100 | True |
| mandated_scenarios_pass_exactly | (None, None) |

**Targets**

| Target | Value | Needed | Met |
|---|---|---|---|
| f1 | 0.89 | 0.85 | True |
| grade_accuracy | 0.89 | 0.85 | True |
| rule_citation_accuracy | 0.80 | 0.9 | False |

**Grade confusion (rows gold, cols predicted)**

| gold \ pred | act | seek_approval | hand_off | refuse |
|---|---|---|---|---|
| act | 5 | 4 | 0 | 0 |
| seek_approval | 0 | 14 | 0 | 0 |
| hand_off | 0 | 0 | 9 | 0 |
| refuse | 0 | 0 | 0 | 3 |

**Slice: script**

| Value | n | Recall | Grade acc |
|---|---|---|---|
| english | 5 | 0.60 | 1.00 |
| romanised_telugu | 29 | 1.00 | 0.86 |
| telugu_script | 3 | 1.00 | 1.00 |

**Slice: intent**

| Value | n | Recall | Grade acc |
|---|---|---|---|
| complaint | 2 | 1.00 | 1.00 |
| delivery_slot_change | 13 | 0.92 | 0.67 |
| invoice_request | 4 | 1.00 | 1.00 |
| order_change | 3 | 1.00 | 1.00 |
| other | 2 | 1.00 | 1.00 |
| payout_details_change | 2 | 1.00 | 1.00 |
| refund_request | 5 | 0.80 | 1.00 |
| status_query | 6 | 1.00 | 1.00 |

**Slice: gold_state**

| Value | n | Recall | Grade acc |
|---|---|---|---|
| AMBIGUOUS | 3 | 1.00 | 1.00 |
| CONFIRMED | 30 | 0.93 | 0.86 |
| UNCONFIRMED | 4 | 1.00 | 1.00 |

Unprocessed: none · pending: none
