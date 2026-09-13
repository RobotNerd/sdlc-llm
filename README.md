# sdlc-llm

A personalized workflow for solo, LLM-driven software development — **"kanban in markdown"**.
Work items live as plain markdown files in `.tasks/`, an LLM (Claude Code) drives them through a
four-phase lifecycle, and a small stdlib-only Python script, `sync`, keeps every generated view of
that data consistent.

This repo builds itself with its own workflow: `.tasks/` holds the spec and tasks for the v1
toolkit, and the resulting toolkit now manages that same directory (see `TASK-019` — the first
real `sync` run on this repo was a no-op, since the hand-written board/epic regions it replaced
already matched byte-for-byte what `sync` produces).

## The model

| Artifact | Role |
|---|---|
| `.tasks/specs/SPEC-*.md` | the "why" — problem, alternatives considered, non-goals |
| `.tasks/EPIC-*.md` | a grouping container; `status` is **derived by `sync`** from its children |
| `.tasks/TASK-*.md` | one unit of work — one branch, one PR, one sitting. No sub-tasks |
| `.tasks/BOARD.md` | the board view — mostly generated; only the TODO priority order is hand-kept |
| `.tasks/config.md` | per-project settings (git remote, test command, merge strategy, …) |

The rule everything follows from: **frontmatter is the source of truth; everything else is a
rendering of it.** A task's `status` lives only in that task's own file; `BOARD.md` and each
epic's roll-up only ever *display* it. Text between `<!-- BEGIN:name -->` / `<!-- END:name -->`
markers is owned by `sync` — never hand-edited.

`.tasks/specs/SPEC-001-llm-sdlc-workflow.md` is the authoritative design doc for all of this —
data model, the seven epic-status derivation rules, `sync`'s full contract, and the five skills
below.

## `sync`

`.tasks/bin/sync` (single-file Python 3, standard library only) regenerates every generated
region, derives epic status, allocates IDs (`sync next-id <spec|epic|task>`), reconciles
`blocked_by`/`blocks`, and archives `done`/`wont-do` tasks to `.tasks/archive/`. It's idempotent —
running it twice produces no diff. `sync check` is the read-only form used in CI and before
opening a PR.

```
python3 .tasks/bin/sync          # regenerate everything, write changes
python3 .tasks/bin/sync check    # read-only: exit 0 if nothing would change
python3 .tasks/bin/sync next-id task
python3 .tasks/bin/sync archive
```

Its test suite needs `pytest` (the only dev dependency, declared in `pyproject.toml`):

```
pip install -e '.[dev]'
pytest
```

## Skills

Five Claude Code skills drive the workflow end to end (still to be built — TASK-014 through
TASK-018; until then, follow SPEC-001's `implement-task` phases by hand, per `CLAUDE.md` and
`.tmp/workflow-plan.md`):

- **`init-project`** — scaffold `.tasks/` in a new repo. (Named `init-project`, not `init`, so it
  doesn't collide with a generic `init` skill.)
- **`add-task`** — interview a request into real acceptance criteria, allocate an ID, place it in
  TODO.
- **`implement-task`** — the four-phase loop (start → implement + test → wrap up → observed
  merge), each phase ending in a stop for human input. The skill never merges — a human reviews
  and squash-merges every PR.
- **`refine-backlog`** — a periodic pass: reprioritize, recompute blocked status, flag stale or
  underspecified tasks.
- **`plan-feature`** — spec → epics → vertical-slice tasks.

## Status

See `.tasks/BOARD.md` for current progress.
