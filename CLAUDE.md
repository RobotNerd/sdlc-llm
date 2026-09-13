# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **self-hosting toolkit** for a solo, LLM-driven SDLC workflow — "kanban in markdown". The repo
uses its own workflow to build itself: `.tasks/` holds the spec, the epic, and the tasks for the
v1 toolkit, and the tooling now manages that same `.tasks/` directory (dogfooded as of TASK-019 —
the first real `sync` run on this repo was a no-op, proving the hand-written regions it replaced
were spec-accurate).

`.tasks/bin/sync` is built and live: it owns every generated region in `BOARD.md`, `EPIC-*.md`,
and `SPEC-*.md` now — **run it, don't hand-edit**. The five skills (`init`, `add-task`,
`implement-task`, `refine-backlog`, `plan-feature` — TASK-014 through TASK-018) don't exist yet;
until they land, work a task by hand following the phases below. The v1 build is tracked as
EPIC-001 with 20 tasks — see `.tasks/BOARD.md` for current progress.

## The workflow model

Read `.tmp/workflow-plan.md` first — it is the operating manual (mental model + how we run tasks
until the skills exist). The one rule everything follows from: **frontmatter is the source of
truth; everything else is a rendering of it.**

- **`.tasks/specs/SPEC-*.md`** — the "why" (PRD). `SPEC-001-llm-sdlc-workflow.md` is the spec for
  this toolkit and is the authority for every task. It supersedes `.tmp/project-management-plan.md`
  (the original analysis) and `README.md` (an older design sketch).
- **`.tasks/EPIC-*.md`** — a grouping container with a `sync`-derived status. Never hand-edit an
  epic's `status` (except to set `wont-do`).
- **`.tasks/TASK-*.md`** — one task = one branch = one PR = one sitting. No sub-tasks.
- **`.tasks/BOARD.md`** — mostly generated. Only the **TODO list** is hand-maintained (priority
  order), and `sync` is forbidden from reordering it.
- **`.tasks/config.md`** — per-project settings the skills and `sync` read (authored in TASK-001).

### Generated regions

Text between `<!-- BEGIN:name -->` and `<!-- END:name -->` markers is owned by `sync`. **Never
hand-edit inside them** — change the source task/epic file and run `.tasks/bin/sync` (bare, no
args). Empty region renders as `_(none)_` (SPEC-001 §"Generated regions" / §"Rendering details").

### `sync` (`.tasks/bin/sync`)

Single-file Python 3, **standard library only**. Regenerates all generated regions, derives epic
status (7 ordered rules), allocates IDs (`sync next-id`), reconciles `blocked_by`/`blocks`,
archives `done`/`wont-do`. `sync check` is the read-only CI form — use it to verify, never to fix.
Must be idempotent — running it twice produces no diff (proven on this real repo by TASK-019).
Its test suite needs `pytest` (the only dev dependency, in `pyproject.toml`); no conda/uv
required.

## Working a task (no skills yet — SPEC-001 §`implement-task`, run by hand)

Four phases, each ending in a **STOP** for human input:

1. **Start** — dirty-tree check; pick top unblocked TODO task; `git fetch origin` + branch from
   `origin/main` as `task-NNN-slug`; set `status: in-progress` + `branch:`; run `sync` (updates
   the board/epic); restate plan for approval.
2. **Implement + test** — code + unit tests; run `test_command`/`lint_command`; walk the Testing
   strategy, handing non-automatable steps to the human and recording results in the task's
   **Worklog**; stay strictly in scope (`git diff --name-only`).
3. **Wrap up** — commit (conventional, cites `TASK-NNN`); rebase onto `origin/main` (surface
   conflicts); push (`--force-with-lease` only after a rebase, only on the task branch); `gh pr
   create`; record `pr:`; set `status: in-review`; run `sync`. **No merge.**
4. **Merge — observed, never performed** — the human reviews and **squash-merges** on GitHub.
   Poll `gh pr view --json state,mergeCommit`; once merged, record `merge_commit:`, set
   `status: done`, run `sync` (regenerates board/epic, archives), delete the branch, fast-forward
   local `main`.

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

`python3 .tasks/bin/sync check` is the read-only sanity check — run it after editing any task/epic
frontmatter or before opening a PR; exit 0 means every generated region and derived status is
consistent with the source files. TASK-019 proved it end to end: the first real `sync` run on this
repo produced an empty diff against the regions that had been hand-written to match its exact
output. There's still no app beyond `sync` itself to run.
