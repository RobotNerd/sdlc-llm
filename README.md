# sdlc-llm

A personalized workflow for solo, LLM-driven software development — **"kanban in markdown"**.
Work items live as plain markdown files in `.tasks/`, an LLM (Claude Code) drives them through a
four-phase lifecycle, and a small stdlib-only Python script, `sync`, keeps every generated view of
that data consistent.

This repo builds itself with its own workflow: `.tasks/` holds the specs and tasks for the
toolkit, and the resulting toolkit manages that same directory (see `TASK-019` — the first
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
data model, the seven epic-status derivation rules, `sync`'s full contract, and the skills
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

Seven Claude Code skills drive the workflow end to end (one of them repo-only — see below). Each
pairs a `SKILL.md` checklist (interviews, judgment calls, STOP markers) with a `scaffold.py`
(stdlib-only, the mechanical file/`git`/`gh`/`sync` work behind each step):

**Feeding the backlog**

```
plan-feature   → writes a SPEC, decomposes into vertical slices, creates epic(s)
add-task       → interviews you into real acceptance criteria, allocates an ID, places it in TODO
refine-backlog → periodic: reprioritize, recompute blocked status, flag stale/underspecified tasks
```

**Executing a task** — `implement-task`, four phases with a hard STOP between each:

| Phase | Does | Ends |
|---|---|---|
| 1. Start | dirty-tree check, pick top unblocked TODO task, branch, `status: in-progress`, restate plan | before any code |
| 2. Implement + test | code, unit tests, run the Testing strategy, record results in Worklog, stay in scope | after tests |
| 3. Wrap up | commit, rebase, push, `gh pr create`, `status: in-review` | PR open, not merged |
| 4. Merge — observed | a human reviews and squash-merges; the skill records the merge, archives, cleans up | done |

The skill never merges — it opens the PR and stops; phase 4 only observes the human's merge and
records it.

- **`init-project`** — scaffold `.tasks/` in a new repo, or (if already initialized) upgrade an
  existing one: refresh every portable skill plus `guidelines.md`/templates/vendored `sync`/PR
  template from a source clone, without ever touching project-owned data. Pass `--target <path>`
  to `run`/`upgrade` to scaffold or refresh a separate project by path — clone this toolkit repo
  and the target side by side, start a session in the toolkit clone, and point `--target` at the
  other one. (Named `init-project`, not `init`, so it doesn't collide with a generic `init`
  skill.) A separate `migrate-config` step additively brings an older project's `config.md` up
  to the current schema — new keys only, at a human-approved STOP, never overwriting a value the
  project already set.
- **`add-task`** — interview a request into real acceptance criteria, allocate an ID, place it in
  TODO.
- **`implement-task`** — the four-phase loop above.
- **`refine-backlog`** — a periodic pass: reprioritize, recompute blocked status, flag stale or
  underspecified tasks.
- **`plan-feature`** — spec → epics → vertical-slice tasks.
- **`review-docs`** — a periodic pass: audit `docs_review_paths` for staleness, dangling
  cross-references, and drift, and propose fixes.
- **`strip-project-references`** — repo-only, not part of what gets vendored elsewhere: a
  periodic pass that keeps this repo's own shipped `.claude/skills/**` surface free of
  project-specific references, auto-fixing what's mechanically safe and proposing the rest.

## Example usage

A new feature, from idea to merged PR:

```
/plan-feature
```
Interviews you for the problem/goals/non-goals/alternatives, drafts `SPEC-002-*.md` and **stops**
for your approval. Once approved, decomposes the feature into vertical slices, groups them under
`EPIC-002-*.md`, checks the slice dependency graph for cycles, **stops** again, then fans out to
`add-task` for each slice (in dependency order) — landing several `TASK-*.md` files in TODO.

```
/implement-task
```
Picks the top unblocked TODO task (or pass a specific `TASK-NNN`), branches from
`origin/main`, sets `status: in-progress`, and **restates the plan** for approval. Once approved:
writes the code and tests, runs `test_command`, walks the task's Testing strategy. Then commits,
rebases, pushes, opens a PR (acceptance criteria checked off, test results filled in) — **stops**
for review. You review and squash-merge on GitHub.

```
/implement-task
```
Re-invoked, it detects the PR merged, records `merge_commit:`, sets `status: done`, runs `sync`
(archiving the task and updating the board/epic), and deletes the branch — no further input
needed.

```
/refine-backlog
```
A periodic pass: reports the blocked-task chain, flags any `todo` task that's gone stale (by
actual development activity, not wall-clock age) as a `wont-do` candidate, flags under-specified
tasks for re-interview, and lets you confirm or reorder TODO priority. Proposes changes and waits
— never acts unilaterally.

## Status

See `.tasks/BOARD.md` for current progress.

trivial change

