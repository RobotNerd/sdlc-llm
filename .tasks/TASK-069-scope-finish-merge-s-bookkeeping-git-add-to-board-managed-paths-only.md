---
id: TASK-069
title: "Scope finish-merge's bookkeeping git add to board-managed paths only"
type: bug
status: todo
epic: null
created: 2026-09-18
branch: task-069-scope-finish-merge-s-bookkeeping-git-add-to-board-managed-paths-only
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-069: Scope finish-merge's bookkeeping git add to board-managed paths only

## Description

Found for real during TASK-043's phase 4: `cmd_finish_merge` in
`.claude/skills/implement-task/scaffold.py` (line ~771) runs `git add -- .tasks` unconditionally
before its bookkeeping commit — a blanket add of the *whole directory*, not just the paths that
commit is supposed to own (`BOARD.md`, `EPIC-*.md`, `.tasks/archive/**`, the merged task's own
`status`/`merge_commit`/`pr` fields). An unrelated untracked file that happened to be sitting in
`.tasks/` (a freshly `add-task`-created task file, in this case) got swept into that commit and
pushed straight to `default_branch` — bypassing the small review-PR every other new task file
normally gets, and bypassing the guardrail hook entirely, since `finish-merge`'s `git push` runs as
a subprocess *inside* the script, not as a Bash command the `PreToolUse` hook ever sees.

`cmd_wrap_up` has the identical pattern at line ~650 for its own bookkeeping commit (recording
`pr:`/`status: in-review`) — lower risk since that one lands on the task's own branch behind a
normal PR, not directly on `default_branch`, but the same scope leak and worth fixing for
consistency while touching this.

Fix both call sites so the bookkeeping `git add` only ever stages what that commit is documented to
own. A plausible approach: `git add -u -- .tasks` (stages modifications/deletions to
*already-tracked* paths only — never a new untracked file) plus an explicit `git add` of the
specific new path(s) each function already knows about by construction (the archived task file's
new path in `cmd_finish_merge`, if `archive_done` moved it). Confirm this doesn't regress the
existing "commit the sync-regenerated board/epic/task changes" behavior every current test for
`wrap-up`/`finish-merge` already exercises.

## Acceptance criteria

- [ ] `cmd_finish_merge`'s bookkeeping commit never stages a file outside `BOARD.md`/`EPIC-*.md`/
      `.tasks/archive/**`/the merged task's own frontmatter fields, even when an unrelated
      untracked file is sitting in `.tasks/` at the time it runs.
- [ ] `cmd_wrap_up`'s bookkeeping commit has the same guarantee.
- [ ] Every existing `wrap-up`/`finish-merge` test in `tests/test_implement_task_scaffold.py` still
      passes — the fix must not stop staging what these commits are actually supposed to.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Regression test: before calling `finish-merge`, drop a stray untracked file in `.tasks/`
   (mimicking an in-flight `add-task` run), then assert the resulting bookkeeping commit does not
   include it and it remains untracked afterward.
2. Same regression test shape for `wrap-up`.
3. Full existing `wrap-up`/`finish-merge` test suite — confirm no regression in what does get
   committed (board/epic regeneration, archived task file, `pr:`/`status:`/`merge_commit:` fields).
4. `pytest` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- No epic — this is a general `implement-task` correctness fix, not specific to batch mode or
  `EPIC-003`'s scope.
- Real incident, not hypothetical: see TASK-068's own history (it landed in
  `chore(TASK-043): phase 4 -- record merge, archive, unblock downstream`,
  commit `f0219d4`, instead of its own small review PR).
