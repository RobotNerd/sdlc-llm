---
id: TASK-020
title: "CI workflow running sync check on every PR"
type: chore
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-020-ci-sync-check
pr: null
merge_commit: null
blocked_by: [TASK-012]
blocks: []
---

# TASK-020: CI workflow running sync check on every PR

## Description

A GitHub Actions workflow that runs `sync check` (and the TASK-013 suite) on every PR, so a drifted board or a broken derivation cannot merge (SPEC-001 §'Success criteria': '`sync check` runs in CI and fails on drift').

## Acceptance criteria

- [ ] `.github/workflows/` job runs `sync check` on `pull_request` and fails the check on non-zero exit.
- [ ] Same job (or a sibling) runs the repo's `test_command`, including the TASK-013 suite.
- [ ] Job uses only the Python standard library — no pip install step for `sync` itself.
- [ ] A PR that hand-edits a generated region without running `sync` gets a red check with a diff in the log.
- [ ] `ci_checks` in `config.md` lists the job names so `implement-task` phase 4 can gate merge on them.

## Testing strategy

1. Open a PR that edits a `BEGIN:`/`END:` region by hand; confirm CI goes red and the log shows the offending diff.
2. Open a clean PR; confirm the check passes.
3. Confirm the job pulls no external dependencies for `sync`.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-012.
- Independent of the skills; can land as soon as `sync check` exists.
