---
id: TASK-078
title: "implement-task-v2: detect and resume an interrupted batch by step name"
type: feature
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-078-v2-resume
pr: null
merge_commit: null
blocked_by: [TASK-077]
blocks: [TASK-081]
---

# TASK-078: implement-task-v2: detect and resume an interrupted batch by step name

## Description

Implement **detect interrupted batch**, and the resume exception in **ensure clean repo**:

- A dirty tree is allowed only when a batch state exists and the checked-out branch is its
  active task branch. On that branch, update `main` with
  `git fetch <remote> <default_branch>:<default_branch>`.
- State plus a user argument → ASK: resume or discard.
- Resuming reports the batch, active task, `step` and `interrupt`. Then apply the human's
  resolution:
  - resume at `step`, with the answer applied and the counter reset
  - skip the task: force-delete its branch and mark it `skipped`
  - discard the batch: confirm, then delete the branch and the state
- Re-entering `merge changes` first checks whether `main` already has the task's squash commit.

## Acceptance criteria

- [ ] A session lost in the middle of a step, with uncommitted work, resumes on the next invocation at the recorded `step`, with no work lost.
- [ ] A paused batch resumes after the human's answer, and that interrupt's counter resets.
- [ ] State plus an argument always gets the resume-or-discard ASK. Discarding asks for confirmation before deleting the branch.
- [ ] Skip leaves the task `todo` on `main` and continues with the next task.
- [ ] A resume after the squash commit but before the push doesn't merge twice.
- [ ] A dirty tree on any other branch, or with no batch state, still stops.
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. Manual, in a scratch repo: `init-project --target <tmp>`, a local bare repo as `origin`, a few dummy `todo` tasks, and `.claude/skills/implement-task-v2/` copied in: start a 2-task batch, then end the session during `implement task` with uncommitted edits. A new session resumes at `implement task` and finishes the batch.
2. Manual: pause via `needs_clarification`, then resume with an answer, then skip, then discard (reset the scratch repo in between).
3. Manual: stop right after the squash commit in `merge changes` (before the push). The resume pushes once, and `git log` shows a single squash commit.
4. Manual: invoke with an argument while a state exists, and confirm the ASK.
5. `.venv/bin/pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

_(empty — appended during implementation)_

## Notes

- The step names replace v1's `phase1`..`phase4`, as the spec requires.
