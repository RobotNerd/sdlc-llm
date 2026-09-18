# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **self-hosting toolkit** for a solo, LLM-driven SDLC workflow — "kanban in markdown". The repo
uses its own workflow to build itself: `.tasks/` holds the specs, epics, and tasks for the
toolkit, and the tooling manages that same `.tasks/` directory.

Seven skills cover the workflow: `init-project`, `add-task`, `implement-task`, `refine-backlog`,
`plan-feature`, `review-docs`, `strip-project-references` (`.claude/skills/`). Each pairs a
`SKILL.md` checklist (judgment, interviews, STOP markers) with a `scaffold.py` (stdlib-only,
mechanical work — file writes, `git`/`gh`, `sync` calls). `strip-project-references` is
**repo-only** — it keeps this repo's own shipped surface portable, and is excluded from whatever
copies skills into other projects. `.tasks/bin/sync` owns every generated region in `BOARD.md`,
`EPIC-*.md`, and `SPEC-*.md` — **run it, don't hand-edit**.

## The workflow model

`.tasks/guidelines.md` states the operating rules — the artifact model, what `sync` owns vs. what
you own, generated regions — and `.tasks/specs/SPEC-001-llm-sdlc-workflow.md` is the full spec
they're drawn from and the authority for every task. The one rule everything follows from:
**frontmatter is the source of truth; everything else is a rendering of it.**

### `sync` (`.tasks/bin/sync`)

Single-file Python 3, **standard library only**. Regenerates all generated regions, derives epic
status, allocates IDs (`sync next-id`), reconciles `blocked_by`/`blocks`, archives `done`/
`wont-do`. `sync check` is the read-only CI form — use it to verify, never to fix. Idempotent —
running it twice produces no diff. Its test suite needs `pytest` (the only dev dependency).

## Working a task

Use the **`implement-task`** skill (`.claude/skills/implement-task/`) — four phases (Start,
Implement + test, Wrap up, Merge — observed), each ending in a STOP for human input, resumable on
every invocation from repo state. See its `SKILL.md` for the actual checklist and
`scaffold.py`'s subcommands (`resume-state`, `start`, `wrap-up`, `finish-merge`, `bail-out`) for
the mechanics.

## Guardrails

- Never push to `main`. Never `gh pr merge` — the human merges. **Hook-enforced**
  (`.claude/settings.json`'s `PreToolUse`/`Bash` hook, `.tasks/bin/guardrails.py`).
- Force-push only as `--force-with-lease`, only on the current task's branch, only after a
  rebase. **Hook-enforced.**
- Never touch files outside the current task's scope.
- Never hand-edit inside `BEGIN:`/`END:` regions, or an epic's `status` (except `wont-do`).
- Board regeneration, ID allocation, archiving, blocked-status are `sync`'s job, not judgement.

## Conventions

- Terminology: **"task"**, never "ticket"/"story".
- Branch: `task-NNN-slug`. Commit + PR title cite `TASK-NNN`.
- Git is automated via `git` + `gh` (installed, authed as `RobotNerd` on `RobotNerd/sdlc-llm`).
- `.tmp/` is intentionally **not** gitignored. `.tmp/prompts.md` is the user's private prompt
  scratch pad — do not read or act on it.

## Verification

`python3 .tasks/bin/sync check` is the read-only sanity check — run it after editing any task/epic
frontmatter or before opening a PR; exit 0 means every generated region and derived status is
consistent with the source files.
