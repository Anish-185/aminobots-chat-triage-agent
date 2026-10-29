# Bake-off (strict mode, prompt extract/v2, dev chats only)

| Model | Chats | P | R | F1 | Intent acc | Evidence J | Slot datetime | Schema failures | Latency p50 / p95 (s) | Tokens in / out | Notional $ | Requests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `nvidia/nemotron-3.5-super-vl:free` | 2/2 | 0.86 | 0.86 | 0.86 | 1.00 | 0.94 | 0/4 | 0 | 106.62 / 132.52 | 5509 / 23986 | 0.0128 | 2 |

TP / predicted / gold: nvidia/nemotron-3.5-super-vl:free 6/7/7

Request counts exclude cached responses (cost 0). Billed cost is $0 (free models);
notional $ uses the paid variant's list price (config/pricing.yaml).
