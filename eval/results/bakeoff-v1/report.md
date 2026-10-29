# Bake-off v1 (Phase 4, strict mode, prompt extract/v1, dev chats only)

| Model | Chats | P | R | F1 | Intent acc | Evidence J | Slot datetime | Schema failures | Latency p50 / p95 (s) | Tokens in / out | Notional $ | Requests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `nvidia/nemotron-3.5-super-vl:free` | 10/10 | 0.88 | 0.81 | 0.84 | 1.00 | 0.92 | 0/6 | 0 | 65.01 / 212.54 | 19928 / 58071 | 0.0320 | 9 |
| `google/gemma-4-31b-it:free` | 0/10 | – | – | – | – | – | 0/0 | 0 | – / – | 0 / 0 | 0.0000 | 1 |

TP / predicted / gold: nvidia/nemotron-3.5-super-vl:free 21/24/26
Stopped early: google/gemma-4-31b-it:free: RateLimited at d01: rate limited (429): google/gemma-4-31b-it:free is temporarily rate-limited upstream (Google AI Studio shared pool)
Failed chats: nvidia/nemotron-3.5-super-vl:free: ['d10', 'd13']

Request counts exclude cached responses (cost 0). Billed cost is $0 (free models);
notional $ uses the paid variant's list price (config/pricing.yaml).
