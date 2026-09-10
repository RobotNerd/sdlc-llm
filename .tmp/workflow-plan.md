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
| 1. Start | pick top unblocked TODO task, branch, `status: in-progress`, restate plan | **before any code** |
| 2. Implement + test | code, unit tests, run the Testing strategy, record results in Worklog | after tests |
| 3. Wrap up | docs, commit, push, **open** PR, `status: in-review` | **PR open, not merged** |
| 4. Merge | separate go-ahead, CI green, merge, `status: done`, archive | done |

The STOPs exist because the original design did all of this in one uninterrupted run *including
auto-merge* — which defeats the purpose of opening a PR at all.

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
| `sync` home | `.tasks/bin/sync` — single stdlib file beside the data it manages |
| Test setup | `pyproject.toml`, pytest as the only dev dependency, `test_command: pytest` |
| Sequencing | Front-load `sync`; drop the soft `TASK-004 ← TASK-002` edge |

## Step 0 — prerequisite (you, manually)

`mvp` is 3 commits ahead of `main` and holds all the spec and task work. Land it first, or every
task branch forks from a `main` that has no tasks in it:

```sh
git checkout main && git merge mvp && git push origin main
```

## Changes to make before TASK-001 starts

1. **`.tasks/TASK-004-sync-frontmatter-parser.md`** — remove `TASK-002` from `blocked_by`. The
   parser targets SPEC-001's schema, which already exists; it does not need the templates. Remove
   the mirrored `TASK-004` from `TASK-002`'s `blocks`, and note the reason in TASK-004's Notes.
2. **`.tasks/TASK-004-...md`** — add an acceptance criterion: creates `pyproject.toml` (pytest as
   sole dev dep) and the `tests/` directory, since it is the first task to ship Python.
3. **`.tasks/BOARD.md`** — rewrite the TODO list in the new order below.
4. **`.tasks/specs/SPEC-001-llm-sdlc-workflow.md`** — record the script's home (`.tasks/bin/sync`)
   in §"The `sync` script"; it currently says "single-file Python 3 script" with no path.

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

I follow SPEC-001's four-phase checklist by hand. **You run every git command.**

**Phase 1 — Start.** I name the top unblocked TODO task and hand you the branch command
(`git checkout main && git pull && git checkout -b task-NNN-slug`). You run it. I set
`status: in-progress` and `branch:` in the task frontmatter, update the board, then restate the
plan and acceptance criteria. → *you approve* → **STOP**

**Phase 2 — Implement + test.** I write the files and unit tests, run `test_command` /
`lint_command` once they exist, then walk the task's Testing strategy. Anything not automatable I
hand to you to run, and record your result in the task's **Worklog**. I touch nothing outside the
task's scope. → **STOP**

**Phase 3 — Wrap up.** I update docs and draft the conventional commit message
(`feat(TASK-001): …`) plus the PR title and body with acceptance criteria as a checklist. You run
`git add` / `commit` / `push` and open the PR in the web UI. I record `pr:` and set
`status: in-review`. → **STOP, no merge**

**Phase 4 — Merge.** Separate go-ahead from you, gated on tests passing (on CI once TASK-020
lands). You merge and `git checkout main && git pull`. I record `merge_commit:`, set
`status: done`, and update the board — via `sync` once it exists.

## Gaps

| Gap | Effect now | Closes at |
|---|---|---|
| **Git is manual** — your call, by design | I draft every command and message; you execute. Nothing is committed or pushed without you | whenever you delegate |
| **`gh` CLI not installed** | PRs opened via web UI. TASK-016's resumability detects state via `gh pr view` — it must degrade gracefully when `gh` is absent. Worth adding to its acceptance criteria | install `gh`, or design around it |
| **No skills exist** | I hand-follow SPEC-001's phase checklists. Risk: I drift from them — call it out if I skip a STOP | TASK-016 |
| **No `sync`** | I hand-maintain task frontmatter + the TODO list; the `epics` panel, status columns and EPIC-001 `children` region go deliberately stale | TASK-008/009, verified by TASK-012 |
| **Epic status won't roll up** | EPIC-001 reads `todo` on paper even once work starts | TASK-006 |
| **No CI** | "merge gated on green CI" is "tests pass locally" | TASK-020 |
| **No `.tasks/archive/`** | Done tasks accumulate on the board | TASK-011 |
| **`CLAUDE.md` is stale** | Still says "design-stage, no application code" — wrong the moment TASK-004 lands | TASK-019, or opportunistically |
| **`prompts.md`** | Untracked, contents just `# prompts`, not referenced by any task | your call |
| **`.tmp/` is not gitignored** | `.gitignore` has `tmp/`, which does not match `.tmp/` — this file would be committed | add `.tmp/` to `.gitignore` if unintended |

## Verification

1. **Step 0 worked:** `git log --oneline main..mvp` is empty and `main` contains `.tasks/`.
2. **Graph still sound:** re-run the dependency checks after the TASK-004 edit — `blocks` is still
   the exact mirror of `blocked_by`, the graph is acyclic, the new TODO order is a valid
   topological sort, all 20 tasks listed exactly once.
3. **Board annotations match:** TASK-004's TODO line no longer carries a ⛔ marker.
4. **First loop end-to-end:** run TASK-001 through all four phases. Success = a merged PR titled
   for `TASK-001`, its frontmatter reading `status: done` with `pr:` and `merge_commit:` filled,
   and `.tasks/config.md` + `.tasks/guidelines.md` present on `main`.
5. **The real proof, later:** at TASK-019 the first full `sync` run produces **no diff** against
   the hand-written generated regions. A mismatch means the spec was underspecified — file it as a
   defect rather than editing the regions to match.
