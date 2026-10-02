# PRD: sdlc-llm v2

- Status: draft, round 2
- Created: 2026-09-28 · Updated: 2026-10-01
- Open questions: the `PRD-v2-questions` doc, nested under this one in Outline

Items marked **[suggestion]** are new in this round. Accept, change, or cut them. Round-1
suggestions you accepted are no longer marked.

## 1. Summary

sdlc-llm is a set of agent skills for a solo developer who builds software with an LLM. The
skills plan features, write tasks, groom the backlog, review docs, and implement batches of
tasks autonomously, from branch to merge.

v1 kept the tracker inside each repo as markdown files, plus a generator script that rendered
the board. v2 moves work items and documents to self-hosted tools:

- **Kaneo** (tracker): tasks, epics, status, priority order, dependencies, worklog.
- **Outline** (doc store): specs, guideline docs, epic reports.
- **A messaging tool** (notifier, optional): a short message whenever a skill stops for the
  human.

The repo keeps only code, tests, config, and agent instructions. Skills reach every external
tool through a backend interface, so any one tool can be swapped later. They talk to the tools
through MCP first. Deterministic steps then move into stdlib Python scripts that call each
tool's REST API.

## 2. Background: what v1 taught us

| Lesson | Consequence for v2 |
|---|---|
| A markdown tracker is a lot of machinery: a 1,100-line generator, region markers, ID allocation, epic-status derivation, archiving, and hooks to stop hand-edits. | Use a real tracker. Delete everything that only exists to emulate one. |
| Done and cancelled task files pile up in the repo and go stale. | Nothing about task state is committed. |
| Committed docs cite task and spec ids, so they go stale as soon as the work ships. | Committed files never reference tracker items (§9.3). |
| The v1 `implement-task` layered two modes with contradictory rules, and a manual test failed because of that. | Build `implement-task` as one linear workflow: the batch-first design, carried forward (§10.5). |
| Scripts that were written before the workflow settled had to be rewritten. | Prose first. Move behavior into scripts in small, tested steps once the prose has settled (§14). |
| Work felt unstructured. | Guideline docs (architecture, testing, code style, task style, commit conventions) become inputs to every skill (§9.1). |
| `init-project` spent a lot of effort vendoring skills into other repos. | Install as one Claude Code plugin (§12). |

## 3. Goals

1. Kaneo is the single source of truth for work items, and Outline is the single source of
   truth for planning and guideline docs.
2. Skills use Kaneo and Outline features instead of reimplementing them.
3. Every external tool sits behind a backend interface, in the scripts and, as far as prose
   allows, in the skills (§6.1).
4. These skills keep their behavior: `add-task`, `plan-feature`, `refine-backlog`,
   `review-docs`, and `implement-task`.
5. `implement-task` runs validated batches of tasks autonomously, with a critic gating each
   merge.
6. Deterministic behavior lives in stdlib-only scripts. Each skill starts prose-only, and its
   behavior moves into scripts in small, testable steps.
7. Every STOP and ASK shows in the terminal and, if enabled, sends a short notification.
8. The critic can run outside Claude Code (§10.5).
9. The skills install together as one Claude Code plugin.
10. Committed files never reference tracker items.

## 4. Non-goals

- A repo-local tracker, generated board files, task archives, or committed specs.
- `init-project`, or any skill that copies the toolkit into a project.
- Installing skills one at a time (`npx skills`). They're designed to work as a group.
- Supporting trackers or doc stores besides Kaneo and Outline. The interfaces keep that
  possible without building it.
- Parallel task execution. One task at a time, one session.
- A PR-based review flow (deferred, §16).
- Multi-agent orchestrator and worker roles (deferred, §16). The external critic is in scope.
- Estimates, sprints, velocity, and time tracking.
- Upgrading and operating the self-hosted tools. A separate project handles that.

## 5. Users and environment

- **User:** one developer, working in one or more repos, and comfortable with a Jira-style
  epic → task hierarchy.
- **Agent:** Claude Code. Whether other host agents matter is open (Q31).
- **Network:** sessions always run on the developer's machine, which reaches the self-hosted
  tools over Tailscale. Cloud-hosted agent sessions are out of scope.
- **Self-hosted tools:** Kaneo, pinned to a Docker image tag, and Outline.
- **Runtime:** `git` and Python ≥ 3.11 (stdlib only). `gh` and Node.js aren't required.

## 6. Architecture

```
          human: Kaneo UI (board, backlog, drag to reorder) · Outline UI (docs) · phone (notifications)
                                              │
     ┌─────────────────── Kaneo ──────────────┼────────── Outline ──────────────┐   ┌── Notifier ──┐
     │ tasks · columns · relations · labels   │  docs · specs · epic reports    │   │ Signal, ntfy,│
     │ comments · REST · MCP (/api/mcp)       │  REST · MCP                     │   │ Mattermost…  │
     └───────────────▲────────────────────────┴─────────────▲───────────────────┘   └──────▲───────┘
                     │                                      │                              │
                     │            backend interfaces: Tracker · DocStore · Notifier · Critic
                     │                                      │                              │
        ┌────────────┴─────────────┐              ┌─────────┴──────────┐                  │
        │ scripts: lib/ + skills/*/ │◄── invoked ──│ SKILL.md prose     │──── notify ──────┘
        │ scripts (stdlib, REST)    │              │ (MCP while prose)  │
        └────────────┬─────────────┘              └─────────┬──────────┘
                     │ git, test/lint/format                │
                     ▼                                      ▼
     ┌──────────────────────────────── project repo ─────────────────────────────────┐
     │ code · tests · README · CLAUDE.md · .sdlc/config.toml · .env.example           │
     │ gitignored: .env · .sdlc/local/ (batch state, batch reports) · throwaway tests │
     └────────────────────────────────────────────────────────────────────────────────┘
```

Principles:

- **Each tool owns one kind of state.** Kaneo owns work items. Outline owns docs. The repo owns
  code. The only links between them are task keys in commit messages, and links between Kaneo
  and Outline (§9.3).
- **The core data model uses only features the MCP servers expose**, so prose-only skills
  never hit a wall. Only the one-time project setup needs REST or the web UI.
- **Scripts are mechanical, and prose is judgment.** This carries over from v1: JSON in and
  out, non-zero exit with a stderr message, one subcommand per deterministic step.
- **Local runtime state is gitignored.** It lives in `.sdlc/local/`.

### 6.1 Backend interfaces

Skills never call a specific tool directly. They call operations on four interfaces:

| Interface | Operations (initial) | First backend |
|---|---|---|
| Tracker | get task, list column (ordered), create task, update description, set status, archive, set position, add/remove label, add/remove relation, list relations, comment, search | Kaneo |
| DocStore | get doc, find doc by title or path, create doc (under a parent), update doc (patch), list children, search | Outline |
| Notifier | send (level, short text, link) to each enabled channel | Chosen after the analysis in §8 |
| Critic | review (task, diff, gate results, guidelines) → verdict JSON | Claude Code subagent (prose), then an API provider such as OpenRouter (scripted) |

- **In scripts:** each interface is a Python module in `lib/backends/`, with one implementation
  per tool, selected by config (`tracker.backend = "kaneo"`). Only the backend module knows an
  endpoint or a field name.
- **In prose [suggestion]:** `SKILL.md` names the abstract operation ("Tracker: set status
  `in-progress`"). One shared reference doc per backend (`lib/references/backends/kaneo.md`,
  `outline.md`) maps each operation to the MCP tool and arguments that perform it. Swapping a
  backend means swapping that reference doc. The skill prose doesn't change.

## 7. Tool evaluation and data model

### 7.1 Kaneo evaluation (round 1, unchanged)

The evaluation is desk research: the docs, the published OpenAPI spec, and the source of the
`@kaneo/mcp` package. It hasn't been tested hands-on yet; the spike in §7.4 covers that.

| Need | Kaneo feature | Fit |
|---|---|---|
| Self-hosted, open source | MIT license; Docker Compose + Postgres | Full |
| Task CRUD with a rich description | Title, markdown description, dates, assignee | Full, if markdown round-trips |
| Stable, human-readable ids | `{projectSlug}-{number}` | Full |
| Custom workflow states | Per-project columns; `isFinal` marks done states | Full |
| Hand-ordered priority | `position` within a column; drag in the UI; `update_task` accepts `position` | Full, if confirmed |
| Backlog apart from the ready queue | The built-in Planned status | Full |
| Dependencies | `blocks` relation, with the inverse shown in the UI | Partial: the batch builder enforces it |
| Epics | No native epic; `subtask` relations show "n/m complete" | Partial: modeled (§7.3) |
| Worklog and reports | Comments, plus an automatic activity log | Full |
| Agent access | HTTP MCP at `/api/mcp` (OAuth), about 36 tools | Full, with gaps: no MCP tools for custom fields, external links, columns, or bulk updates |
| Script access | REST API with a bearer API key; OpenAPI spec | Full |

**Risks:**
- API churn (very frequent releases, MCP package at 0.1.x). Mitigation: Kaneo is pinned to an
  image tag, one thin backend module, and contract tests (§13).
- No offline mode. Mitigation: a `tracker_failure` interrupt pauses the batch cleanly.
- Descriptions may not round-trip as markdown (§7.4).

### 7.2 Outline [suggestion]

Outline replaces committed specs and docs. Claude Code is already connected to its MCP server.
Its MCP tools cover what the DocStore interface needs: collections, nested docs, create, patch
updates, full-text search, comments, and templates. Scripts use Outline's REST API with an API
token.

**Structure:** one collection per project, named after the project.

```
<project>                    (collection)
├── docs                     finalized docs: guidelines, architecture, design, tutorials
│   └── guidelines           [suggestion] the docs skills read as input (§9.1)
├── spec                     specs and PRDs, one per feature
└── reports                  epic reports
```

**[suggestion] Spec titles:** the feature name only, with no `SPEC-NNN` number. Outline's URL is
the stable id, and a number would need its own allocator. The spec and its epic link to each
other.

### 7.3 Data model

**Workspace and project.** One Kaneo workspace. One Kaneo project and one Outline collection per
repo. The project's slug is the task-key prefix (`KEY-NNN`).

**Columns:**

| Column | Final | Meaning |
|---|---|---|
| *(Planned: the Backlog view)* | — | Captured or awaiting review. `implement-task` never picks from here. |
| `to-do` | no | Ready. Top to bottom is priority order. |
| `in-progress` | no | Claimed by a batch: the one task being worked on. |
| `needs-human` | no | A batch paused on this task: an interrupt, or a blocking manual test. |
| `done` | yes | Merged to the default branch. |

- **Cancelled tasks** aren't a column. They're archived, with a `wont-do` label and a comment
  giving the reason **[suggestion]**, so cancelled work stays distinguishable from finished
  work.
- **"Blocked"** is derived at read time from `blocks` relations whose blocker isn't final.

**Priority:** a task's `position` in `to-do`. The human reorders by dragging. Kaneo's
`priority` field stays unset.

**Task:** a title, plus a markdown description with fixed sections. The task style guide sets
the wording.

```markdown
## Description
## Acceptance criteria
- [ ] ...
## Testing strategy
### Automated
### Manual
## Notes
```

- **Type:** one label from `feature`, `bug`, `chore`, `refactor`, `docs`.
- **Dependencies:** `blocks` relations. The blocker is the source.
- **Worklog:** comments only. Critic verdicts, interrupts, the per-task report, and the merge
  record (commit SHA) are all comments.
- **Branch:** derived, not stored: `<branch_prefix><number>-<slug>`.

**Epic:** a Kaneo task with the `epic` label, kept in Planned. Its children are linked with
`subtask` relations. The description holds Goal, In scope, Out of scope, Success criteria, and a
link to the spec in Outline.

**Labels:** the five types, `epic`, `follow-up`, `wont-do`, and `deferred` **[suggestion]**
(for parked work, such as the multi-agent tasks, Q13).

### 7.4 Verification spike

This runs ad hoc with the developer, outside the workflow, because the workflow's own tooling
depends on its results. The agent connects to the existing Kaneo instance's MCP server and runs
each check in a sandbox project. The answers go into the architecture doc, and §7.3 changes
wherever an answer breaks it.

**Kaneo:**

1. Markdown in descriptions (headings, checklists, code, tables) round-trips through create →
   UI edit → read.
2. `position` semantics: the values the UI writes when dragging, inserting at the top or after
   a given task, and whether a status change resets `position`.
3. `subtask` relation direction, and the rollup shown in the UI.
4. Archiving a task: how it's done (an `archived` status or a separate call), whether MCP can do
   it, and whether labels survive it.
5. Claude Code connects to `/api/mcp` over OAuth. REST works with an API key.
6. Rate limits and error shapes.
7. Planned status behavior through the API.

**Outline [suggestion]:**

8. Markdown round-trip, and that a patch update leaves the rest of a doc intact.
9. Nesting and moving docs under the `docs`/`spec`/`reports` parents through MCP and REST.
10. A Kaneo URL in Outline, and an Outline URL in a Kaneo description, both render as links.

## 8. Notifications

**Requirement:** every STOP and every ASK, in every skill, always shows in the Claude Code
terminal. If notifications are enabled in config, a short version also goes to every enabled
channel. Channels sit behind the Notifier interface, so more than one can be enabled now or
added later.

**Message shape [suggestion]:** one line: project, skill, kind (STOP/ASK), a task key when
there is one, and what's needed, plus a link. For example: `sdlc-llm · implement-task · STOP ·
KEY-12: critic rejected 3×, decision needed <link>`. Messages never include code, diffs, or
secrets.

**How it's sent [suggestion]:** a small `notify` script from the start, an exception to "prose
first". Sending is purely mechanical, and calling an HTTP API from prose would put tokens in
shell commands. Every STOP and ASK in the skills calls it. The alternative is a Claude Code
`Stop` hook (Q28).

**Messaging options (preliminary; a spike decides, Q27):**

| Option | Self-hosted | Reaches the phone off Tailscale | Sending from a script | Notes |
|---|---|---|---|---|
| Signal (via `signal-cli` or `signal-cli-rest-api`) | The sender bridge is; Signal's servers aren't | Yes | Local REST call or CLI | End-to-end encrypted. Needs a second phone number for the sender. Unofficial client, so it can break when Signal changes. |
| Mattermost | Yes (server + Postgres) | The push notification usually arrives through Mattermost's hosted push proxy; opening the app needs Tailscale | Incoming webhook | Heaviest to run. Gives a searchable history and channels. |
| ntfy | Yes, or the public ntfy.sh | Only through a public server or the ntfy.sh relay | HTTP POST | Lightest option. Topics need access control. |
| Matrix (Synapse or Conduit) | Yes | Through a push gateway | HTTP API | Heavy to run. Possible two-way chat later. |
| Telegram or Discord bot | No | Yes | HTTP API | Easiest to set up. Messages sit with a third party. |

**Later [suggestion]:** two-way replies, so the human can answer an ASK from the phone. This is
out of scope for v2.

## 9. Docs and repository artifacts

### 9.1 Guideline docs

Skills read these from Outline (`docs/guidelines`), at the step that needs them. Config maps
each role to a document.

| Doc | Governs | Read by | Drafted by |
|---|---|---|---|
| Architecture | Components, boundaries, where new code goes, key decisions | `plan-feature`, `implement-task`, critic | Developer |
| Testing strategy | Test types, TDD/BDD rules, Given/When/Then, `[blocks merge]`, throwaway unit tests | `add-task`, `plan-feature`, `implement-task`, critic | Developer (migrated from the repo, with task references removed) |
| Code style | Lint and format rules, naming, comment density, sorting | `implement-task`, critic | Developer |
| Task style guide | Task structure and wording; short and plain; sizing; titles; no hard limit on criteria | `add-task`, `plan-feature`, `refine-backlog` | Agent, then the developer edits |
| Commit conventions | Conventional-commit types, the type → prefix map, how the task key appears | `implement-task` | Agent, then the developer edits |

The toolkit ships defaults for the task style guide and testing strategy as plugin references.
A project's guideline doc overrides the default.

### 9.2 What's where

| Location | Holds |
|---|---|
| Repo, committed | Code, tests, `README.md`, `CLAUDE.md`, `.sdlc/config.toml`, `.env.example`, `.gitignore` |
| Repo, gitignored | `.env`, `.sdlc/local/` (batch state, batch reports), the throwaway test directory |
| Kaneo | Tasks, epics, the worklog, per-task reports |
| Outline | Guideline docs, other finalized docs, specs, epic reports |

### 9.3 Reference rules

- **Committed files** never cite tracker items: no task keys and no legacy v1 ids, in docs,
  code comments, test names, or skill files. Commit messages are the one exception.
- **Outline `docs`** follows the same rule **[suggestion]**, because those docs are meant to
  last.
- **Outline `spec` and `reports`** may link to Kaneo items, and Kaneo items link back.
- **Enforcement:** a deterministic reference check (the project's key pattern plus the legacy
  patterns, with an allow-list for placeholders like `KEY-NNN`). It runs as an
  `implement-task` gate, inside `review-docs`, and in CI.

## 10. Skills

Every skill:

- is a numbered checklist with explicit **STOP** and **ASK** markers, each of which also sends a
  notification (§8)
- speaks in backend-interface operations (§6.1)
- loads guideline docs and references only at the step that needs them
- checks at the start that its backends are reachable, and stops if one isn't

**Interactive vs. agent-invoked:** when another skill invokes a skill with every parameter
supplied, it runs **non-interactively**. It has no STOPs or ASKs, and records anything it would
have asked as a task comment.

| Skill | Status vs. v1 |
|---|---|
| `add-task` | Kept |
| `plan-feature` | Kept; the spec goes in Outline, the epic in Kaneo |
| `refine-backlog` | Kept; slimmed |
| `review-docs` | Kept; covers repo and Outline docs; absorbs the reference check |
| `implement-task` | Replaced by the batch-first design |
| `setup-project` | New |
| `init-project`, `strip-project-references` | Dropped |

### 10.1 `add-task`

Turns a rough request into a Kaneo task.

1. **Parameters** (each one skips its interview step): description, type, epic, `blocked_by`,
   placement (`top` | `end` | `after <key>` | `planned`).
2. **Interview** until the task has objective acceptance criteria and a testing strategy.
3. **Duplicate check:** search the tracker for similar open tasks.
4. **Size check:** if it's more than one branch and one sitting, propose a split or an epic.
5. **Epic:** attach to an open epic, create one, or leave none.
6. **Dependencies and placement.**
7. **Create:** the task, its description from the template, the type label, `blocks` relations,
   a `subtask` relation from the epic, then its position. Show the key and URL.

**Human-invoked:** steps 2–6 STOP or ASK as needed.

**Agent-invoked** (by `plan-feature`, or by `implement-task` for follow-ups): no STOPs or ASKs.
- A possible duplicate is noted in a comment.
- An oversized task is created anyway and flagged in a comment.
- A task that's missing information is created with a `needs-refinement` comment
  **[suggestion]** (Q30).

### 10.2 `plan-feature`

Turns a feature idea into a spec, an epic, and vertical-slice tasks. The human reviews the tasks
after they're created.

1. **Interview** for the problem, goals, non-goals, and alternatives. Don't draft until all four
   are concrete.
2. **Architecture check:** read the architecture doc, and draft any change the feature needs.
3. **Draft the spec** in Outline (`spec/`) → **STOP** for approval of the spec and the
   architecture change. On approval, apply the architecture change in Outline.
4. **Decompose** into vertical slices, each with acceptance criteria, a testing strategy, and
   dependencies. Run the cycle check. No STOP.
5. **Create** the epic in Kaneo (linked to the spec, and the spec linked back), then invoke
   `add-task` non-interactively per slice, in dependency order. Tasks land in Planned
   **[suggestion]** (Q29).
6. **Review** → **STOP**. The human reviews and edits the created tasks in Kaneo, and marks any
   `[blocks merge]` manual tests.
7. **Release:** on approval, move the tasks to the end of `to-do` in dependency order. Show the
   URLs.

### 10.3 `refine-backlog`

A short, periodic pass. It proposes changes and waits.

1. **Blocked chains:** `to-do` tasks with outstanding blockers, and transitive chains.
2. **Blocked-order problems:** a task ranked above one of its own blockers.
3. **Stale tasks:** by active days (days with commits to the default branch since the task was
   created) over `stale_active_days`. Each one → **STOP**: archive as `wont-do`, keep, or
   re-rank.
4. **Under-specified tasks:** descriptions that break the task style guide → **STOP**:
   re-interview now, or leave flagged.
5. **Ready check:** Planned tasks that now meet the style guide → propose moving them to
   `to-do`. This includes `follow-up` tasks awaiting triage.
6. **Epic closure:** epics whose children are all final → propose closing them. Write the epic
   report if it doesn't exist yet (§10.5).
7. **Priority:** show the `to-do` order and **ASK** whether to change it.

### 10.4 `review-docs`

A periodic docs health pass over the repo docs (`README.md`, `CLAUDE.md`, skill files) and
Outline `docs`. It proposes changes and waits.

1. **Mechanical report:** repo paths cited in docs that don't exist, tracker references (§9.3),
   skill lists that don't match the plugin, and missing guideline docs.
2. **Judgment pass:** staleness, redundancy, and conflicts between guideline docs.
3. Propose each fix → **STOP** → apply only the confirmed ones → re-run the report.

### 10.5 `implement-task`

The batch-first, critic-gated, local-merge design, adapted to the new backends. It's the most
complex skill and the main automation target.

**Argument (optional, free-form):** none (the top unblocked `to-do` task), a list of keys, a
range (`KEY-A..KEY-B` in board order), a stopping task (`..KEY-B`), or an epic key. If it's
ambiguous → **ASK**.

**Steps** (the batch state records these exact names; steps 4–10 repeat per task):

| # | Step | Behavior |
|---|---|---|
| 1 | `ensure clean repo` | Clean tree (outside `ignored_paths`), except when resuming on the active task's branch. Backends reachable. `git pull --ff-only` the default branch. Any failure → **STOP**. |
| 2 | `detect interrupted batch` | No state → build. State and an argument → **ASK**: resume or discard. State and no argument → resume at the recorded step, applying the human's decision. |
| 3 | `build batch` | Resolve against `to-do` order. Validate before any work: a task doesn't exist, is final, or isn't in `to-do`; there's no stopping task; the batch is empty; a blocker is outside the batch or after the task it blocks; a range is in the wrong order. Any failure → **STOP**. Then list any `[blocks merge]` tests → **ASK** whether to proceed. Announce the order and write the state. |
| 4 | `start task` | Usage checkpoint. Branch from the default branch. Move the task to `in-progress`, comment "started", announce the plan. |
| 5 | `write tests` | Failing behavioral tests first, plus throwaway unit tests where they help. Commit. |
| 6 | `implement task` | Meet the acceptance criteria, update `docs_update_paths`, stay in scope. Out-of-scope work becomes a follow-up. Commit. |
| 7 | `run tests` | Gates: `test_command`, `lint_command`, `format_command`, and the reference check. On failure, loop back to step 6 (or step 5 if a test is wrong). |
| 8 | `spawn critic` | Usage checkpoint. Run the Critic. On rejection, comment the findings and loop back, up to `critic_rejection_attempts`. |
| 9 | `merge changes` | If the task has a `[blocks merge]` test, pause as `manual_test_required` first. Squash-merge with the conventional message, push, delete the branch and the throwaway tests. Then in the tracker: move to `done`, and comment the merge SHA. A failed tracker update after the push is retried on resume (`git log --grep <key>`). |
| 10 | `create summary report` | Per-task report as a comment. If this task was the last open child of its epic, write the epic report to Outline `reports/` **[suggestion]**. |
| 11 | `batch complete` | Write the batch report (Q24), clear the state (or keep it on a pause), and print the headline → **STOP**. |

**Critic:**

- **Checklist:** `criteria_met`, `docs_clean`, `gates_passed`, `nothing_alarming`, `scope_ok`,
  `sorted_order`, `tests_behavioral`. It answers in strict JSON. `approve` is true only if every
  item is. Anything unverifiable or malformed is a rejection.
- **Inputs:** the task, the diff, the gate results, and the architecture and code-style docs.
- **Prose phase:** a read-only Claude Code subagent on Haiku.
- **Scripted phase:** a provider-agnostic critic script behind the Critic interface, with
  OpenRouter as the first provider. It's configured by `critic.provider` and `critic.model`, and
  has the same checklist and JSON contract.
- **[suggestion] Safety for the external critic:** sending code to a third party requires an
  opt-in flag, a secret scan of the payload, and a diff-size cap that halts instead of
  truncating (Q32).

**Interrupts** pause the batch. A pause:
1. writes a worklog comment
2. moves the task to `needs-human`
3. records the interrupt in the batch state
4. writes the batch report
5. **STOP**s with the question, which sends a notification

Kinds:

- `context_usage_exceeded`
- `critic_rejection`
- `guardrail_denial`
- `infra_failure`
- `manual_test_required`
- `needs_clarification`
- `quality_gate_failure`
- `token_budget_exceeded`
- `tracker_failure`
- `unexpected_blocker`

On resume, the human picks one: resume, skip the task (its branch is deleted and it goes back to
`to-do`), or discard the batch.

**Attempt counters:** consecutive failures for the same reason, per task:
`quality_gate_attempts`, `guardrail_denial_attempts`, `critic_rejection_attempts`.

**Usage safety valve:** at `start task` and `spawn critic`, check the estimated context
percentage against `context_usage_halt_pct`, and the transcript token sum against
`token_budget_per_batch`. If the transcript can't be read, it falls back to the context estimate
alone. This reads Claude Code transcripts, so it's specific to Claude Code (Q31).

**Follow-up tasks:**
- Created through `add-task`, non-interactively.
- Labeled `follow-up`, with a `related` relation to the parent, and placed in Planned. A batch
  never picks up its own follow-ups; the human triages them.
- Capped by `autonomous_new_task_limit`. Past the cap, the follow-up is recorded as a
  recommendation in the reports.

**Bail-out:** comment the findings, move the task back to `to-do`, and pause as
`needs_clarification`.

**Batch state:** `.sdlc/local/batch-state.json`.

**Reports:**
- **Per-task comment:** summary, criteria met, tests, gates, critic rounds, manual testing steps,
  follow-ups, and notes.
- **Epic report (Outline):** the epic's goal, its tasks with their commits, follow-ups created
  and recommended, outstanding manual tests, and notes.
- **Batch report (local):** status, tasks done and not done, the early stop, follow-ups, manual
  testing, and usage.

### 10.6 `setup-project`

One-time and idempotent. It's backed by a script because creating columns needs REST.

1. Connect the repo to a Kaneo project, creating it if needed.
2. Ensure the columns and labels from §7.3 exist.
3. Ensure the Outline collection and its `docs`/`spec`/`reports` structure exist.
4. Write `.sdlc/config.toml`, `.env.example`, and the `.gitignore` entries. Ask for the
   commands, the thresholds, and the notifier settings.
5. Check each backend: MCP connections, API keys, and a test notification.

## 11. Configuration and secrets

**`.sdlc/config.toml`:** committed, TOML, and free of secrets.

| Key | Used by |
|---|---|
| `config_version` | all |
| `tracker.backend`, `kaneo.url`, `kaneo.workspace_id`, `kaneo.project_id`, `kaneo.project_slug`, `kaneo.columns` | all |
| `docs.backend`, `outline.url`, `outline.collection_id` | all |
| `guidelines.architecture`, `.testing`, `.code_style`, `.task_style`, `.commits` (Outline doc ids) | all |
| `notify.enabled`, `[[notify.channels]]` (type plus non-secret settings, per channel) | all |
| `critic.provider`, `critic.model` | `implement-task` |
| `test_command`, `lint_command`, `format_command` | `implement-task` |
| `default_branch`, `remote`, `branch_prefix`, `ignored_paths` | `implement-task` |
| `docs_update_paths` | `implement-task` |
| `docs_review_paths`, `docs_ignore_paths` | `review-docs` |
| `throwaway_test_dir` | `implement-task` |
| `reference_check.allow` | reference check |
| `autonomous_new_task_limit` | `implement-task` |
| `quality_gate_attempts`, `guardrail_denial_attempts`, `critic_rejection_attempts` | `implement-task` |
| `context_usage_halt_pct`, `token_budget_per_batch` | `implement-task` |
| `stale_active_days` | `refine-backlog` |

**Secrets:** a gitignored `.env` at the repo root. It holds `KANEO_API_KEY`,
`OUTLINE_API_KEY`, the notifier tokens, and the critic provider key. A committed `.env.example`
lists the names with empty values. Rules:

- Scripts load `.env` with a small stdlib parser. A real environment variable overrides `.env`.
- MCP connections use OAuth through Claude Code, not `.env`.
- **[suggestion]** The project's Claude Code settings deny the agent reading `.env`
  (`permissions.deny`), so secrets don't end up in the transcript. Only scripts read it (Q34).

## 12. Packaging and distribution

```
.claude-plugin/plugin.json        plugin manifest
.claude-plugin/marketplace.json   makes the repo installable as a marketplace
skills/<name>/SKILL.md
skills/<name>/references/*.md
skills/<name>/scripts/*.py
lib/                              shared code and references: the single source
lib/backends/                     Tracker, DocStore, Notifier, Critic implementations
lib/references/                   shared references: backend operation maps, default guidelines
hooks/hooks.json                  plugin hooks (later)
tests/
```

- **Install:** `/plugin marketplace add RobotNerd/sdlc-llm`, then install the plugin. Skills are
  namespaced by the plugin.
- **Shared code** lives only in `lib/`. Skill scripts import it by a path relative to their own
  file, so it works from the plugin's install directory. There's no build or copy step.
- **Dogfooding:** this repo runs its skills from the working tree (a local plugin install), so
  an edit takes effect without a release.
- **Versioning:** semver tags. The plugin manifest version tracks the tag.

### 12.1 Guardrails

- No hooks at first. Every script enforces its own preconditions.
- **Follow-up work:** plugin hooks as a backstop:
  - Deny force-pushes to the default branch.
  - Deny pushes of the default branch outside the merge step.
  - Deny hand edits to the batch state.
  - A SessionStart hook that prints the tracker's `in-progress` and `needs-human` tasks.

## 13. Testing the toolkit

This repo follows its own testing-strategy guideline: TDD, BDD, Given/When/Then, and throwaway
unit tests.

- **Behavioral script tests** drive a script's real CLI in a temp git repo against **fake
  backends**: stdlib `http.server` fakes of Kaneo and Outline, a recording notifier, and a stub
  critic. Assertions check git state, the recorded calls, and the JSON output.
- **Contract tests** run each backend module against the real tools: the pinned Kaneo image in
  Docker, and a sandbox Kaneo project and Outline collection. They sit behind a pytest marker and
  are run on demand.
- **Manual skill tests** use a scratch repo, a local bare remote, the sandbox project and
  collection, and the notifier pointed at a test channel. Each prose-only behavior has a written
  manual test, which becomes the spec for its automated replacement.
- **CI:** tests, lint, and the reference check.

## 14. Development process

1. **The developer's planning inputs:** each feature prompt states the architecture direction and
   the testing procedure. Guideline docs capture the standing rules.
2. **Prose first:** a skill ships as `SKILL.md` + references and drives the backends through MCP
   until it settles.
3. **Extraction, in small chunks:** one deterministic step per task, with behavioral tests
   written from that step's manual test. The developer decides when a step has settled; a good
   rule of thumb is two clean manual runs with no prose change in between.
4. **Extraction order:**
   1. the backend interfaces, with the Kaneo and Outline modules, plus the config and `.env`
      loader
   2. the reference check
   3. batch build and validate
   4. the merge step
   5. the reports
   6. the external critic
   7. the usage checkpoint
   8. the follow-up cap
   9. the stale and under-specified scans
   10. `add-task`'s create-and-place

   The notifier script exists from the start (§8).
5. **Task wording** follows the task style guide.

## 15. Roadmap

| Milestone | Delivers |
|---|---|
| M0: Foundations | The spike (§7.4) and the messaging analysis (§8), both run ad hoc with the developer. The Outline structure, with this PRD in `spec/`. Guideline docs in Outline: testing strategy (migrated), architecture, code style, task style guide, commit conventions. |
| M1: Restructure | The plugin layout, `lib/` with the backend interface skeletons, `.sdlc/config.toml`, `.env` handling, the notifier script, `setup-project`, and a tagged v1 snapshot. Legacy removed (§17). |
| M2: Planning skills, prose-only | `add-task` (both modes) and `plan-feature`, which are then used to load the rest of this roadmap into Kaneo. Then `refine-backlog`, `review-docs`, the reference check, and the rewritten multi-agent tasks, filed as `deferred`. |
| M3: `implement-task`, prose-only | Slices: the single-task skeleton; reports (per task, epic, batch); the Haiku critic gate; batch build and validation; interrupts and `needs-human`; resume; the usage valve; follow-ups; `[blocks merge]` pauses. |
| M4: Script extraction | The §14 order, one step per task, including the external critic. |
| M5: Hardening | Plugin hooks (§12.1). The SessionStart hook. Install docs. |

**Bootstrapping:** the current `.tasks/` backlog is frozen. Until M2, the developer tracks M0–M1
in Kaneo by hand (the UI, or ad-hoc MCP calls). From M2 on, the toolkit plans its own work.

## 16. Deferred

- Multi-agent orchestrator and worker roles, with per-role model and effort tiering. The old
  tasks are rewritten from scratch against this design and filed in Kaneo as `deferred`.
- An opt-in PR mode with CI gating.
- Two-way notifications (answering an ASK from the phone).
- Parallel batches, and multi-developer use.
- Context compaction and reset strategy beyond the usage safety valve.

## 17. Migration from v1

| v1 component | Disposition |
|---|---|
| `.tasks/` (board, epics, specs, tasks, archive, templates, config, guidelines) | Removed at M1. The implement-task-v2 tasks are dropped (M3 re-plans them). The multi-agent tasks are rewritten as `deferred` in Kaneo. Useful parts of `guidelines.md` move into the guideline docs. |
| `sync`, `guardrails.py`, `.claude/hooks/*`, `.dev/hooks/*`, and their tests | Removed. Hooks come back later (§12.1). |
| v1 `implement-task` (including `batch_select.py`) | Replaced by §10.5. `batch_select.py` is reference material for extraction. |
| `add-task`, `plan-feature`, `refine-backlog`, `review-docs` scripts | Rewritten prose-first. The old scripts are reference only. |
| `init-project`, `strip-project-references` | Removed. |
| `doc/testing-strategy.md` | Moved to Outline `docs/guidelines`, with task references removed, then deleted from the repo. |
| `doc/PRD-v2.md`, questions | Moved to Outline `spec/`. Removed from the repo after this round. |
| `README.md`, `CLAUDE.md` | Rewritten at M1. |
| CI, the PR template | CI replaced per §13. The PR template is removed. |

v1 stays reachable through a git tag.
