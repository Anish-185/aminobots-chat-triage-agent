# Bake-off (strict mode, prompt extract/v3, dev chats only)

| Model | Chats | P | R | F1 | Intent acc | Evidence J | Slot datetime | Schema failures | Latency p50 / p95 (s) | Tokens in / out | Notional $ | Requests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `google/gemma-4-31b-it:free` | 0/10 | – | – | – | – | – | 0/0 | 0 | – / – | 0 / 0 | 0.0000 | 1 |

TP / predicted / gold: 
Stopped early: google/gemma-4-31b-it:free: RateLimited at d01: rate limited (429): google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations

Request counts exclude cached responses (cost 0). Billed cost is $0 (free models);
notional $ uses the paid variant's list price (config/pricing.yaml).
