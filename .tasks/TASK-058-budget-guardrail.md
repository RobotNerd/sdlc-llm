---
id: TASK-058
title: "Budget guardrail: OpenRouter credit floor and burn-rate monitor"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-058-budget-guardrail
pr: null
merge_commit: null
blocked_by: [TASK-055]
blocks: [TASK-063]
---

# TASK-058: Budget guardrail: OpenRouter credit floor and burn-rate monitor

## Description

Blocked on TASK-055 (OpenRouter client) — this reads its `balance()` and wraps its `send()`.

Two new config keys: `openrouter_min_credits` (a floor — below this, refuse further external
calls) and `openrouter_max_cost_per_request` (a per-call ceiling from the response's own
`usage.cost`). Burn-rate detection: track the cost of the last 2 OpenRouter requests in
`.tasks/.run/openrouter-usage.json` (gitignored run state, not a tracked artifact) and flag when
the rate of consumption across those 2 requests exceeds a third configurable threshold,
`openrouter_burn_rate_threshold`.

On any breach (credit floor, per-request ceiling, or burn-rate threshold): halt the run and alert —
this is a **systemic** interrupt per TASK-042's taxonomy (every remaining task in the batch would
hit the same wall), not an isolated one.

## Acceptance criteria

- [ ] `openrouter_min_credits`, `openrouter_max_cost_per_request`, and
      `openrouter_burn_rate_threshold` exist as template-fixed config keys with documented, sane
      defaults.
- [ ] A `balance()` call reading at or below `openrouter_min_credits` halts before any further
      external call is attempted.
- [ ] A single response's `usage.cost` exceeding `openrouter_max_cost_per_request` is flagged and
      halts — even if the overall balance is still healthy.
- [ ] Burn rate is computed from exactly the last 2 requests' recorded costs, not the whole run's
      history, and a breach halts.
- [ ] Every halt in this task is routed as a systemic (halt-the-batch) interrupt, matching TASK-042.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the credit-floor check against synthetic balance figures (above, at, below the
   floor).
2. Unit tests on the per-request ceiling against synthetic `usage.cost` values.
3. Unit tests on burn-rate detection against a synthetic usage-history fixture with exactly 2 prior
   requests, confirming the threshold comparison and confirming a 3rd+ older request is correctly
   excluded from the calculation.
4. Unit test confirming a breach of any of the three checks returns/raises the systemic-halt
   signal, not the isolated one.
5. `python3 -m pytest -q` — full suite green.
6. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- `.tasks/.run/` is new run-state territory for this epic (see also TASK-060's `BATCH-<id>.json`)
  — should be `.gitignore`d, matching how the repo already excludes `__pycache__` etc., since it's
  ephemeral per-run bookkeeping, not project-owned data.
- This is explicitly analogous to EPIC-003's TASK-043 (context/token safety valve) but for external
  dollar spend instead of Anthropic context/tokens — same halt semantics, different resource.
