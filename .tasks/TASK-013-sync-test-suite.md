---
id: TASK-013
title: "End-to-end idempotency and derivation-matrix test suite"
type: chore
status: in-review
epic: EPIC-001
created: 2026-09-10
branch: task-013-sync-test-suite
pr: https://github.com/RobotNerd/sdlc-llm/pull/13
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

- 2026-09-13: AC #2 ("sync then sync again → empty diff") cannot be expressed without something
  that actually writes — the gap flagged (and deliberately deferred) in TASK-011's and TASK-012's
  Worklogs. Built it here: `apply_all` (writes every region/frontmatter `compute_mismatches` would
  otherwise only report — chaining a file's updates when more than one applies, since BOARD.md
  often needs several at once and computing each independently against stale text would let a
  later write undo an earlier one) and `run_sync` (`apply_all` + conditional archiving). Bare
  `.tasks/bin/sync` now actually writes; previously it only discovered and summarized. This is a
  bigger-than-typical change for one task, but it's the exact prerequisite this task's own AC
  demands, not unrelated scope.
- Built `tests/fixtures/mini_repo/` — a checked-in, deliberately stale fixture (wrong epic status,
  empty regions, a scrambled+incomplete TODO list, two done/wont-do tasks not yet archived, a
  two-hop blocked chain where one link is already resolved) so the first `run_sync` has real,
  meaningful work to prove, not just a no-op on an already-correct tree.
- Testing strategy step 2 (swap rules 5/6, confirm the matrix catches it): first attempt swapped
  the two branches' *code position* without swapping their *output values* — the conditions stayed
  mutually exclusive regardless of order, so nothing failed. Redid it swapping the actual `new_status`
  values; both TASK-006's own suite and this task's end-to-end matrix caught it immediately, on
  exactly rules 5 and 6. Worth remembering: "swap two branches" bugs need the *outputs* swapped, not
  just their order, to be a real test of branch-order sensitivity.
- Testing strategy step 3 (timestamp in a renderer): caught immediately and broadly — 13 tests
  failed, not just the idempotency test, including several already-shipped tests from TASK-005/008
  that had been implicitly relying on deterministic output. Confirms the existing suite already
  guards non-determinism from more angles than just this task's own idempotency test.
- Ran `sync check` (read-only) against this real repo throughout — stayed clean. Deliberately did
  **not** run bare `sync` (write) against the real repo: that migration is TASK-019's job
  ("dogfood... bring this repo's .tasks/ fully under the toolkit"), not this task's.
- "Wired for CI" (AC #6) is satisfied by construction (this repo's `test_command: pytest` already
  runs the whole suite) but the actual CI workflow file is TASK-020's job, not built here.

## Notes

- Blocked by TASK-009, TASK-011, TASK-012.
- Blocks TASK-019 (dogfitch migration relies on this suite being green).
- This is the real proof of the derivation rules — the live repo only exercises rule 2.
