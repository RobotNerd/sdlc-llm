---
id: TASK-012
title: "sync check: compute, diff, exit non-zero, write nothing"
type: feature
status: in-progress
epic: EPIC-001
created: 2026-09-10
branch: task-012-sync-check
pr: null
merge_commit: null
blocked_by: [TASK-007, TASK-008, TASK-009]
blocks: [TASK-013, TASK-016, TASK-019, TASK-020]
---

# TASK-012: sync check: compute, diff, exit non-zero, write nothing

## Description

A read-only `sync`: run every derivation and renderer in memory, diff the result against what is on disk, print a unified diff, and exit non-zero if anything differs — without writing. For CI (TASK-020) and for skills detecting drift (SPEC-001 §'The sync script').

## Acceptance criteria

- [ ] `sync check` writes no files under any circumstance.
- [ ] Exit 0 and no output when disk already matches; exit non-zero with a unified diff per file when it does not.
- [ ] Covers all generated regions: epic `children`, spec `epics`, board `epics` panel, and the four board columns, plus the TODO merge and epic `status` frontmatter.
- [ ] Diff output names the file and region so a human can act on it.
- [ ] Unit tests: clean repo (exit 0), a repo with one hand-broken region (exit non-zero, diff points at it).

## Testing strategy

1. Immediately after this epic's files are written, run `sync check` — must exit 0 with no output (the whole-epic bootstrap no-op check).
2. Hand-edit one character inside a generated region; confirm `sync check` exits non-zero and the diff identifies that region.
3. Confirm no file mtimes change across a `sync check` run.

## Worklog

- 2026-09-12: `python3 .tasks/bin/sync check` against this actual repo exits **0, no output** —
  every generated region, every epic status field, and the TODO section already match what `sync`
  would produce. This is the payoff of the bootstrap approach: eight tasks of hand-writing regions
  to match a tool that didn't exist yet, and the tool agrees with all of it on the first real run.
  Confirmed the other two testing-strategy steps too: a hand-broken character in `BOARD.md` is
  caught with a diff naming the exact file and region (exit 1), and no file mtimes change across a
  check run.
- Scope note: AC explicitly scopes this task to the read-only `check` path ("writes no files under
  any circumstance"). Nothing in the 20-task breakdown explicitly owns wiring bare `sync` (no args)
  to actually *write* the computed regions — but TASK-019 (dogfood) needs that to exist to migrate
  this repo off manual bookkeeping. Deliberately not building it here to keep this PR scoped to its
  own AC; `compute_mismatches()` already returns everything a write mode needs (each `Mismatch`
  carries the full expected file content), so adding one is a small follow-up, not a redesign.
  Flagging for the user rather than deciding unilaterally which task should own it.
- Also checks task `blocks` frontmatter against `reconcile_blocks` — not itemized in the AC's
  region list, but the Description says "every derivation," and skipping it would leave a real
  class of drift (blocked_by edited without updating the mirror) undetected.

## Notes

- Blocked by TASK-007, TASK-008, TASK-009 (it diffs everything they render).
- Blocks TASK-013, TASK-016, TASK-019, TASK-020.
