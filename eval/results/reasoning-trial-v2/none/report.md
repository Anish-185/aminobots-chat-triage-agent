# Bake-off (strict mode, prompt extract/v2, dev chats only)

| Model | Chats | P | R | F1 | Intent acc | Evidence J | Slot datetime | Schema failures | Latency p50 / p95 (s) | Tokens in / out | Notional $ | Requests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `nvidia/nemotron-3.5-super-vl:free` | 2/2 | 0.67 | 0.86 | 0.75 | 1.00 | 0.86 | 0/3 | 0 | 4.30 / 4.51 | 5509 / 1152 | 0.0014 | 2 |

TP / predicted / gold: nvidia/nemotron-3.5-super-vl:free 6/9/7

Request counts exclude cached responses (cost 0). Billed cost is $0 (free models);
notional $ uses the paid variant's list price (config/pricing.yaml).
