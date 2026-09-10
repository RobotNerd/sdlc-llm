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

The execution skill. Four phases from SPEC-001 §`implement-task`, each ending in a STOP: Start (branch, status, restate plan for approval), Implement+test (code, tests, human-run steps recorded in Worklog, no scope creep), Wrap up (docs, commit, push, PR, status → in-review), Merge (separate go-ahead, CI-green gated). Resumable from repo state; explicit bail-out path.

## Acceptance criteria

- [ ] Skill is a numbered checklist; a STOP marker separates each of the four phases and the model halts there for human input.
- [ ] Phase 1 picks the top unblocked TODO task, announces any blocked tasks it skipped, branches from latest `default_branch`, sets `status: in-progress`, runs `sync`, then restates the plan + acceptance criteria for approval before any code.
- [ ] Phase 2 runs `test_command` and `lint_command`, walks the Testing strategy, and presents non-automatable steps for the human to run — recording results in the task's Worklog, never skipping silently. States the 'do not fix unrelated things' rule.
- [ ] Phase 3 updates `docs_paths`, makes a conventional commit referencing the task ID, pushes, opens the PR from the template with acceptance criteria as a checklist, records `pr:`, sets `status: in-review`, runs `sync`, and STOPS — no merge.
- [ ] Phase 4 is a separate invocation gated on green CI; on merge it records `merge_commit:`, sets `status: done`, runs `sync` (which archives).
- [ ] Resumability: on invocation the skill infers the current phase from branch existence, frontmatter `status`/`pr`, and `gh pr view`, and continues from there.
- [ ] Bail-out: if the task proves wrong or underspecified mid-flight, it writes findings into the task file, sets `status` back to `todo`/`blocked`, runs `sync`, and surfaces to the user.

## Testing strategy

1. Dry-run each phase against a scratch task on a scratch branch; confirm the STOP halts and the frontmatter/board transitions happen via `sync`.
2. Start phase 1, abandon, re-invoke; confirm it resumes at phase 2 rather than restarting.
3. Trigger the bail-out mid-phase-2; confirm status reverts and findings land in the file.
4. Confirm `sync check` is clean after each phase.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-002 (task-file body shape) and TASK-012 (`sync check` between phases).
- The largest skill — keep each phase independently testable.
