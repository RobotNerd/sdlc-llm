---
id: TASK-003
title: "Add .github/pull_request_template.md mirroring acceptance criteria"
type: chore
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-003-pr-template
pr: https://github.com/RobotNerd/sdlc-llm/pull/15
merge_commit: c26452b610b7a71e3a844a32fe79107d5438c689
blocked_by: []
blocks: [TASK-014]
---

# TASK-003: Add .github/pull_request_template.md mirroring acceptance criteria

## Description

A PR template whose body mirrors the task acceptance-criteria checklist plus a filled-in test-results section, so `implement-task` phase 3 can open a PR that maps 1:1 to the task file (SPEC-001 §`init`, §`implement-task`).

## Acceptance criteria

- [x] `.github/pull_request_template.md` has an 'Acceptance criteria' checklist section and a 'Test results' section (including a slot for non-automatable steps run by the human).
- [x] Template references the task ID and PR-title convention from SPEC-001 §Guardrails (conventional commit + `TASK-NNN`).
- [x] Structure lines up with the task-file body so phase 3 is a copy-with-checkboxes, not a rewrite.

## Testing strategy

1. Open a throwaway draft PR in a scratch branch using the template; confirm GitHub picks it up and the sections render.
2. Walk a sample task file and confirm each acceptance-criteria line has a home in the template.

## Worklog

- 2026-09-12: Ran `pytest` (209 passed) and `python3 .tasks/bin/sync check` (exit 0) before and
  after adding the template — expected no-ops since this change touches no Python.
- Testing strategy step 2: walked `.tasks/archive/TASK-013-sync-test-suite.md` against the
  template by hand. Every body section had a home: `## Task` <- id/title, `## Description` <-
  Description, `## Acceptance criteria` <- its checklist verbatim, `## Test results` <- its
  Testing strategy's 3 numbered steps with results filled in, `## Notes` <- reviewer-facing
  deviations. TASK-013's own Notes (blocked_by/blocks graph metadata) and its Worklog's
  blow-by-blow decisions don't get a literal 1:1 slot — that's intentional: the task file's
  Worklog stays the source of truth for implementation history, `## Notes` in the PR is for
  what a reviewer needs, not a full transcript.
- Testing strategy step 1 (throwaway draft PR): deferred to this task's own phase-3 `gh pr
  create` rather than a separate scratch branch — opening TASK-003's real PR against the
  template it adds exercises the same thing without the throwaway. Confirmed via `gh pr view
  --json body`: https://github.com/RobotNerd/sdlc-llm/pull/15 rendered every section (Task,
  Description, Acceptance criteria with checked boxes, Test results, Notes) intact.
- Phase 4 (record merge, archive, board/epic updates) was first committed straight to
  `main`, per the documented guardrail carve-out. `git push origin main` was blocked by an
  environment safety classifier, so — on the human's instruction — those changes were moved
  onto a branch (`task-003-record-merge`) and opened as PR #16 instead, one-off for this task.
  The documented carve-out itself is unchanged and applies again from TASK-019 onward.

## Notes

- No dependencies.
- Blocks TASK-014 (`init` writes this file).
