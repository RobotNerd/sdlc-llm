---
id: TASK-032
title: Hooks infrastructure + shared guardrails module + core git/gh guardrail hooks
type: feature
status: todo
epic: EPIC-002
created: 2026-09-14
branch: task-032-hooks-infra-core-guardrails
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-033, TASK-034, TASK-035, TASK-036, TASK-037, TASK-038]
---

# TASK-032: Hooks infrastructure + shared guardrails module + core git/gh guardrail hooks

## Description

Foundational slice for EPIC-002 (see SPEC-002). No blockers — proves the whole hooks mechanism
end to end with the guardrails that need no other in-flight task.

Introduce:
- `init-project/templates/settings.json` (new; copied to `.claude/settings.json`), registering
  `PreToolUse` hooks on `Bash`.
- A vendored hook-scripts location under `.claude/skills/init-project/` (naming to match the
  `vendored-sync` convention), copied into `.claude/hooks/` in the target project.
- `.tasks/bin/guardrails.py` — stdlib only, vendored the same way as `sync` — holding every
  guardrail as a pure function.

Three guardrails, as functions in `guardrails.py` plus their hook wiring:
1. Deny `gh pr merge` outright.
2. Deny `git push` of task work to `default_branch`. Allow only the phase-4 bookkeeping
   pattern: a push to `default_branch` whose diff touches only board-managed paths (`BOARD.md`,
   `EPIC-*.md`, a task file's `status`/`merge_commit`/`pr` fields, `.tasks/archive/**`).
3. Deny `git push --force` that isn't `--force-with-lease`, and deny `--force-with-lease` on any
   branch but the current task's own (cross-check `.tasks/config.md`'s `branch_prefix` and the
   in-progress task's `branch:`).

`scaffold.py`'s `cmd_run` gains these paths to its write set (and to `managed_files()` if that
helper already exists by the time this is implemented; otherwise the inline copy list).

This slice defines the shared-module pattern that TASK-024 (and any other script-extraction task
still open) is expected to call into for the same rules, rather than reimplementing them — see
SPEC-002's Alternatives for why.

## Acceptance criteria

- [ ] A fresh scaffold includes `.claude/settings.json` wired to hook scripts that call
      `.tasks/bin/guardrails.py`.
- [ ] Each of the three guardrails has a unit test on its pure function.
- [ ] Each has a hook-script test: feed the documented `PreToolUse` JSON shape on stdin, assert
      the `deny` decision for a violating `tool_input.command` and `allow` (or no output) for
      everything else.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests per guardrail function with crafted git/task-file states (fixture repos in
   `tmp_path`, following the existing `tests/` conventions).
2. Hook-script tests: real subprocess invocation of the hook script with representative
   `PreToolUse` stdin JSON for `Bash` (`gh pr merge`, a `git push` to `default_branch` with
   non-board changes, a bare `--force` push, a `--force-with-lease` push on the wrong branch) and
   confirm denial; confirm an ordinary allowed command passes through untouched.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.
5. Scratch-branch dry run (throwaway branch off `origin/main`, deleted — not merged — when done):
   attempt a real `gh pr merge` in a live Claude Code session against a scaffolded scratch
   project and confirm the hook refuses it end to end. Human-run — record in the Worklog.

## Worklog

_(empty — appended during implementation)_

## Notes

- This is the foundational slice for EPIC-002 — every other task in the epic depends on it.
- The shared-module decision (hooks and skill scripts both call `guardrails.py`) is documented in
  SPEC-002; keep new guardrail logic there, not duplicated into a hook script or a skill script.
