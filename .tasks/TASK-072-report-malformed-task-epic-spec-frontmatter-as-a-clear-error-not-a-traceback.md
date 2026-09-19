---
id: TASK-072
title: Report malformed task/epic/spec frontmatter as a clear error, not a traceback
type: bug
status: in-progress
epic: EPIC-003
created: 2026-09-19
branch: task-072-report-malformed-task-epic-spec-frontmatter-as-a-clear-error-not-a-traceback
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-072: Report malformed task/epic/spec frontmatter as a clear error, not a traceback

## Description

Found during TASK-069: a `.tasks/TASK-*.md` (or `EPIC-*`/`SPEC-*`) file that doesn't start with a
valid `---` frontmatter block -- a half-written file, a stray scratch file with a task-shaped
name -- makes `sync`'s `discover()` raise `FrontmatterError`. The exception's *message* is already
good (it names the offending file and the problem), but nothing catches it, so every entry point
that reaches `discover()` dies with a full Python traceback that buries that message:

- `.tasks/bin/sync` itself: a bare `sync` and `sync check` (`main()` only wraps `next-id` in a
  `try`).
- The skill scripts that call `sync_mod.discover(...)` directly: `implement-task/scaffold.py`
  (`resume-state`, `start`, `wrap-up`, `finish-merge`, `bail-out`), `add-task/scaffold.py`,
  `refine-backlog/scaffold.py`, and `implement-task/batch_select.py`.

Reproduced by dropping `.tasks/TASK-999-stray.md` containing just `no frontmatter` and running
`sync check` / `implement-task/scaffold.py resume-state`: both print a traceback ending in
`FrontmatterError: .../TASK-999-stray.md: file does not start with a '---' frontmatter block`.

Catch `FrontmatterError` at each of those entry points and report its message as a one-line
error with a non-zero exit code, in each tool's existing `<tool>: <message>` stderr style. `sync
check` in particular is the CI/read-only verifier -- a malformed file should be a clean "check
failed" result, not a crash. A malformed file must still fail loudly (non-zero) -- this is about
the *presentation* of the error, never about tolerating or skipping the bad file.

## Acceptance criteria

- [x] A bare `sync`, `sync check`, and `sync archive` run against a `.tasks/` containing a
      malformed `TASK-*.md` (no frontmatter block, unclosed block, or missing `id`) print a
      one-line message naming the offending file and problem to stderr, exit non-zero, and emit no
      traceback.
- [x] The same holds for each skill script that calls `discover()` directly (`implement-task`'s
      `scaffold.py` subcommands and `batch_select.py`, `add-task`, `refine-backlog`).
- [x] The malformed file is still never silently skipped -- every one of those entry points still
      exits non-zero (`sync check` in particular can't report clean while a bad file exists).
- [x] No behavior change for a well-formed `.tasks/` (existing tests unchanged and green).
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Regression tests for `sync`: a scratch `.tasks/` with a stray `TASK-999-stray.md` (no
   frontmatter) -- run bare `sync`, `sync check`, and `sync archive` as subprocesses; assert exit
   code non-zero, the file's name in stderr, and no `Traceback` in stderr/stdout. Repeat for the
   other malformed shapes (unclosed `---` block, missing `id`).
2. The same shape for each skill script's `discover()` call sites -- at least one representative
   subcommand per script (`implement-task` `resume-state`, `batch_select.py select`, `add-task`
   `list-open-epics`, `refine-backlog`'s entry point) -- asserting the same three things.
3. Confirm existing tests for a well-formed `.tasks/` are unchanged.
4. `pytest` -- full suite green.
5. `python3 .tasks/bin/sync check` -> exit 0 (on the real, well-formed repo).

## Worklog

- Tests first: new `tests/test_malformed_frontmatter.py` (25 cases) -- 24 failed with the traceback for the expected reason (the 25th, a well-formed `.tasks/`, passed as the no-regression control). One test fix on the way: `start` with `task_id: null` exits at "no unblocked TODO task" before ever reaching `discover()`, so that case now passes an explicit id.
- `sync`: `main()` now wraps a new `_main()` and turns `FrontmatterError` into one `sync: <message>` stderr line -- exit 1 for `check` (same code as "drift found"), 2 for bare `sync`/`archive`/other. `.claude/skills/init-project/vendored-sync` updated byte-identically.
- Skill scripts: a local `discover_or_exit(sync_mod, tasks_root)` in each of `implement-task/scaffold.py` (5 call sites), `add-task/scaffold.py` (2), `refine-backlog/scaffold.py` (3), `implement-task/batch_select.py` (1) raises `SystemExit("<tool>: <message>")` (exit 1, each script's existing fatal-error style). No shared module -- they stay standalone/vendorable. `guardrails.py` left alone: its `discover()` call already swallows exceptions, correct for a fail-open hook.
- Covered shapes: no frontmatter, unclosed `---` block, missing `id`; malformed TASK in `.tasks/`, EPIC, SPEC, and an archived TASK; all 12 script entry points (every subcommand that reaches `discover()`, incl. `wrap-up`/`finish-merge`/`bail-out`). Each asserts non-zero exit, offending filename on stderr, exactly one stderr line, no `Traceback`.
- Exit-code decision (per human): keep each tool's own convention rather than unify.
- Full suite 714 passed; `sync check` exit 0.

## Notes

- Presentation-only fix: do not make `discover()` skip or tolerate bad files -- a malformed
  artifact must keep failing every entry point, just readably.
- Each skill's `scaffold.py` stays stdlib-only and standalone (they're vendored into other
  projects), so a small per-script `except` is preferable to a new shared module.
- Related but out of scope: TASK-069 (why a stray file mattered at all).
