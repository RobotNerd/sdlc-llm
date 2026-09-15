---
id: TASK-046
title: "implement-task: wrap-up should commit and push its own pr/status bookkeeping"
type: bug
status: todo
epic: EPIC-001
created: 2026-09-14
branch: task-046-implement-task-wrap-up-should-commit-and-push-its-own-pr-status-bookkeeping
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-046: implement-task: wrap-up should commit and push its own pr/status bookkeeping

## Description

`implement-task`'s `wrap-up` subcommand (TASK-024) opens the PR (`gh pr create`), then records
`pr:` + `status: in-review` on the task file and runs `sync` to regenerate `BOARD.md`/the epic —
but it never commits or pushes that resulting change itself. It's left as uncommitted local drift
on the task branch, so the just-opened PR's diff doesn't include its own bookkeeping unless a
human or the LLM operator notices `git status` afterward and does a manual follow-up commit+push.

This isn't hypothetical: it happened for real on both TASK-025's PR (#35) and TASK-026's PR (#36)
— `wrap-up` reported success both times, but `git status` immediately after showed the task file,
`BOARD.md`, and `EPIC-001-mvp.md` all uncommitted, requiring a manual
`git add -A && git commit && git push` before either PR's diff actually reflected
`status: in-review`. `finish-merge` (the phase-4 counterpart) already gets this right — it takes a
`bookkeeping_commit_message` and commits+pushes its own post-merge changes as part of the same
invocation. `wrap-up` should do the analogous thing for its own post-PR-creation changes.

## Acceptance criteria

- [ ] `wrap-up` commits and pushes the `pr:`/`status: in-review` frontmatter update and the
      resulting `sync`-regenerated board/epic changes as part of its own single invocation — no
      separate manual follow-up commit is needed after a successful `wrap-up` call.
- [ ] The commit message for this follow-up commit is supplied by the caller in `wrap-up`'s
      answers JSON (a new key, e.g. `bookkeeping_commit_message`), consistent with how
      `finish-merge` already takes one for its own analogous post-merge commit — content-authoring
      stays with `SKILL.md`/the LLM, not hardcoded in the script.
- [ ] The follow-up push reuses `decide_push_args` (the same guardrail-respecting push-mode
      decision already used for the main push) — still only ever pushes the task's own branch,
      never `default_branch`, and still only uses `--force-with-lease` when warranted.
- [ ] `wrap-up`'s behavior is unchanged if there's nothing to commit after recording `pr:`/`status`
      (e.g. `sync` made no board/epic changes) — don't fail or push an empty commit.
- [ ] `SKILL.md`'s wrap-up step documents the new answer key; no prose anywhere still describes a
      separate manual "record PR, set status in-review" bookkeeping step as necessary after
      `wrap-up` succeeds.
- [ ] Tests cover: after a successful `wrap-up` run, the working tree is clean (nothing left
      uncommitted), and the pushed branch's remote history actually contains the `pr:`/
      `status: in-review` update (not just the local file).

## Testing strategy

1. Live dry run (same throwaway-branch/PR approach TASK-024's own Worklog used): run `wrap-up`
   end to end against a scratch task and a real throwaway PR; confirm `git status` is clean
   immediately afterward, and that the remote branch's history (not just the local working tree)
   contains a commit with the `pr:`/`status: in-review` update. Close the throwaway PR without
   merging and clean up afterward, per the established convention.
2. Confirm `sync check` stays clean after the follow-up commit.
3. Confirm no follow-up commit is attempted (and `wrap-up` doesn't fail) when there's nothing to
   commit after the frontmatter/sync step.
4. Re-read `SKILL.md`'s wrap-up section and confirm it no longer implies a separate manual
   bookkeeping commit is needed.

## Worklog

_(empty — appended during implementation)_

## Notes

- Found and manually worked around during TASK-025 and TASK-026 (see their own Worklogs for the
  exact `git status` output that surfaced it) — this task formalizes the fix in
  `implement-task/scaffold.py` itself so no future `wrap-up` call silently leaves the same gap.
- Placed at the top of TODO per explicit instruction — it affects every future `implement-task`
  invocation, so it's worth fixing before continuing further down the backlog.
