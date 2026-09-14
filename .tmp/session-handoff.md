# Session handoff

Written 2026-09-14, so a fresh session can resume cleanly. Skills, `guidelines.md`, and
`.tmp/workflow-plan.md` are self-documenting for the workflow mechanics — this file only holds
what isn't written down anywhere else.

## State

All five original skills (`init-project`, `add-task`, `implement-task`, `refine-backlog`,
`plan-feature`) are done. Currently working through a second pass: one script-extraction refactor
task per skill, moving each skill's deterministic steps into a stdlib Python script (TASK-021,
the `init-project` one, is done and is the reference implementation — see below). Check
`.tasks/BOARD.md` for the current TODO order and progress count; nothing is in-progress right
now, `main` is clean.

## Conventions established but not yet written into any skill or doc

- **Script-extraction shape** (applies to the remaining `add-task`/`implement-task`/
  `refine-backlog`/`plan-feature` script tasks): follow TASK-021's `scaffold.py` +
  `SKILL.md` rewrite as the template. Confirmed answers/inputs go to the script as a JSON file
  (not CLI flags) when there are several or list-valued fields. The script is stdlib-only, never
  prompts interactively, and refuses cleanly (stderr message, non-zero exit, writes nothing) on
  bad input. `SKILL.md` keeps a cheap narrative pre-check for anything the script would refuse on
  (e.g. a precondition already false) so an interview isn't wasted on a doomed run, even though
  the script independently re-verifies the same thing defensively.
- **Testing a *-script.py`**: import it in `tests/` via `SourceFileLoader` with a unique module
  name (same pattern `conftest.py` already uses for `.tasks/bin/sync`) — several skills will each
  have a similarly-named script, so a bare `import scaffold` would collide across test files.
  Prefer real subprocess + `tmp_path` integration tests over mocks for anything touching the
  filesystem or git.
- **Scratch-branch dry-run testing**: a throwaway branch off `origin/main`, deleted (never
  merged) once done. Only open a real throwaway PR on it when the task needs to prove actual
  `git`/`gh` mechanics (TASK-016's `implement-task` test did); skip opening a PR for a file-only
  dry run (TASK-018's `plan-feature` test never needed one).

## Nothing else

No open questions, no bail-outs, no unresolved design decisions right now.
