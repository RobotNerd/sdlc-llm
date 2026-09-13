---
id: TASK-020
title: "CI workflow running sync check on every PR"
type: chore
status: in-progress
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

- [x] `.github/workflows/` job runs `sync check` on `pull_request` and fails the check on non-zero exit.
- [x] Same job (or a sibling) runs the repo's `test_command`, including the TASK-013 suite.
- [x] Job uses only the Python standard library — no pip install step for `sync` itself.
- [x] A PR that hand-edits a generated region without running `sync` gets a red check with a diff in the log.
- [x] `ci_checks` in `config.md` lists the job names so `implement-task` phase 4 can gate merge on them.

## Testing strategy

1. Open a PR that edits a `BEGIN:`/`END:` region by hand; confirm CI goes red and the log shows the offending diff.
2. Open a clean PR; confirm the check passes.
3. Confirm the job pulls no external dependencies for `sync`.

## Worklog

- 2026-09-12: `.github/workflows/ci.yml` added — two jobs, `sync-check` (checkout + setup-python
  + `python3 .tasks/bin/sync check`, no install step) and `test` (checkout + setup-python +
  `pip install -e '.[dev]'` + `pytest`), both on `pull_request` and `push` to `main` (the latter
  to also cover phase-4's direct-to-main bookkeeping commits). `config.md`'s `ci_checks` updated
  to `[sync-check, test]` to match the job names. `sync check` stayed clean throughout.
- Steps 2/3 (clean PR passes; no external deps for the `sync-check` job) can only be proven by a
  real GitHub Actions run — verifying against this task's own PR once opened, recorded below.
  Step 1 (a PR that hand-edits a region goes red with the diff in the log) needs a second,
  throwaway PR carrying a deliberate violation — same approach as TASK-003's throwaway-PR check.
- Opened this task's own PR (#18): both `sync-check` and `test` passed (7s / 12s —
  https://github.com/RobotNerd/sdlc-llm/actions/runs/34740258295). Confirms step 2. Inspected the
  `sync-check` job's log directly: its one step runs only `python3 .tasks/bin/sync check`, no
  `pip`/install anywhere in that job — confirms step 3 (AC #3).
- Step 1: pushed a throwaway branch (`task-020-throwaway-drift-check`, based on this task's
  branch so the new workflow was present) that hand-corrupted `BOARD.md`'s `epics` region
  (`999/20 done`), opened PR #19, confirmed `sync-check` failed (6s) while `test` still passed —
  https://github.com/RobotNerd/sdlc-llm/actions/runs/34740296494. The job log printed the exact
  unified diff (`-| EPIC-001 | in-progress | 999/20 done |` / `+...14/20 done |`) followed by
  `Process completed with exit code 1`. Closed PR #19 without merging and deleted its branch —
  throwaway, not part of this task's real change.

## Notes

- Blocked by TASK-012.
- Independent of the skills; can land as soon as `sync check` exists.
