---
id: TASK-012
title: "sync check: compute, diff, exit non-zero, write nothing"
type: feature
status: todo
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

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-007, TASK-008, TASK-009 (it diffs everything they render).
- Blocks TASK-013, TASK-016, TASK-019, TASK-020.
