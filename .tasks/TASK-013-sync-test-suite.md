---
id: TASK-013
title: "End-to-end idempotency and derivation-matrix test suite"
type: chore
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-013-sync-test-suite
pr: null
merge_commit: null
blocked_by: [TASK-009, TASK-011, TASK-012]
blocks: [TASK-019]
---

# TASK-013: End-to-end idempotency and derivation-matrix test suite

## Description

The cross-cutting suite over a fixture `.tasks/` repo: proves `sync` is idempotent (run twice → no diff), the seven derivation rules each fire on the right input, TODO order survives a `sync`, and archiving behaves. This is SPEC-001's core correctness property (§'Idempotency', §'Success criteria').

## Acceptance criteria

- [ ] A `tests/fixtures/` mini-repo exercises every status, an epic with mixed children, a blocked chain, and an archivable task.
- [ ] Idempotency test: `sync` then `sync` again → second run yields an empty diff (asserted via `sync check` exit 0).
- [ ] Derivation matrix: one parametrised case per row of the §derivation worked-cases table, asserting status + rule number.
- [ ] TODO-preservation test: scrambled order in, same order out, annotations refreshed.
- [ ] Archive test: `done`/`wont-do` move, `next-id` still accounts for them.
- [ ] Suite runs under the repo's `test_command` and is wired for CI (TASK-020).

## Testing strategy

1. Run the suite; all pass.
2. Introduce a deliberate bug in `derive_epic_status` (swap rules 5 and 6) and confirm the matrix catches it.
3. Break idempotency (make a renderer emit a timestamp) and confirm the idempotency test fails.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-009, TASK-011, TASK-012.
- Blocks TASK-019 (dogfitch migration relies on this suite being green).
- This is the real proof of the derivation rules — the live repo only exercises rule 2.
