---
id: SPEC-001
title: LLM-driven SDLC workflow — "kanban in markdown" with epics
status: draft            # draft | approved | superseded
created: 2026-09-09
---

# SPEC-001: LLM-driven SDLC workflow

## Problem

`.tmp/project-management-plan.md` critiques the workflow sketched in `README.md` and reaches firm
conclusions, but it is written as feedback on a design, not as something buildable: there are no
schemas to code against, no derivation rules, no scope line. Separately, the workflow has no
concept of an **epic** — a grouping layer above the task — which the user relies on in Jira
(Epic → Task, plus an epic panel on the board).

This spec turns the analysis into a PRD for a v1 toolkit, and adds epic tracking.

## Goals

- A markdown-native task tracker for solo, single-repo projects: no external service, state lives
  with the code, every change is diffable in a PR.
- Frontmatter is the single machine-readable source of truth; `BOARD.md` is mostly a rendered view.
- A deterministic `sync` script does everything that does not require judgement (board
  regeneration, epic roll-up, ID allocation, blocked computation, archiving).
- Five skills drive the lifecycle: `init`, `add-task`, `implement-task`, `refine-backlog`,
  `plan-feature`.
- An **epic** layer that groups tasks and rolls their status up to a board panel.
- Generic skill logic is separated from per-project config so the same skills work in any repo.

## Non-goals (v1)

Called out because a Jira user will look for these and should know they are deliberately absent:

- **Sub-tasks.** A task is one branch / one PR / one sitting. If it needs sub-tasks, either split
  it into sibling tasks or promote it to an epic.
- **Estimates, story points, velocity.**
- **Cycle-time / throughput metrics.** Derivable from git history later if ever wanted.
- **Sprints / iterations.** The board is a continuous flow, not time-boxed.
- **Extracting the toolkit into a reusable global workflow.** v1 is dogfooded in *this* repo;
  packaging for reuse is a follow-on spec once the shape is proven.
- **A separate "Epic" status vocabulary.** Epics reuse the task status values (see derivation).

## Audience

A single developer working with an LLM assistant in one repository, comfortable with a Jira-style
Epic → Task hierarchy and a kanban board.

---

## Data model

Three artifact types, each a markdown file with YAML frontmatter.

| Type | File | Owns |
|---|---|---|
| Spec | `.tasks/specs/SPEC-NNN-slug.md` | the "why": problem, alternatives considered, non-goals |
| Epic | `.tasks/EPIC-NNN-slug.md` | grouping and status roll-up for a body of work |
| Task | `.tasks/TASK-NNN-slug.md` | one unit of work = one branch = one PR |

### ID allocation

IDs are a per-type integer sequence, zero-padded to three digits (`TASK-011`). To allocate the
next ID of a type:

> Take the maximum existing ID of that type across `.tasks/`, `.tasks/specs/`, **and**
> `.tasks/archive/`, and add 1.

Scanning the archive is what keeps IDs from colliding after a done task is archived. Allocation is
performed by `sync` (exposed as `sync next-id <type>`), never by model arithmetic.

### Relationships — stored on the child only

A parent never lists its children in frontmatter; the child names its parent, and the parent's
child list is always *derived* by `sync` into a generated region.

- **Task → Epic:** the task carries `epic: EPIC-003` (nullable — a loose chore needs no epic).
  This is Jira's "Epic Link".
- **Epic → Spec:** the epic carries `spec: SPEC-001` (nullable). One spec may spawn several epics.
- **Task → Task:** `blocked_by` / `blocks` lists, as in the analysis doc. `blocks` is a
  convenience mirror that `sync` keeps consistent with the `blocked_by` edges; if the two
  disagree, `blocked_by` wins. `blocked_by` is a **static, declared dependency list** — nothing
  prunes it as a blocker completes; it stays the true historical graph. "Is this task still
  blocked" is answered at render time by checking each listed blocker's current `status`
  (`done`/`wont-do` = satisfied), not by mutating the list. The TODO ⛔ marker shows only
  currently-outstanding blockers for exactly this reason.

### Task frontmatter

```yaml
id: TASK-011
title: Use API to request current weather
type: feature          # feature | bug | chore | refactor | docs
status: todo            # todo | in-progress | blocked | in-review | done | wont-do
epic: EPIC-003          # or null
created: 2026-09-09
branch: task-011-weather-api
pr: null                # PR URL once opened
merge_commit: null      # filled on merge
blocked_by: [TASK-008]
blocks: [TASK-012]
---
```

Body sections: **Description**, **Acceptance criteria** (a `- [ ]` checklist), **Testing
strategy**, **Worklog** (appended during implementation — decisions and deviations), **Notes**.

`type` widens the analysis doc's two-value enum. It is metadata only in v1 — no skill branches on
it yet — but it is cheap to record and useful for later filtering.

### Epic frontmatter

```yaml
id: EPIC-003
title: Board sync tooling
spec: SPEC-001          # or null
status: todo            # derived by sync — DO NOT EDIT (except to set wont-do)
created: 2026-09-09
---
```

Body sections: **Goal**, **In scope**, **Out of scope**, **Success criteria**, then a generated
children region (below).

### Spec frontmatter

```yaml
id: SPEC-001
title: LLM-driven SDLC workflow — "kanban in markdown" with epics
status: draft           # draft | approved | superseded
created: 2026-09-09
---
```

The spec's epic list is not a frontmatter field — it is the generated `epics` region in the body
(see Generated regions). Frontmatter holds source-of-truth values only; anything `sync` derives
lives in a region.

---

## Epic status derivation

`sync` computes each epic's `status` from its child tasks. Rules are evaluated **in order**; the
first match wins. This list is total — every possible child set matches exactly one rule.

1. If a human has set the epic to `wont-do`, it stays `wont-do`. `sync` never overwrites this —
   cancelling an epic is a human decision.
2. Else if the epic has no children, or every child is `todo` → **`todo`**.
3. Else if any child is `in-progress` or `in-review` → **`in-progress`**.
4. Else if there is at least one child and every child is `blocked` → **`blocked`**.
5. Else if there is at least one child and every child is `wont-do` → **`wont-do`**.
6. Else if there is at least one child and every child is `done` or `wont-do` (at least one
   `done`) → **`done`**.
7. Else (a mix of `todo` with some `done`/`wont-do`/`blocked`, none active) → **`in-progress`**.

Rule 5 covers an epic whose every task was abandoned — that reads as cancelled, not delivered.
Rule 7 is the catch-all: partial progress with nothing currently moving still reads as "started".

Worked cases:

| Children | Result | Rule |
|---|---|---|
| (none) | `todo` | 2 |
| all `todo` | `todo` | 2 |
| `todo`, `in-progress` | `in-progress` | 3 |
| `blocked`, `blocked` | `blocked` | 4 |
| `wont-do`, `wont-do` | `wont-do` | 5 |
| `done`, `wont-do` | `done` | 6 |
| `todo`, `done` | `in-progress` | 7 |
| epic hand-set to `wont-do`, children all `done` | `wont-do` | 1 |

---

## Generated regions

The mechanism that lets these files read like Jira pages while never needing a careful hand-edit:
`sync` only ever rewrites text **between markers**, and leaves everything outside them untouched.

```markdown
<!-- BEGIN:children (generated by sync — do not edit) -->
| Task | Status | Title |
|---|---|---|
| TASK-011 | done | Use API to request current weather |
| TASK-012 | todo | Cache weather responses |

Progress: 1/2 done
<!-- END:children -->
```

Marker rules:

- A region is delimited by `<!-- BEGIN:<name> ... -->` and `<!-- END:<name> -->` on their own
  lines.
- `sync` replaces only the lines strictly between them. If a region is missing from a file that
  should have one, `sync` appends it in the documented position.
- Hand-editing inside a region is a guardrail violation (see Guardrails); the edit is lost on the
  next `sync`.

Rendering details (so output is byte-stable and `sync check` is meaningful):

- Between the marker lines, `sync` emits exactly: the content lines, then a single trailing
  newline before `<!-- END -->`. No leading blank line after `BEGIN`.
- An **empty** region — a table with no rows — renders as the single line `_(none)_`.
- Column tables (`in-progress`, `in-review`, `blocked`, `done`) use the header
  `| Task | Title | Epic | Ref |`. `Ref` is the branch name while `in-progress`, the PR URL once
  `in-review` or `done`. A task with no epic shows `—` in the Epic cell.
- Table rows are ordered by task ID ascending. The `children` and `epics` panels likewise.

Regions in use:

| File | Region | Contents |
|---|---|---|
| `EPIC-*.md` | `children` | table of child tasks + `Progress: n/m done` |
| `SPEC-*.md` | `epics` | table of epics spawned from this spec + their derived status |
| `BOARD.md` | `epics` | roll-up panel (see below) |
| `BOARD.md` | `in-progress`, `in-review`, `blocked`, `done` | one region per non-TODO column |

---

## BOARD.md contract

`BOARD.md` has one hand-maintained section (TODO) and the rest is generated.

### Epics panel — generated (`BEGIN:epics`)

One row per epic whose derived status is not `done` and not `wont-do`:

```markdown
<!-- BEGIN:epics (generated by sync — do not edit) -->
| Epic | Status | Progress |
|---|---|---|
| EPIC-002 | in-progress | 3/7 done |
| EPIC-003 | todo | 0/2 done |
<!-- END:epics -->
```

This is the Jira epic panel: what bodies of work are open and how far along each is.

### TODO — hand-maintained, the only ordered thing in the system

The developer orders TODO by priority. `sync` must **preserve that order** and may only:

- **Drop** a line whose task has left `todo` status.
- **Append** — at the end — a line for any `todo` task not already listed.
- **Re-annotate** each line with its epic tag and a blocked marker.

`sync` must **never reorder** TODO. Line format:

```markdown
- TASK-012 — Cache weather responses  `EPIC-003`
- TASK-019 — Rotate API keys  `EPIC-002` ⛔ blocked_by TASK-008
```

A task with no epic simply omits the tag. Two distinct things share the word "blocked" here — a
`todo` task with a non-empty `blocked_by` (colloquially blocked, but its `status` field is still
`todo`) stays visible in TODO with the ⛔ marker, so the priority list stays complete; a task whose
`status` field is literally `blocked` (see below) has left `todo` and moves to its own column.

### In Progress / In Review / Blocked / Done — fully generated

Each is a `BEGIN:`/`END:` region holding a table of `ID | Title | Epic | Branch/PR`. `in-review`
is its own column (it maps to a real workflow state — a PR open, awaiting merge). Done is capped
(e.g. last 20) with older entries removed by archiving.

There is no "Won't do" column. `sync archive` moves `wont-do` task files to `.tasks/archive/`,
leaving only a one-line reference behind — the board shows active work, not a graveyard.

### Idempotency

Running `sync` twice in a row produces **no diff**. This is the core correctness property and the
thing to unit-test hardest — including the TODO-preservation logic, which is the one place `sync`
merges rather than regenerates.

---

## `.tasks/config.md`

Written by `init`, read by every skill and by `sync`. It is the seam that keeps skill logic
identical across projects — only this file changes per repo.

```yaml
---
workflow_version: 1
test_command: pytest
lint_command: ruff check .
docs_paths: [README.md, docs/]
default_branch: main
branch_prefix: task-
remote: origin
rebase_before_pr: true
merge_strategy: squash          # performed by a human; the skill never merges
delete_branch_after_merge: true
allow_auto_merge: false
ci_checks: [build, test]
archive_done: true
---
```

`workflow_version` exists so a future `upgrade` path can migrate older projects.

---

## The `sync` script

Lives at **`.tasks/bin/sync`** — a single-file **Python 3 script, standard library only** — no pip
dependencies, no YAML library (it hand-parses the small frontmatter subset the model produces:
scalars, `null`, and simple `[a, b]` lists). Rationale: Python is present on macOS and virtually
all Linux, so the script drops into any project regardless of that project's own language, and
keeping it under `.tasks/` means the whole workflow travels as one directory when it is later
extracted into a standalone repo. Its tests need `pytest` (declared as the only dev dependency in
`pyproject.toml`); the script itself imports nothing outside the standard library.

Subcommands:

| Command | Does |
|---|---|
| `sync` | regenerate all generated regions (epic `children`, spec `epics`, board panels + columns), recompute every epic `status`, reconcile `blocked`/`blocked_by`, then archive if `archive_done` |
| `sync check` | same computation, but exit non-zero and print a diff instead of writing — for CI and for skills to detect drift |
| `sync next-id <spec\|epic\|task>` | print the next free ID |
| `sync archive` | move `done` / `wont-do` task files to `.tasks/archive/`, leaving a one-line board reference with the PR link |

`sync check` in CI is what guarantees the committed board always matches the task files.

---

## Skills (v1)

All five are checklist-style with explicit **STOP** markers and "if X is ambiguous, ASK" rules —
not prose descriptions of intent. Each calls `sync` rather than hand-editing generated files.

### `init`

Scaffolds `.tasks/` in a new repo: empty `BOARD.md` with its regions, `config.md` (interviews the
user for `test_command`, the git settings — `remote`, `rebase_before_pr`, `merge_strategy`,
`delete_branch_after_merge` — etc.), `guidelines.md` (carrying `workflow_version`, and stating the
never-merge / `--force-with-lease`-only guardrails), templates under `.tasks/templates/` for
spec/epic/task, and `.github/pull_request_template.md` mirroring the acceptance-criteria checklist.

### `add-task`

Interviews rather than transcribes: if the description does not yield concrete acceptance criteria
and a testing strategy, it asks follow-ups. Then:

- Allocates the ID via `sync next-id task`.
- **Epic prompt:** assign to an existing epic (lists open ones), create a new epic now, or leave
  unassigned.
- **Size check:** if the work looks bigger than one PR / one sitting, propose splitting it.
- **Priority placement:** asks where the task ranks in TODO rather than always appending.
- Writes the task file from the template, runs `sync`.

### `implement-task`

Four phases, each a natural stopping point with a **STOP** between them. Carries over the analysis
doc's design.

1. **Start.** Refuse to begin if the working tree is dirty. Pick the top unblocked TODO task
   (announce any blocked ones skipped). `git fetch <remote>`, then branch from
   `<remote>/<default_branch>`. Set `status: in-progress` and `branch:`, run `sync`. **Restate the
   plan and the acceptance criteria for human approval before writing any code.** — STOP —
2. **Implement + test.** Write code and unit tests. Run `test_command` and `lint_command`. Then
   walk the task's Testing strategy; for steps that cannot be automated (real API calls, cost
   money, need credentials) **present them to the human to run and record the result** in the
   Worklog — do not silently skip. Explicit rule: **do not fix unrelated things on this branch** —
   verify with `git diff --name-only` before committing. — STOP —
3. **Wrap up.** Update `docs_paths`. Commit (conventional, referencing the task ID). If
   `rebase_before_pr`, `git fetch <remote>` and rebase onto `<remote>/<default_branch>` — on
   conflict, stop and surface it rather than guessing. Push (`--force-with-lease` if the rebase
   rewrote already-pushed history). Open the PR with `gh pr create`, acceptance criteria as a
   checklist and test results filled in. Record the returned URL in `pr:`, set
   `status: in-review`, run `sync`. **STOP here** — the human reviews and merges.
4. **Merge — observed, never performed.** A human reviews the PR on GitHub and **squash-merges**
   it. On the next invocation the skill polls `gh pr view --json state,mergeCommit`; once `MERGED`
   it records `merge_commit:` (the squash commit), sets `status: done`, runs `sync` (which
   archives the task), then deletes the task branch locally and on the remote if
   `delete_branch_after_merge`, and fast-forwards local `default_branch`. **The skill never runs
   `gh pr merge`.**

**Resumability:** on invocation the skill detects current phase from repo state — working tree
clean? branch exists (`git branch --list`)? frontmatter `status` / `pr`? `gh pr view --json
state,mergeCommit`? — and continues from there rather than restarting.

**Bail-out:** if mid-implementation the task proves wrong or underspecified, stop, write findings
into the task file, set `status` back to `todo` or `blocked`, run `sync`, surface to the user.

### `refine-backlog`

A short periodic pass, not a ceremony: confirm/reorder TODO priority, recompute blocked status
(via `sync`), surface tickets whose `created` date is old and still in `todo` as candidates for
`wont-do`, flag under-specified tickets for another `add-task`-style pass.

### `plan-feature`

Requirements gathering. Produces a **spec** in `.tasks/specs/` (problem, alternatives, non-goals),
then decomposes the feature into **vertical slices** — each independently shippable and testable —
capturing `blocked_by` / `blocks` as it goes. Groups slices under one or more **epics** linked to
the spec, then fans out to `add-task` for each slice. This is spec-driven development (cf. GitHub
spec-kit, Amazon Kiro).

---

## Guardrails

Stated explicitly for the LLM, from the analysis doc plus epic/marker additions:

- Never push *task work* to `default_branch`. Always branch from the freshly-fetched
  `<remote>/<default_branch>`. The one exception: phase 4's own bookkeeping (`merge_commit`,
  `status: done`, archiving, board/epic regeneration) may commit straight to `default_branch` —
  it records a fact about a merge a human already reviewed, not new work, and requiring a PR to
  document a PR's own merge is unbounded regress.
- **Never merge.** The skill opens the PR and stops; a human reviews and squash-merges on GitHub.
  Phase 4 only observes that merge and records it. Never run `gh pr merge`.
- Force-pushing is allowed **only** as `git push --force-with-lease` on the current task's own
  branch, immediately after a rebase onto `default_branch` — never plain `--force`, never on
  `default_branch`, never on a branch anyone else uses.
- Never touch files outside the current task's scope (`git diff --name-only` is the check).
- Never hand-edit text inside a `BEGIN:`/`END:` generated region — change the source task/epic
  file and run `sync`.
- Never hand-edit an epic's `status` except to set `wont-do`.
- Board regeneration, ID allocation, archiving, and "is this task blocked" are `sync`'s job, not
  model judgement.

---

## Success criteria (v1)

- [ ] This repo's own `.tasks/` is managed end-to-end by the toolkit.
- [ ] `sync` is idempotent — proven by unit tests, including TODO-order preservation.
- [ ] `sync check` runs in CI and fails on drift.
- [ ] A reader can produce a valid `EPIC-*.md` and `TASK-*.md` from this document alone.
- [ ] All five skills exist and reference `config.md` rather than hard-coded values.
- [ ] The epics panel in `BOARD.md` reflects derived epic status with no hand-editing.

---

## Resolved during planning

- **Archiving cadence** → runs at the end of every `sync` when `archive_done: true`. The
  sync-subcommand table already specifies this; `implement-task` phase 4 simply calls `sync`.
- **`in-review` on the board** → its own column. It maps to a real workflow state and the diff
  noise of a dedicated column is negligible.

## Open questions

- **Multiple epics per task.** Jira allows only one Epic Link; this spec follows that. Revisit if
  a task legitimately spans two bodies of work (usually a sign it should be split).

---

## Epics

The original decomposition below proposed six phase-shaped epics (data model, then `sync`, then
skills, then dogfood). That was superseded during planning: phases aren't independently shippable
slices, so all v1 work was consolidated under a single `EPIC-001: MVP` instead — see that epic's
own Goal/In scope/Out of scope. This region is TASK-007's `render_spec_epics` output, generated by
`sync` (or, until it runs standalone, kept current by hand — see `.tmp/workflow-plan.md`).

<!-- BEGIN:epics (generated by sync — do not edit) -->
| Epic | Status | Progress |
|---|---|---|
| EPIC-001 | in-progress | 6/20 done |
<!-- END:epics -->
