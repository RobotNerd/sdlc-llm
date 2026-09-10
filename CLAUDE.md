# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **self-hosting toolkit** for a solo, LLM-driven SDLC workflow — "kanban in markdown". The repo
uses its own workflow to build itself: `.tasks/` holds the spec, the epic, and the tasks for the
v1 toolkit, and once the tooling exists it manages that same `.tasks/` directory.

Nothing is built yet — `.tasks/` is all markdown and there is no `sync` script or skills on disk.
The v1 build is tracked as EPIC-001 with 20 tasks.

## The workflow model

Read `.tmp/workflow-plan.md` first — it is the operating manual (mental model + how we run tasks
during bootstrap). The one rule everything follows from: **frontmatter is the source of truth;
everything else is a rendering of it.**

- **`.tasks/specs/SPEC-*.md`** — the "why" (PRD). `SPEC-001-llm-sdlc-workflow.md` is the spec for
  this toolkit and is the authority for every task. It supersedes `.tmp/project-management-plan.md`
  (the original analysis) and `README.md` (an older design sketch).
- **`.tasks/EPIC-*.md`** — a grouping container with a `sync`-derived status. Never hand-edit an
  epic's `status` (except to set `wont-do`).
- **`.tasks/TASK-*.md`** — one task = one branch = one PR = one sitting. No sub-tasks.
- **`.tasks/BOARD.md`** — mostly generated. Only the **TODO list** is hand-maintained (priority
  order), and `sync` is forbidden from reordering it.
- **`.tasks/config.md`** — per-project settings the skills and `sync` read (does not exist yet;
  TASK-001 authors it).

### Generated regions

Text between `<!-- BEGIN:name -->` and `<!-- END:name -->` markers is owned by `sync`. **Never
hand-edit inside them** — change the source task/epic file and (once it exists) run `sync`. Empty
region renders as `_(none)_`. Until `sync` exists, these regions are hand-written to match the
exact byte shape `sync` will emit (SPEC-001 §"Generated regions" / §"Rendering details").

### `sync` (planned, `.tasks/bin/sync`)

Single-file Python 3, **standard library only**. Regenerates all generated regions, derives epic
status (7 ordered rules), allocates IDs (`sync next-id`), reconciles `blocked_by`/`blocks`,
archives `done`/`wont-do`. `sync check` is the read-only CI form. Must be idempotent — running it
twice produces no diff. Its test suite needs `pytest` (the only dev dependency, in
`pyproject.toml`); no conda/uv required.

## Working a task (bootstrap mode — SPEC-001 §`implement-task`)

Four phases, each ending in a **STOP** for human input:

1. **Start** — dirty-tree check; pick top unblocked TODO task; `git fetch origin` + branch from
   `origin/main` as `task-NNN-slug`; set `status: in-progress` + `branch:`; restate plan for
   approval.
2. **Implement + test** — code + unit tests; run `test_command`/`lint_command`; walk the Testing
   strategy, handing non-automatable steps to the human and recording results in the task's
   **Worklog**; stay strictly in scope (`git diff --name-only`).
3. **Wrap up** — commit (conventional, cites `TASK-NNN`); rebase onto `origin/main` (surface
   conflicts); push (`--force-with-lease` only after a rebase, only on the task branch); `gh pr
   create`; record `pr:`; set `status: in-review`. **No merge.**
4. **Merge — observed, never performed** — the human reviews and **squash-merges** on GitHub.
   Poll `gh pr view --json state,mergeCommit`; once merged, record `merge_commit:`, set
   `status: done`, delete the branch, fast-forward local `main`.

Resumable: infer the current phase from working-tree state, branch existence, frontmatter, and
`gh pr view`.

## Guardrails

- Never push to `main`. Never `gh pr merge` — the human merges.
- Force-push only as `--force-with-lease`, only on the current task's branch, only after a rebase.
- Never touch files outside the current task's scope.
- Never hand-edit inside `BEGIN:`/`END:` regions, or an epic's `status` (except `wont-do`).
- Board regeneration, ID allocation, archiving, blocked-status are `sync`'s job, not judgement.

## Conventions

- Terminology: **"task"**, never "ticket"/"story".
- Branch: `task-NNN-slug`. Commit + PR title cite `TASK-NNN`.
- Git is automated via `git` + `gh` (installed, authed as `RobotNerd` on `RobotNerd/sdlc-llm`).
- `.tmp/` is intentionally **not** gitignored — `workflow-plan.md` is a checked-in living doc.
  `.tmp/prompts.md` is the user's private prompt scratch pad — do not read or act on it.

## Verification

No app to run yet. To sanity-check the task graph after editing dependencies or the TODO order,
the scratch script at `verify.py` (see `.tmp/` history / session scratchpad) checks: frontmatter
parses, IDs gapless, `blocks` mirrors `blocked_by`, graph acyclic, TODO order is a valid
topological sort, board annotations match. The real proof lands at TASK-019: the first full `sync`
run must produce **no diff** against the hand-written regions.
