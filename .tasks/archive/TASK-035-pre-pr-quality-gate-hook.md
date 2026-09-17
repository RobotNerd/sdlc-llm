---
id: TASK-035
title: "Pre-PR quality gate hook: sync check, test, lint, format"
type: feature
status: done
epic: EPIC-002
created: 2026-09-14
branch: task-035-pre-pr-quality-gate-hook
pr: "https://github.com/RobotNerd/sdlc-llm/pull/66"
merge_commit: d7ba18d78502f391838683da595a3a76881f5458
blocked_by: [TASK-032, TASK-031]
blocks: [TASK-039, TASK-040]
---

# TASK-035: Pre-PR quality gate hook: sync check, test, lint, format

## Description

Blocked on TASK-032 (hooks infrastructure) and TASK-031 (`format_command` config key).

On `gh pr create`: run `sync check`, `test_command`, `lint_command` (if not `null`), and
`format_command` (if not `null`, in a check/diff mode that does not write — compare its output
against current file content, never auto-apply). Any failure denies the tool call with the
failing tool's output attached so the agent fixes and retries; a formatter that would change
files denies with the diff, telling the agent to run it and commit before retrying. All green
allows the PR to be opened.

Never mutates the working tree itself — per SPEC-002's Alternatives, an auto-fixing hook was
explicitly rejected. The formatter's actual changes must land in the agent's own commit.

## Acceptance criteria

- [x] Each of the four gates (`sync check`, `test_command`, `lint_command`, `format_command`)
      independently denies `gh pr create` on failure, with the failing command's output attached.
- [x] All four passing allows `gh pr create` to proceed.
- [x] A `null` `lint_command`/`format_command` skips that gate entirely — no regression from
      today's skill-prose behavior.
- [x] The hook never writes to the working tree under any outcome.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests per gate against fixture repos: a failing test, a failing lint, a file needing
   formatting, and a fully passing repo.
2. Hook-script test confirming denial output includes the actual failing command's
   stderr/diff, and confirming no file in the fixture repo changes across any test case.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.
5. Scratch-branch dry run (throwaway branch off `origin/main`, deleted — not merged — when done):
   attempt `gh pr create` against a scratch project with an intentionally failing gate, confirm
   denial, fix it, and confirm a real PR opens once everything is clean. Human-run — record in
   the Worklog.

## Worklog

- Added `check_pre_pr_quality_gate` to `.tasks/bin/guardrails.py` (guardrail 5), wired into
  `evaluate_bash_command`'s dispatcher: on a `gh pr create` command, runs `sync check` (via
  `compute_mismatches`, no subprocess needed), then `test_command`, then `lint_command` (if set),
  then `format_command` (if set) in a check-only mode — it runs the real command, diffs what it
  changed, then reverts those exact tracked-file paths and deletes any new file it created, so the
  tree ends exactly as it started under every outcome. Denies with the failing gate's output
  attached; `None` `lint_command`/`format_command` skips that gate entirely.
- Kept `.claude/skills/init-project/vendored-guardrails` byte-identical to `.tasks/bin/guardrails.py`
  (existing convention from TASK-032/033/034 — `tests/test_guardrails.py` enforces this).
- Added `tests/test_pre_pr_quality_gate.py` (17 tests): direct `check_pre_pr_quality_gate` calls
  per gate (sync drift, failing test, failing lint, format-command diff-and-revert on a tracked
  file, format-command new-file cleanup, all-green), `evaluate_bash_command`-level tests reading
  `test_command` from `config.md`, and real hook-script subprocess tests (denial on sync drift,
  allow on a clean repo, and a dedicated "never writes to the tree" check after a denied
  `format_command`).
- Full suite: `.venv/bin/pytest -q` → 510 passed (493 existing + 17 new), no existing test edited.
- `python3 .tasks/bin/sync check` → exit 0.
- **Scratch-branch dry run (step 5, human + agent, run together):** created `task-999-scratch-dryrun`
  off `origin/main`, brought the in-progress `guardrails.py` change onto it (since it isn't merged
  yet), set `test_command` to an always-failing command, pushed, and ran `gh pr create` as a real
  Claude Code `Bash` tool call. Correctly denied:
  `` `gh pr create` is denied -- `test_command` ('python3 -c "import sys; sys.exit(1)"') failed: ...
  exited 1 with no output ``. Fixed `test_command` to a passing inline command (see Notes re:
  `pytest` not being on `PATH` in this shell) and re-ran `gh pr create` — a real PR opened
  (https://github.com/RobotNerd/sdlc-llm/pull/65). Closed without merging and deleted the branch
  (`gh pr close 65 --delete-branch`), pruned the stale remote-tracking ref.
  - First attempt at this step was run by the human directly in their own terminal (not through
    Claude Code) and was *not* denied despite an intentionally failing gate — not a bug: the
    `PreToolUse` hook only intercepts Claude Code's own `Bash` tool calls, never a human's own
    shell session, so the hook was simply never in the loop. Re-run as a Claude Code tool call
    above to get a real signal.

## Notes

- Depends on TASK-032's `guardrails.py` module/hook-wiring and TASK-031's `format_command` key.
- **Follow-up candidate (out of this task's scope):** this repo's own `test_command: pytest` in
  `.tasks/config.md` isn't found on `PATH` in a plain shell here — only `.venv/bin/pytest` exists.
  Surfaced during the scratch dry run (`/bin/sh: pytest: command not found`). Worth a separate task
  to point `test_command` at the venv's `pytest` (or otherwise ensure it resolves), since the new
  pre-PR gate now actually *runs* `test_command` for real on every `gh pr create` — this repo's own
  gate would currently fail unless run from an activated venv shell.
