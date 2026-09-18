---
id: TASK-065
title: Fix test_command so it resolves outside an activated venv shell
type: bug
status: done
epic: EPIC-002
created: 2026-09-17
branch: task-065-fix-test-command-so-it-resolves-outside-an-activated-venv-shell
pr: "https://github.com/RobotNerd/sdlc-llm/pull/68"
merge_commit: 85040e67d0fd84f834ea4cce37f129b6c29034e2
blocked_by: []
blocks: []
---

# TASK-065: Fix test_command so it resolves outside an activated venv shell

## Description

`.tasks/config.md`'s `test_command: pytest` isn't found on `PATH` in a plain, non-activated shell
in this repo — only `.venv/bin/pytest` exists (this repo's own dev dependency, per
`CLAUDE.md`/`pyproject.toml`; there is no global `pytest` install). This was invisible before
TASK-035, since `test_command` was previously only ever run by a human (or an agent) working from
an already-activated shell. TASK-035's pre-PR quality gate hook now runs `test_command` for real,
via `subprocess.run(command, shell=True, ...)`, on every `gh pr create` — including when Claude
Code's own `Bash` tool invokes it, which does not have the venv activated. Surfaced during
TASK-035's scratch dry run: `` `gh pr create` is denied -- `test_command` ('pytest') failed:
`/bin/sh: pytest: command not found` ``, even though the suite genuinely passes.

Fix: point `test_command` at the venv's `pytest` explicitly — `.venv/bin/pytest`, a path relative
to the repo root, which is how `test_command` is always invoked (`cwd` is set to the repo root in
every caller: `guardrails.py`'s pre-PR gate, and anywhere else `test_command` is read from
`.tasks/config.md`).

## Acceptance criteria

- [x] `.tasks/config.md`'s `test_command` resolves and runs the real suite successfully from a
      plain shell with no venv activated (no `pytest: command not found`).
- [x] The pre-PR quality gate hook (TASK-035) no longer fails `gh pr create` due to `test_command`
      not being found, when run as a Claude Code `Bash` tool call (which doesn't activate the venv).
- [x] `python3 .tasks/bin/sync check` passes (config.md isn't part of any generated region, so this
      should be a no-op for `sync`, but confirm nothing else broke).

## Testing strategy

1. In a plain shell with the venv *not* activated, run the exact value that will be in
   `test_command` (e.g. `.venv/bin/pytest -q` from the repo root) and confirm it runs the real
   suite and exits `0`, rather than `command not found`.
2. `python3 .tasks/bin/sync check` → exit 0.
3. Re-run TASK-035-style scratch verification: as a real Claude Code `Bash` tool call (not the
   human's own terminal — see TASK-035's Worklog for why that distinction matters), attempt
   `gh pr create` on a clean, throwaway branch and confirm the `test_command` gate no longer
   errors with `command not found` (it may still legitimately fail for other reasons, e.g. a real
   test failure — that's out of scope here, only the `PATH` resolution is being fixed).

## Worklog

- Changed `.tasks/config.md`'s `test_command` from `pytest` to `.venv/bin/pytest` — a one-line fix.
- `.venv/bin/pytest -q` run directly (bare `pytest` confirmed absent from `PATH` first) → 510
  passed.
- `python3 .tasks/bin/sync check` → exit 0.
- Scratch-branch dry run: created `task-999-scratch-dryrun-065` off `origin/main` (which already
  has TASK-035's pre-PR gate merged), applied this task's `test_command` fix, pushed, and ran
  `gh pr create` as a real Claude Code `Bash` tool call — the gate ran the real suite via
  `.venv/bin/pytest` and passed; a real PR opened
  (https://github.com/RobotNerd/sdlc-llm/pull/67). Closed without merging, deleted the branch,
  pruned the stale remote-tracking ref.

## Notes

- Follow-up from TASK-035 (`.tasks/archive/TASK-035-pre-pr-quality-gate-hook.md`'s Notes) — see
  that task's Worklog for the exact failure text this fixes.
- If this repo's dev environment ever changes (e.g. a different venv path, or `pytest` installed
  globally), `test_command` should be revisited then; this fix is specific to today's `.venv/`
  layout, not a general "always use a venv" policy for other projects this toolkit is vendored
  into (`test_command` is a per-project config value, not something `sync`/the skills hard-code).
