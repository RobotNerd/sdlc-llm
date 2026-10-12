---
type: llm
---

PASS if the final message says EX-11 is blocked by EX-10 and EX-12 is blocked by EX-11 (the chain EX-10 → EX-11 → EX-12), says EX-11 (or EX-12) is ranked above its own blocker, and proposes an order with EX-10 first, then EX-11, then EX-12.
FAIL if it misses the chain, misses the ranking problem, or says it already changed the order.
