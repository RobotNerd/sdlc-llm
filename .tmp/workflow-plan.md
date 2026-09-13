# The workflow, and how we bootstrap it

Two parts: **(1)** a mental model of the workflow SPEC-001 defines, and **(2)** the manual
procedure we follow until enough of it exists to run itself.

---

# Part 1 — The workflow

## The Jira mapping

| This repo | Jira / Confluence equivalent |
|---|---|
| `.tasks/specs/SPEC-*.md` | the Confluence PRD — the *why* |
| `.tasks/EPIC-*.md` | the Jira epic — a container, no work of its own |
| `.tasks/TASK-*.md` | the story |
| `.tasks/BOARD.md` | the board view (incl. the epic panel) |
| `.tasks/config.md` | per-project settings the skills read |

There are **no sub-tasks**, by design. A task is one branch, one PR, one sitting. Anything bigger
gets split into siblings or promoted to an epic. Also deliberately absent: story points, velocity,
cycle-time metrics, sprints.

## The one rule everything follows from

**Frontmatter is the source of truth; everything else is a rendering of it.**

- A task's `status` lives in that task's own file.
- `BOARD.md` does not own status — it *displays* it.
- An epic does not own its status either. `sync` computes it from its children.

This is what makes markdown kanban survivable with an LLM doing the editing. The classic failure
is the board and the task files drifting apart because the model hand-edited two files and got one
wrong. Here it structurally cannot: there is exactly one writable copy of each fact.

## Epic status is derived, not set

Seven ordered rules, first match wins (SPEC-001 §"Epic status derivation"):

1. human-set `wont-do` → preserved (cancelling is a human decision)
2. no children, or all `todo` → `todo`
3. any child `in-progress`/`in-review` → `in-progress`
4. ≥1 child, all `blocked` → `blocked`
5. ≥1 child, all `wont-do` → `wont-do`
6. ≥1 child, all `done`/`wont-do` with ≥1 `done` → `done`
7. otherwise → `in-progress`

## The determinism boundary

Anything mechanical belongs to `sync`, not to model judgement:

- board regeneration and the epic roll-up panel
- epic status derivation
- ID allocation (`sync next-id` — max existing ID of that type across `.tasks/`, `.tasks/specs/`
  **and** `.tasks/archive/`, plus 1)
- `blocked_by` / `blocks` reconciliation
- archiving `done` / `wont-do` out to `.tasks/archive/`

Two consequences for me: **never hand-edit between `BEGIN:`/`END:` markers**, and **never set an
epic's status** (except `wont-do`, which is yours).

## The one thing that is yours

**TODO order.** `sync` may drop lines whose task left `todo`, append new ones, and re-annotate
each line with its epic tag and blocked marker — but it is forbidden from reordering. Priority is
the single thing a model cannot infer.

## Two loops

**Feeding the backlog**

```
plan-feature  →  writes a SPEC, decomposes into vertical slices, creates epic(s)
add-task      →  interviews you into real acceptance criteria, allocates ID, places in TODO
refine-backlog→  periodic: reprioritise, recompute blocked, flag stale / underspecified
```

**Executing a task** — `implement-task`, four phases with a hard **STOP** between each:

| Phase | Does | Ends |
|---|---|---|
| 1. Start | dirty-tree check, pick top unblocked TODO task, `git fetch` + branch from `origin/main`, `status: in-progress`, restate plan | **before any code** |
| 2. Implement + test | code, unit tests, run the Testing strategy, record results in Worklog, stay in scope | after tests |
| 3. Wrap up | docs, conventional commit, rebase onto `origin/main`, push (`--force-with-lease` after rebase), `gh pr create`, `status: in-review` | **PR open, not merged** |
| 4. Merge — observed | a human reviews and **squash-merges** on GitHub; the skill polls `gh pr view`, then records `merge_commit`, `status: done`, archives, deletes the branch, ff-s local `main` | done |

The STOPs exist because the original design did all of this in one uninterrupted run *including
auto-merge* — which defeats the purpose of opening a PR at all. **The skill never merges** — it
opens the PR and stops; phase 4 only observes the human's merge and records it.

Two more behaviours worth knowing: **resumability** (on invocation it infers the current phase
from branch existence + frontmatter + PR state, rather than restarting) and the **bail-out path**
(if a task turns out to be wrong mid-flight: stop, write findings into the task file, move it back
to `todo`/`blocked`, surface it).

---

# Part 2 — Bootstrapping

## The problem

`.tasks/` holds SPEC-001, EPIC-001 and 20 tasks, but **none of the tooling those tasks describe
exists** — no `sync`, no skills, no config, no CI. We cannot use the workflow to build the
workflow.

But the workflow splits in two, and only one half is missing:

- **The git/PR half** — branch per task, conventional commit citing the task ID, PR carrying the
  acceptance criteria as its checklist, merge. **Needs no tooling.** We run it from task one.
- **The board half** — `sync`. Doesn't exist. Until it does I keep frontmatter current by hand and
  we let the derived views go stale on purpose.

## Decisions

| Decision | Choice |
|---|---|
| Branching | Per-task branches off `main`, PR into `main` — SPEC-001's flow verbatim |
| Git driver | Automated via `git` + `gh` (installed, authed). Rebase-before-PR, `--force-with-lease` only after a rebase. **Human reviews every PR and does the squash & merge on GitHub**; the skill never merges |
| `sync` home | `.tasks/bin/sync` — single stdlib file beside the data it manages |
| Test setup | `pyproject.toml`, pytest as the only dev dependency, `test_command: pytest`. No conda/uv |
| Sequencing | Front-load `sync`; drop the soft `TASK-004 ← TASK-002` edge |

## Step 0 — prerequisite (done)

`mvp` was merged to `main` (the spec + tasks are on `main`). Refinements now go through
`feat/initial-workflow` → PR → squash-merge before TASK-001 starts.

## Changes made before TASK-001 (done — on `feat/initial-workflow`)

1. ✅ **TASK-004** — dropped `TASK-002` from `blocked_by`; removed the mirror from `TASK-002`'s
   `blocks`; reason noted in both files' Notes.
2. ✅ **TASK-004** — added acceptance criteria: `.tasks/bin/sync` path, root `pyproject.toml` with
   `pytest` as the sole dev dep, `tests/` directory.
3. ✅ **`.tasks/BOARD.md`** — TODO list rewritten in the new order below; `TASK-004` loses its ⛔.
4. ✅ **SPEC-001** — script home fixed at `.tasks/bin/sync`; `config.md` schema gained the git
   keys (`remote`, `rebase_before_pr`, `merge_strategy`, `delete_branch_after_merge`); Guardrails
   gained the never-merge and `--force-with-lease`-only rules; `implement-task` phases 1/3/4
   rewritten for `git`+`gh` automation.
5. ✅ **TASK-001 / TASK-014 / TASK-016** — acceptance criteria updated for the git keys and the
   `gh`-driven phases.

### New TODO order

```
001, 005, 004, 006, 007, 008, 009, 012, 010, 011,
013, 002, 003, 019, 020, 014, 015, 016, 017, 018
```

- `sync check` goes live at **position 8** (was 13).
- The fully-manual window shrinks to the **first 6 tasks**.
- `001` moves to the front because `sync` reads `config.md` — and it is small, pure authoring, a
  gentle first run through the loop.
- Verified as a valid topological order against the amended dependency graph.

## The per-task loop (bootstrap mode)

I follow SPEC-001's four-phase checklist. **I run `git` and `gh`.** You review and squash-merge
each PR on GitHub — that is the only step that is yours.

**Phase 1 — Start.** I check the tree is clean, name the top unblocked TODO task, run
`git fetch origin && git switch -c task-NNN-slug origin/main`, set `status: in-progress` and
`branch:`, update the board, then restate the plan and acceptance criteria. → *you approve* →
**STOP**

**Phase 2 — Implement + test.** I write the files and unit tests, run `test_command` /
`lint_command` once they exist, then walk the task's Testing strategy. Anything not automatable I
hand to you to run, and record your result in the task's **Worklog**. I stay strictly in scope
(`git diff --name-only`). → **STOP**

**Phase 3 — Wrap up.** I update docs, make the conventional commit (`feat(TASK-001): …`), rebase
onto `origin/main` (surfacing any conflict), push (`--force-with-lease` if the rebase rewrote
pushed history), and run `gh pr create` with the acceptance criteria as a checklist. I record
`pr:` and set `status: in-review`. → **STOP** — over to you

**Phase 4 — Merge (yours, then I observe).** You review the PR on GitHub and **squash & merge**.
On my next turn I poll `gh pr view --json state,mergeCommit`; once merged I record `merge_commit:`,
set `status: done`, update the board (via `sync` once it exists), delete the task branch, and
fast-forward local `main`. I never run `gh pr merge`.

## Gaps

Updated 2026-09-13, 12/20 tasks done. See `.tmp/session-handoff.md` for exactly where things
stand and how to resume.

| Gap | Status |
|---|---|
| **No `sync`** | ✅ Closed — TASK-004 through TASK-013. `.tasks/bin/sync check` (read-only) and `.tasks/bin/sync` (write mode, TASK-013) both exist and are fully tested. |
| **Epic status won't roll up** | ✅ Closed — TASK-006 (`derive_epic_status`, 7 rules). |
| **No `.tasks/archive/`** | ✅ Closed — TASK-011 (`sync archive`). |
| **Merge is manual** — by design | Unchanged, and staying this way: I open every PR and stop; you review and squash-merge on GitHub; I observe the result next turn. |
| **Git driver is checklist prose, not code** | Unchanged. I still run `git`/`gh` by following the phase checklist by hand each task (no skill exists yet to encode it — that's TASK-016). |
| **No skills exist** | Unchanged — TASK-014 through TASK-018, not started. |
| **No CI** | Unchanged — TASK-020, not started. "Merge gated on green CI" is still "tests pass locally" + your eyeball. |
| **`gh` degradation path untested** | Unchanged — exercising it is part of TASK-016's own testing strategy. |
| **`sync`'s write mode not yet run on this repo for real** | New, deliberate: TASK-013 built it, but phase-4 bookkeeping still hand-edits `BOARD.md`/`EPIC-001`/`SPEC-001` rather than running bare `sync`, on purpose — so TASK-019's "first real run" stays a meaningful proof rather than already-true-by-construction. |

## Verification

The original bootstrap-specific verification steps (TASK-001 through the graph/board checks) all
passed and are now historical — see the archived task Worklogs under `.tasks/archive/` for what
each one actually found. For current status and how to resume, see `.tmp/session-handoff.md`.
