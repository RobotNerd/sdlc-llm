# Project management workflow — analysis & recommendations

Feedback on the LLM-driven, "kanban in markdown" PM workflow being prototyped in this
repo (`.tasks/`), with the goal of abstracting it into a reusable global workflow for
self-contained, solo-developer projects.

## Overall assessment

The process is sound. It maps cleanly onto a normal product-management lifecycle, and
"kanban in markdown" is the right substrate for a solo, single-repo project — no external
service, state lives with the code, diffable in PRs.

The gaps are in three areas:

1. **State consistency** — keeping `BOARD.md` and the individual `TASK-*.md` files in sync
   is the primary failure mode when an LLM is doing the editing.
2. **Checkpoints in the implement flow** — the "implement a ticket" skill as described does
   too much in one uninterrupted run, including auto-merge to `main`.
3. **Structuring for reuse** — generic skill logic needs to be separated from per-project
   configuration for the global-workflow goal to work.

---

## Data model changes (do these first — everything else depends on them)

### 1. Add YAML frontmatter to every `TASK-*.md`

Prose fields are fine for humans, but the skills need machine-readable state. Example:

```yaml
---
id: TASK-011
title: Use API to request current weather
type: feature
status: todo          # todo | in-progress | blocked | in-review | done | wont-do
created: 2026-08-27
branch: task-011-weather-api
pr: null
blocked_by: [TASK-008]
blocks: [TASK-012]
---
```

This eliminates the biggest weakness of markdown kanban with an LLM: `BOARD.md` and the
task files drifting apart. Currently "Blocked by TASK-008" lives in free-text
"Additional notes", where the model cannot reliably act on it.

### 2. One source of truth for status; make the board partly derived

Recommended split:

- **Task-file frontmatter owns `status`.**
- **`BOARD.md` owns priority order** within TODO — a total ordering the model cannot infer,
  and the one thing a human must maintain by hand.
- Provide a small **deterministic `sync` script/skill** that regenerates every section of
  `BOARD.md` *except* the TODO ordering, from the task files.

Do not rely on the LLM to hand-edit two files transactionally; it will eventually leave
them inconsistent.

### 3. Define how Done gets archived

`BOARD.md` and `.tasks/` grow without bound otherwise. Move `done` / `wont-do` task files
to `.tasks/archive/` and keep only a one-line reference (or a link to the merged PR) on
the board. Perform this in the same `sync` step.

### 4. Define the ID allocation rule

"Max existing ID across `.tasks/` and `.tasks/archive/`, plus 1." State it explicitly in
the add-ticket skill, or IDs will collide after archiving.

### 5. Traceability convention

This is what you'd otherwise lose by not using Jira. Lock in:

- Branch: `task-011-short-slug`
- Commit messages reference `TASK-011`
- PR title references `TASK-011`
- Task file records the PR URL and the merge commit

Result: bidirectional links between ticket, branch, commits, and PR — all reconstructable
from the repo.

---

## Per-skill feedback

### init

Good as scoped. Have it write:

- `guidelines.md` (with a `workflow_version` field so projects can be upgraded later)
- empty `BOARD.md`
- `.github/pull_request_template.md` that mirrors the acceptance-criteria checklist
- a **project config file** (see "Structuring for reuse" below)

### add ticket

The skill should **interview, not transcribe**. If the user's description doesn't yield
concrete acceptance criteria and a testing strategy, it asks follow-up questions. It
should place the ticket into the TODO order ("where does this rank?") rather than always
appending. Add a size check: if the ticket looks bigger than one PR / one sitting, split
it.

### backlog refinement

Keep it, keep it lightweight. Its jobs:

- Confirm / reorder TODO priority
- Recompute blocked status from `blocked_by`
- Flag stale or now-irrelevant tickets for → `wont-do`
- Flag under-specified tickets that need another add-ticket-style pass

For a solo developer this is a short periodic pass, not a heavy ceremony.

### implement a ticket

This does far too much for one skill. Break it into checkpointed phases, each a natural
stopping point:

1. **Start** — pick the top unblocked TODO ticket (announce any skipped blocked ones),
   create the branch, set `status: in-progress`, then **restate the plan for human
   approval before writing code**. Catches underspecified tickets cheaply.
2. **Implement + test** — code, unit tests, then run the ticket's testing strategy. Some
   testing-strategy steps aren't automatable (real API calls, cost money, need
   credentials) — the skill should **present those to the human to run** and record the
   result, not silently skip them. Explicit rule: **do not fix unrelated things on this
   branch** (scope creep is the classic LLM failure here).
3. **Wrap up** — update docs, commit (conventional commit + `TASK-011`), push, open the PR
   with the acceptance criteria as a checklist and test results filled in. **Stop here.**
4. **Merge** — a separate action with a separate human go-ahead, gated on CI green. Even
   solo, auto-merging past your own PR review defeats the purpose of opening one.

Also give it an explicit **bail-out path**: if mid-implementation the ticket turns out to
be wrong or underspecified, stop, write findings into the task file, move it back to TODO
or Blocked, and surface to the user.

Make it **resumable**: on invocation, detect "TASK-011 is in-progress, branch exists, no
PR yet" and continue from the correct phase rather than starting over. That state is
recoverable from the repo (branch existence, frontmatter, `gh pr view`) if designed for.

### requirements gathering

The hard part is decomposition. Add an intermediate artifact: a short spec / mini-PRD per
feature in `.tasks/specs/` (the "why", alternatives considered, non-goals). Tickets link
back to it and stay small ("what/how"). Decompose into **vertical slices** — each
independently shippable and testable — capturing `blocked_by` / `blocks` as you go, then
fan out to the add-ticket skill.

This is essentially **spec-driven development** (cf. GitHub spec-kit, Amazon Kiro), which
is the current best-practice pattern for LLM feature work and a good fit here.

---

## Structuring for reuse (the actual goal)

Split **generic skill logic** from **per-project config**. Have `init` create a
`.tasks/config.md` (or frontmatter in `guidelines.md`) that the global skills read:

```yaml
test_command: pytest
lint_command: ruff check .
docs_paths: [README.md, docs/]
default_branch: main
branch_prefix: task-
allow_auto_merge: false
ci_checks: [build, test]
```

The skills stay identical across projects; only this file changes. Version it alongside
`workflow_version` so an `upgrade` path can be written later.

---

## LLM-specific practices worth baking in

- **Plan-then-act with a human checkpoint** before any code is written.
- **Skills as explicit checklists with STOP markers** and "if X is ambiguous, ASK" rules —
  not prose descriptions of intent.
- **Determinism wherever possible**: board regeneration, ID allocation, archiving, and
  "is this ticket blocked" should be scripts, not model judgment.
- **Guardrails, stated explicitly**: never push to `main`, never force-push, always branch
  from latest `main`, never merge with red CI, never touch files outside ticket scope.
- **Worklog**: append a short decisions/deviations log to the task file during
  implementation. Helps PR review and helps a resumed session.

---

## What to cut / not build

- **`Type` field** — keep only if it changes skill behavior. Otherwise drop it, or expand
  to something useful (feature / bug / chore / refactor / docs).
- **Metrics / retro / cycle-time** — out of scope for solo; derivable from git later if
  ever wanted. Don't build it now.
- **Separate "Blocked" board section** — with `blocked_by` in frontmatter and a sync step,
  blocked tickets can render under TODO with a marker. One less place to keep in sync.
  (Minor — current sections are also fine.)
- **Terminology** — pick "task" or "ticket" and use it everywhere. `guidelines.md`
  currently mixes both.

---

## Suggested sequencing

1. Lock the data model: frontmatter schema, board-sync rule, archiving rule.
2. Write the `sync` script and the `config.md` schema.
3. Write skills in this order: `init` → `add ticket` → `implement a ticket` (phased) →
   `backlog refinement` → `requirements gathering`.
4. Dogfood on this repo, then extract skills + templates into the standalone workflow repo.

### Artifacts to produce

- Revised `guidelines.md` (with `workflow_version`)
- `TASK-*.md` template with frontmatter
- `.tasks/config.md` schema
- `sync` script (board regeneration + archiving)
- `.github/pull_request_template.md`
