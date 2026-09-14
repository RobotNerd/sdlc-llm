---
id: TASK-035
title: "Pre-PR quality gate hook: sync check, test, lint, format"
type: feature
status: todo
epic: EPIC-002
created: 2026-09-14
branch: task-035-pre-pr-quality-gate-hook
pr: null
merge_commit: null
blocked_by: [TASK-032, TASK-031]
blocks: []
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

- [ ] Each of the four gates (`sync check`, `test_command`, `lint_command`, `format_command`)
      independently denies `gh pr create` on failure, with the failing command's output attached.
- [ ] All four passing allows `gh pr create` to proceed.
- [ ] A `null` `lint_command`/`format_command` skips that gate entirely — no regression from
      today's skill-prose behavior.
- [ ] The hook never writes to the working tree under any outcome.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

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

_(empty — appended during implementation)_

## Notes

- Depends on TASK-032's `guardrails.py` module/hook-wiring and TASK-031's `format_command` key.
