---
id: TASK-031
title: Add optional format_command config key; run it in implement-task before opening a PR
type: feature
status: done
epic: EPIC-001
created: 2026-09-14
branch: task-031-format-command-config-key
pr: "https://github.com/RobotNerd/sdlc-llm/pull/51"
merge_commit: 743b8016a0223e808d928f56586526ebc5daf949
blocked_by: [TASK-024]
blocks: [TASK-035]
---

# TASK-031: Add optional format_command config key; run it in implement-task before opening a PR

## Description

`config.md` already has a `test_command`/`lint_command` pair, with `lint_command: null` meaning
"no linter configured, skills skip the step." There's no equivalent for an auto-formatter. Add one
the same way — `format_command`, defaulting to `null`, asked in `init-project`'s interview — and
have `implement-task` run it before a PR goes up, so the diff a human reviews is already formatted.

**No Claude Code hooks infrastructure** (no `settings.json` anywhere in this toolkit today) — that
mechanism is explicitly deferred to a separate future epic. This task's only enforcement is
`implement-task`'s own checklist/script, run as a normal step — same posture as
`test_command`/`lint_command` today.

`implement-task`'s phase 3 is pure prose right now; TASK-024 (blocking this task) rewrites it into
a stdlib script per the established script-extraction pattern (TASK-021/022). The formatter step
belongs *in that script*, not as new prose bolted onto a phase this repo already knows is about to
be rewritten.

### Where it runs

After rebase, before push — not literally between push and `gh pr create`. The point (formatting
reflects the final diff, including anything touched during rebase-conflict resolution) is
satisfied by running it post-rebase; running it *after* push would force a second push before
`gh pr create` for no benefit. So phase 3 becomes: update docs → commit → rebase → **run
`format_command`** → push → `gh pr create`. If the formatter changes anything, amend the existing
commit (`git add -A && git commit --amend --no-edit`) rather than adding a second commit — keeps
the one-task-one-commit-family shape the rest of the phase already assumes. A non-zero exit from
`format_command` itself (a real tool error, not just "it reformatted files") is a STOP, surfaced to
the human — same treatment `lint_command` gets today.

### Config key

Mirrors `lint_command` exactly:

- `init-project/templates/config.md` (and this repo's own `.tasks/config.md`): add
  `format_command: null` to the frontmatter, plus a "Key notes" entry: `null` means
  `implement-task` skips the formatting step; set it once a formatter is chosen (e.g.
  `ruff format .`, `black .`, `prettier --write .`).
- `scaffold.py`'s `REQUIRED_KEYS` gains `format_command` — asked in the interview, not fixed like
  `allow_auto_merge`/`ignored_paths`.
- `init-project/SKILL.md`'s interview table gains a `format_command` row ("How is code formatting
  run, if at all?" / default `null`) — the table's existing general instruction (look at the repo
  for hints, always ASK to confirm) already covers detection guidance; no per-field special-casing
  needed.

### implement-task integration

Since TASK-024's script doesn't exist yet, describe the *behavior* here (run `format_command`
after rebase, before push; amend on changes; STOP on a real failure) and wire it into whatever
script structure TASK-024 actually produces by the time this task is picked up, rather than
inventing function/file names for a script that doesn't exist yet. `SKILL.md`'s phase 3 prose gets
one added line pointing at that step, matching the shape TASK-024 leaves for every other
mechanical step.

### Explicitly out of scope

Descoped this session, deferred to a future epic: any Claude Code `PreToolUse`/`settings.json`
hook enforcing this independent of the skill. Also out of scope: running the formatter during
phase 2 — only the pre-PR point, per the decision made when this task was created.

## Acceptance criteria

- [x] `init-project/templates/config.md` (and this repo's `.tasks/config.md`) include
      `format_command: null`, documented under "Key notes" like `lint_command`.
- [x] `scaffold.py`'s `REQUIRED_KEYS` includes `format_command`; a freshly scaffolded project is
      asked for it and writes whatever value (including `null`) is given.
- [x] `init-project/SKILL.md`'s interview table has a `format_command` row.
- [x] `implement-task` runs `format_command` (when not `null`) after the phase-3 rebase and before
      the push; if it modifies files, those changes are folded into the existing commit
      (`--amend`), not a separate one.
- [x] A `format_command` that exits non-zero itself (not just reformatting files) is a STOP,
      surfaced to the human, same treatment as `lint_command`'s failures.
- [x] `format_command: null` (the default) makes `implement-task` skip the step entirely — no
      behavior change for a project that hasn't configured one, including this repo today.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Extend `tests/test_init_project_scaffold.py`: a scaffolded `config.md` contains
   `format_command: null` by default, and a non-null answer round-trips correctly.
2. Whatever test module TASK-024 established for the implement-task script gains cases for the
   formatter step: `format_command: null` → step is skipped; a formatter that rewrites a file →
   change is amended into the existing commit, not a new one; a formatter that exits non-zero →
   surfaced as a stop condition, nothing pushed.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.
5. Scratch-branch dry run (throwaway branch off `origin/main`, deleted — not merged — when done):
   set a real formatter (e.g. any tool that visibly rewrites a file) as `format_command` on a
   scratch project, run `implement-task` phase 3 through to PR creation, confirm the pushed branch
   is already formatted and only one commit carries the change. Human-run — record in the
   Worklog.

## Worklog

- Added `format_command` (default `null`) to `init-project/templates/config.md`,
  `init-project/scaffold.py`'s `REQUIRED_KEYS`, `init-project/SKILL.md`'s interview table, and
  this repo's own `.tasks/config.md` — mirrors `lint_command` exactly, positioned right after it.
- `implement-task/scaffold.py`'s `cmd_wrap_up` now runs `format_command` (via `shell=True`) after
  the phase-3 rebase (and any `ignored_paths` stash-pop) and before the push. A non-zero exit is
  treated exactly like a rebase conflict: printed and returned as a STOP, nothing pushed, nothing
  amended. On success, any files the formatter changed (excluding `ignored_paths`, consistent with
  how the rest of phase 3 already protects them) are folded into the existing commit via
  `git commit --amend --no-edit`. Whether an amend happened is now OR'd into the existing
  force-push decision alongside `rebase_before_pr`, since an amend rewrites history the same way a
  rebase does — matters if `wrap-up` is resumed after a formatter failure on a branch that was
  already pushed by an earlier run.
- Updated `implement-task/SKILL.md` phase 3 with the new step and its STOP condition.
- Tests: added `format_command` to the 6 test fixtures that hardcode a full `init-project`
  answers dict. Added 3 new `implement-task` integration tests against the real scratch-repo
  fixture: a formatter that rewrites a file gets amended into the existing commit (not a separate
  one, confirmed on both the local and pushed remote branch); `format_command: null` is a true
  no-op; a formatter that exits non-zero stops everything after it (nothing pushed, no PR, task
  stays `in-progress`).
- Testing strategy step 5 (a human-run scratch-branch dry run against a real repo with real `gh`)
  was explicitly skipped per the human's decision — the 3 automated integration tests above
  exercise the same logic (rewrite-and-amend, no-op, and failure-stops-everything) against a real
  git repo, just with a fake `gh` and a synthetic formatter rather than a real PR.
- Full suite: `pytest` 420 passed; `python3 .tasks/bin/sync check` exits 0.

## Notes

- Blocked on TASK-024 so the formatter step is written directly into its new script rather than
  into prose that TASK-024 is about to replace.
- A future epic will cover Claude Code hooks (`settings.json`) as a stronger, skill-independent
  enforcement mechanism — deliberately not part of this task.
