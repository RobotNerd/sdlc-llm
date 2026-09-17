---
workflow_version: 1
---

# Workflow guidelines

The shared model every skill assumes — the parts of this repo's "kanban in markdown" workflow
that don't belong to any one skill. `.tasks/config.md` holds the per-project values these rules
refer to; `.tasks/specs/SPEC-001-llm-sdlc-workflow.md` is the full spec they're drawn from. Each
skill's own `SKILL.md` owns its own step-by-step procedure — this file doesn't repeat it.

Terminology: **task**, always — never "ticket" or "story".

## The artifact model

**Frontmatter is the source of truth; everything else is a rendering of it** (SPEC-001 §"Data
model").

- A **spec** (`.tasks/specs/SPEC-NNN-slug.md`) captures the "why": problem, alternatives
  considered, non-goals. Written by `plan-feature`.
- An **epic** (`.tasks/EPIC-NNN-slug.md`) groups a body of work and links back to its spec via
  `spec:`. Its `status` is **derived by `sync`** from its children — never hand-set, except to
  mark it `wont-do` (cancelling is a human decision).
- A **task** (`.tasks/TASK-NNN-slug.md`) is one unit of work: one branch, one PR, one sitting. No
  sub-tasks — split the task or promote it to an epic instead. Links to its epic via `epic:`
  (nullable — a loose chore needs none).
- IDs are allocated by `sync next-id <type>` — never by counting files yourself (SPEC-001
  §"ID allocation").

## What `sync` owns, and what you own

`sync` (`.tasks/bin/sync`) owns: ID allocation, regenerating every `BEGIN:`/`END:` region in
`BOARD.md`/`EPIC-*.md`/`SPEC-*.md` (SPEC-001 §"Generated regions"), deriving epic status (§"Epic
status derivation"), reconciling `blocked_by`/`blocks`, and archiving `done`/`wont-do` tasks. None
of that is model judgement — run `sync`, don't hand-compute it. `sync check` is the read-only
form: it verifies, it never fixes.

You own the **TODO list's hand-ordered priority** — the one thing in `BOARD.md` that's
hand-maintained, because priority order is a judgement call `sync` can't infer (§"TODO"). Nothing
else in `BOARD.md`, and nothing inside a `BEGIN:`/`END:` region anywhere, is yours to edit by
hand — change the source task/epic file and re-run `sync`.

## Which skill when

| Situation | Skill |
|---|---|
| Scaffold `.tasks/` into a new repo, or refresh an already-scaffolded one | `init-project` |
| Turn a rough request into a well-formed task | `add-task` |
| Do a task: branch → implement → PR → observed merge | `implement-task` |
| Periodic backlog triage: reprioritize, recompute blocked status, flag stale/underspecified tasks | `refine-backlog` |
| Plan a larger feature: spec → epics → vertical-slice tasks | `plan-feature` |
| Periodic docs health pass: staleness, dangling references, guidelines-mirror drift | `review-docs` |
| Keep this repo's own shipped skills surface portable (repo-only) | `strip-project-references` |

## Guardrails that need your judgement

The rest of SPEC-001's Guardrails list (§"Guardrails") is now hook-enforced, not something to
reason about by hand. Two aren't, because no hook can supply the judgement:

- Never touch files outside the current task's scope — `git diff --name-only` is the check.
- Never skip a Testing strategy step silently. Hand anything non-automatable to the human and
  record the result in the task's Worklog.
