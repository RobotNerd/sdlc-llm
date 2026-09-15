---
id: TASK-046
title: "implement-task: wrap-up should commit and push its own pr/status bookkeeping"
type: bug
status: in-review
epic: EPIC-001
created: 2026-09-14
branch: task-046-implement-task-wrap-up-should-commit-and-push-its-own-pr-status-bookkeeping
pr: "https://github.com/RobotNerd/sdlc-llm/pull/39"
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

- [x] `wrap-up` commits and pushes the `pr:`/`status: in-review` frontmatter update and the
      resulting `sync`-regenerated board/epic changes as part of its own single invocation — no
      separate manual follow-up commit is needed after a successful `wrap-up` call.
- [x] The commit message for this follow-up commit is supplied by the caller in `wrap-up`'s
      answers JSON (a new key, e.g. `bookkeeping_commit_message`), consistent with how
      `finish-merge` already takes one for its own analogous post-merge commit — content-authoring
      stays with `SKILL.md`/the LLM, not hardcoded in the script.
- [x] The follow-up push reuses `decide_push_args` (the same guardrail-respecting push-mode
      decision already used for the main push) — still only ever pushes the task's own branch,
      never `default_branch`, and still only uses `--force-with-lease` when warranted.
- [x] `wrap-up`'s behavior is unchanged if there's nothing to commit after recording `pr:`/`status`
      (e.g. `sync` made no board/epic changes) — don't fail or push an empty commit.
- [x] `SKILL.md`'s wrap-up step documents the new answer key; no prose anywhere still describes a
      separate manual "record PR, set status in-review" bookkeeping step as necessary after
      `wrap-up` succeeds.
- [x] Tests cover: after a successful `wrap-up` run, the working tree is clean (nothing left
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

- 2026-09-14: Fixed `cmd_wrap_up` in `.claude/skills/implement-task/scaffold.py`: after the
  existing `sync` call (which sets `pr:`/`status: in-review` and regenerates the board/epic),
  added `git add -- .tasks`, a `git diff --cached --quiet` check (skip cleanly if nothing staged —
  AC's "don't push an empty commit"), and if there is something staged: commit with the new
  `bookkeeping_commit_message` answer key, then push via `decide_push_args` (same function the
  main push already uses, `force=False` — a brand-new commit on top of an already-pushed branch
  never needs `--force-with-lease`). Mirrors `finish-merge`'s existing, already-correct pattern
  for its own analogous post-merge bookkeeping commit.
- Updated `SKILL.md`'s wrap-up step (step 3) to document `bookkeeping_commit_message` as a new
  required answer key and describe the commit+push as part of the single `wrap-up` call — no
  prose anywhere still implies a manual follow-up commit is needed.
- **Tests** (`tests/test_implement_task_scaffold.py`, 2 new): added a `fake_gh` fixture — a small
  executable stub on its own `PATH` directory answering `pr create` with a fixed deterministic URL
  and `pr checks` with "no checks configured" (exit 1, which `wrap-up` must not fail on regardless)
  — letting `wrap-up`'s actual git mechanics be exercised as a real subprocess against the
  existing bare-origin/work-clone fixture, without needing real network/`gh` auth in the test
  suite. `test_wrap_up_commits_and_pushes_its_own_bookkeeping` confirms `dirty_files() == []`
  after a run and that `git show origin/<branch>:<task file>` (the *remote* history, fetched
  fresh, not just the local working tree) contains both `status: in-review` and the fake PR URL.
  `test_wrap_up_skips_empty_bookkeeping_commit` pre-sets the task file to exactly what `wrap-up`
  would end up writing, then confirms no extra (empty) bookkeeping commit appears — caught and
  fixed a bug in the test itself along the way: the manual pre-set initially left the URL
  unquoted, but `render_frontmatter` always quotes a scalar containing a colon (a URL always has
  one), so re-rendering the *same* logical value still produced a byte-diff until the fixture's
  manual text matched that canonical quoted form.
- **Live dry run against real `gh`** (testing strategy step 1, same isolated-scratch-clone
  approach used for TASK-024's own dry run): cloned the real repo fresh, added a throwaway
  `TASK-901`, ran `start` then `wrap-up` with the fixed script — `git status` came back clean
  immediately after, `git log` showed the bookkeeping commit made automatically, and the real
  opened PR (#38) already reflected `status: in-review` in its own diff before any manual
  intervention. Closed the PR without merging and deleted the remote branch + scratch clone
  afterward — no residue.
- Full suite: `pytest` 318 passed (316 prior + 2 new); `python3 .tasks/bin/sync check` exit 0 on
  the real repo throughout, including after the live dry run's cleanup.

## Notes

- Found and manually worked around during TASK-025 and TASK-026 (see their own Worklogs for the
  exact `git status` output that surfaced it) — this task formalizes the fix in
  `implement-task/scaffold.py` itself so no future `wrap-up` call silently leaves the same gap.
- Placed at the top of TODO per explicit instruction — it affects every future `implement-task`
  invocation, so it's worth fixing before continuing further down the backlog.
