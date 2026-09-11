---
id: TASK-016
title: "implement-task skill: four phases, STOP markers, resumable, bail-out"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-016-skill-implement-task
pr: null
merge_commit: null
blocked_by: [TASK-002, TASK-012]
blocks: []
---

# TASK-016: implement-task skill: four phases, STOP markers, resumable, bail-out

## Description

The execution skill, and the workflow's git driver. Four phases from SPEC-001 §`implement-task`, each ending in a STOP: Start (fetch + branch, status, restate plan for approval), Implement+test (code, tests, human-run steps recorded in Worklog, no scope creep), Wrap up (docs, commit, rebase, push, `gh pr create`, status → in-review), Merge (observe the human's squash-merge, never perform it). It runs `git` and `gh` directly. Resumable from repo state; explicit bail-out path.

## Acceptance criteria

- [ ] Skill is a numbered checklist; a STOP marker separates each of the four phases and the model halts there for human input.
- [ ] Phase 1: refuses to start if the working tree is dirty; picks the top unblocked TODO task; announces any blocked tasks it skipped; runs `git fetch <remote>` and branches from `<remote>/<default_branch>` (name `<branch_prefix><NNN>-<slug>`); sets `status: in-progress` and `branch:`; runs `sync`; then restates the plan + acceptance criteria for approval before any code.
- [ ] Phase 2 runs `test_command` and `lint_command`, walks the Testing strategy, and presents non-automatable steps for the human to run — recording results in the task's Worklog, never skipping silently. States the 'do not fix unrelated things' rule and checks `git diff --name-only` against the task's scope before committing.
- [ ] Phase 3 updates `docs_paths`; makes a conventional commit referencing the task ID; if `rebase_before_pr`, runs `git fetch <remote>` and rebases onto `<remote>/<default_branch>`, stopping and surfacing on conflict; pushes (`--force-with-lease` when the rebase rewrote pushed history); runs `gh pr create` with acceptance criteria as a checklist and test results filled in; records the returned URL in `pr:`; sets `status: in-review`; runs `sync`; and STOPS. Never merges.
- [ ] Phase 4 is observe-only: the human squash-merges on GitHub. The skill polls `gh pr view --json state,mergeCommit`; once `MERGED` it records `merge_commit:`, sets `status: done`, runs `sync`, then (if `delete_branch_after_merge`) deletes the branch locally and on `<remote>` and fast-forwards local `<default_branch>`. The skill never runs `gh pr merge`.
- [ ] `gh pr checks` is used to report CI status to the human in phases 3 and 4; a red or pending check is surfaced, not worked around.
- [ ] If `gh` is not installed or not authenticated, the skill stops at the point it is needed and prints the exact `git`/`gh` commands for the human to run, then resumes from `gh pr view` on the next invocation.
- [ ] Resumability: on invocation the skill infers the current phase from working-tree cleanliness, branch existence (`git branch --list`), frontmatter `status`/`pr`, and `gh pr view --json state,mergeCommit`, and continues from there.
- [ ] Bail-out: if the task proves wrong or underspecified mid-flight, it writes findings into the task file, sets `status` back to `todo`/`blocked`, runs `sync`, and surfaces to the user.

## Testing strategy

1. Dry-run each phase against a scratch task on a scratch branch of this repo; confirm the STOP halts, the branch is cut from fresh `origin/main`, and the frontmatter/board transitions happen via `sync`.
2. Phase 3 dry-run: make a trivial change, confirm the rebase + `--force-with-lease` push + `gh pr create` sequence runs and `pr:` is recorded from `gh` output. Close the PR without merging afterward.
3. Simulate the human merge (squash-merge the scratch PR), re-invoke; confirm phase 4 detects `MERGED`, records `merge_commit`, and cleans up the branch.
4. Start phase 1, abandon, re-invoke; confirm it resumes at phase 2 rather than restarting.
5. Temporarily rename `gh` on `PATH`; confirm the skill degrades to printing commands rather than erroring.
6. Trigger the bail-out mid-phase-2; confirm status reverts and findings land in the file.
7. Confirm `sync check` is clean after each phase.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-002 (task-file body shape) and TASK-012 (`sync check` between phases).
- The largest skill — keep each phase independently testable.
- Git guardrails it must enforce (SPEC-001 §Guardrails): never push to `default_branch`, never
  `gh pr merge`, `--force-with-lease` only on the task's own branch after a rebase.
- The human reviews every PR on GitHub and does the squash & merge. This skill's phase 4 is purely
  observational.
- If the phase-3/4 git sequence proves unreliable as checklist prose, extract it into a small
  helper (functions in `.tasks/bin/sync`, or a sibling `.tasks/bin/gitflow`) — deferred for now.
