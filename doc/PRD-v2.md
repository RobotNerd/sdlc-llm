# PRD: sdlc-llm v2

- Status: draft, for iteration
- Created: 2026-09-28
- Open questions: [questions.md](questions.md)

Items marked **[suggestion]** are additions beyond the brief. Accept, change, or cut them.

## 1. Summary

sdlc-llm is a set of agent skills for a solo developer who builds software with an LLM. The
skills plan features, write tasks, groom the backlog, review docs, and implement batches of
tasks autonomously, from branch to merge.

v1 kept the tracker inside each repo as markdown files (`.tasks/`), plus a generator script
(`sync`) that rendered the board. v2 moves all task management to a self-hosted
[Kaneo](https://kaneo.app) instance. The repo keeps only code and durable guideline docs.
Skills talk to Kaneo through its MCP server first. Deterministic steps then move into stdlib
Python scripts that call Kaneo's REST API.

## 2. Background: what v1 taught us

| Lesson | Consequence for v2 |
|---|---|
| A markdown tracker is a lot of machinery: a 1,100-line generator, region markers, ID allocation, epic-status derivation, archiving, and hooks to stop hand-edits. | Use a real tracker. Delete everything that only exists to emulate one. |
| Done and won't-do task files pile up in `.tasks/archive/` (61 files so far) and go stale. | Nothing about task state is committed to the repo. |
| Committed docs cite task and spec ids, so they go stale as soon as the work ships. | Committed files never reference tracker items (§8.3). |
| The v1 `implement-task` layered two modes with contradictory rules, and a manual test failed because of that. | Build `implement-task` as one linear workflow: the batch-first v2 design, carried forward (§9.5). |
| Scripts that were written before the workflow settled had to be rewritten. | Prose first. Move behavior into scripts in small, tested steps once the prose has settled (§13). |
| Work felt unstructured. | Human-owned guideline docs (architecture, testing, code style, task style) become inputs to every skill (§8.1). |
| `init-project` spent a lot of effort vendoring skills into other repos. | Distribute as a Claude Code plugin and through `npx skills` (§11). |

## 3. Goals

1. Kaneo is the single source of truth for work items: tasks, epics, status, priority order,
   dependencies, and the worklog.
2. Skills use Kaneo features instead of reimplementing them. The agent does only what Kaneo
   can't.
3. These skills keep their behavior: `add-task`, `plan-feature`, `refine-backlog`,
   `review-docs`, and `implement-task`.
4. `implement-task` runs validated batches of tasks autonomously. It follows the batch-first,
   critic-gated, local-merge design that was planned for v1's replacement.
5. Deterministic behavior lives in stdlib-only scripts. Each skill starts prose-only, and its
   behavior moves into scripts in small, testable steps.
6. The skills install as a Claude Code plugin, and with `npx skills` for other agents.
7. Committed files in a project never reference tracker items.
8. Project-level guideline docs drive how skills plan, write, test, and review.

## 4. Non-goals

- A repo-local tracker, generated board files, or task archives.
- `init-project`, or any skill whose job is copying the toolkit into a project.
- Supporting trackers other than Kaneo. **[suggestion]** Keep the tracker calls behind one
  client module anyway, so a second backend stays possible.
- Parallel task execution. One task at a time, one session.
- A PR-based review flow in the first release (see Q16).
- The multi-agent orchestrator/worker design and the external-provider critic. They're
  deferred (§15).
- Estimates, sprints, velocity, and time tracking, even though Kaneo supports some of them.

## 5. Users and environment

- **User:** one developer, working in one or more repos, and comfortable with a Jira-style
  epic → task hierarchy.
- **Agent:** Claude Code is the primary target. Other agents that `npx skills` supports are
  best-effort (Q9).
- **Kaneo:** self-hosted on the home network with Docker Compose and PostgreSQL. It's reachable
  only from machines on that network, so cloud-hosted agent sessions are out of scope (Q18).
- **Runtime:** `git`, Python 3 (stdlib only) and, for the stdio MCP transport, Node.js 24+.
  `gh` is no longer required.

## 6. Architecture

```
            human (Kaneo web UI: board, backlog, drag to reorder, comments)
                                      │
                                      ▼
┌─────────────────────────── Kaneo (self-hosted) ────────────────────────────┐
│  project ↔ repo · columns · tasks · relations · labels · comments · activity│
│  REST API (/api, bearer API key)          MCP server (/api/mcp, or stdio)   │
└──────────────▲────────────────────────────────────────▲─────────────────────┘
               │ deterministic calls                     │ judgment-time calls
      ┌────────┴─────────┐                      ┌────────┴────────┐
      │ skill scripts    │◄──── invoked by ─────│ SKILL.md prose  │
      │ (stdlib Python)  │                      │ (agent)         │
      └────────┬─────────┘                      └────────┬────────┘
               │ git, test/lint/format commands          │ reads
               ▼                                         ▼
┌─────────────────────────────── project repo ───────────────────────────────┐
│ code · tests · guideline docs (no tracker refs) · .sdlc/config.toml         │
│ .sdlc/local/ (gitignored: batch state, batch reports)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

Principles:

- **Kaneo owns work-item state. The repo owns code and durable knowledge.** Nothing moves
  between them except a task key in commit messages (Q6).
- **Two access paths, one data model.** Prose-only skills use the Kaneo MCP tools. Scripts use
  the REST API through one stdlib client. **[suggestion]** The core data model (§7) uses only
  features that the MCP server exposes, so prose-only skills never hit a wall. Only the
  one-time project setup needs REST or the web UI.
- **Scripts are mechanical, and prose is judgment.** This split carries over from v1: JSON in
  and out, non-zero exit with a stderr message, one subcommand per deterministic step.
- **Local runtime state is gitignored.** Batch state and batch reports live in `.sdlc/local/`.

## 7. Kaneo evaluation and data model

### 7.1 Evaluation

The evaluation is desk research: the docs, the published OpenAPI spec (`/docs/openapi.json`),
and the source of the `@kaneo/mcp` 0.1.11 package. Nothing has been tested hands-on yet, so
§7.3 lists what a spike has to confirm.

| Need | Kaneo feature | Fit |
|---|---|---|
| Self-hosted, free, open source | MIT license; Docker Compose + Postgres, or Helm; backup and upgrade docs | Full |
| Task CRUD with a rich description | Tasks with title, description, priority, dates, and assignee | Full, if markdown round-trips (§7.3) |
| Stable, human-readable ids | `{projectSlug}-{number}`, issued per project by Kaneo | Full |
| Custom workflow states | Per-project columns (name, slug, order); `isFinal` marks done states | Full |
| Hand-ordered priority | `position` orders tasks within a column; drag to reorder in the UI; `update_task` accepts `position` | Full, if confirmed (§7.3) |
| Backlog kept apart from the ready queue | The built-in **Planned** status (the Backlog view), separate from board columns | Full |
| Dependencies | `blocks` relation, with the inverse "blocked by" shown in the UI | Partial: nothing stops a blocked task from starting, so the batch builder checks |
| Epics | No native epic. The `subtask` relation shows "n/m subtasks complete". Labels work across projects. | Partial: modeled (§7.2) |
| Specs / feature docs | No document entity. Task and project descriptions are the closest fit. | Gap: modeled (§7.2, Q2) |
| Worklog, decisions, reports | Comments, plus an automatic activity log | Full |
| Task type | Workspace labels | Full |
| Link to commits | External links (REST only), GitHub/Gitea/GitLab integrations that track branches and PRs | Partial: v2 has no PRs, so the commit SHA goes in a comment |
| Agent access | Built-in Streamable HTTP MCP at `/api/mcp` (OAuth 2.1), or the `@kaneo/mcp` stdio package (device login or `KANEO_API_KEY`). About 36 tools: tasks, status, relations, labels, comments, search, and columns (read-only). | Full, with gaps below |
| Script access | REST API with a bearer API key; OpenAPI 3 spec published | Full |
| Gaps in the MCP surface | No tools for custom fields, external links, column create/reorder, bulk updates, import/export, or workflow rules | REST only; §6 keeps the core model off them |
| Search | Global search across tasks, comments, and activity | Full |
| Notify the human | Outgoing webhooks and Discord/Slack/Telegram/Mattermost on task created, status changed, and comment created | Full: used to notify on pauses **[suggestion]** |
| Export | Per-project JSON export; database backup docs | Full |

**Risks**

- **API churn.** Six releases from v2.28.1 to v2.29.2 in about two days (26–27 Sep 2026). The
  MCP package is at 0.1.x, and it has an open issue where `whoami` returns null in API-key mode.
  Mitigation: pin the Kaneo image version, keep one thin client, and run contract tests against
  the pinned version (§12).
- **Availability.** No offline mode. If Kaneo is down, planning and batches stop. Mitigation:
  a `tracker_failure` interrupt pauses the batch cleanly (§9.5).
- **Rich-text storage.** If the description editor rewrites markdown into its own format,
  agent-written sections (checklists, headings, code) may not round-trip.

**Verdict:** Kaneo meets the needs. The core workflow maps onto columns, position, relations,
labels, and comments. The real gaps are epics and specs, which are modeling choices, and
dependency enforcement, which the batch builder handles. Proceed, gated on the spike in §7.3.

### 7.2 Data model (proposed)

**Workspace and project.** One workspace. One Kaneo project per repo. The project's slug is the
task-key prefix (`KEY-NNN`). The repo's config records the project id (§10).

**Columns** (slugs are what the API stores as `status`):

| Column | Final | Meaning |
|---|---|---|
| *(Planned: the Backlog view)* | — | Captured, not ready. `implement-task` never picks from here. |
| `to-do` | no | Ready. Top to bottom is priority order. |
| `in-progress` | no | Claimed by a batch. It's the one task being worked on. |
| `needs-human` | no | **[suggestion]** A batch paused on this task: an interrupt, or a blocking manual test. Moving a task here fires Kaneo's status-change notification. |
| `done` | yes | Merged to the default branch. |
| `wont-do` | yes | Cancelled. |

v1's `blocked` status is dropped. "Blocked" is derived at read time from `blocks` relations
whose source task isn't in a final column. v1's `in-review` becomes `needs-human`, because
there are no PRs to review (Q11).

**Priority.** A task's `position` in `to-do` is its priority. The human reorders by dragging.
Kaneo's `priority` field is left unset (Q12).

**Task.** Title, plus a markdown description with fixed sections. The task style guide (§8.1)
defines their wording rules.

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
- **Worklog:** comments, never description edits. Critic verdicts, interrupts, the per-task
  report, and the merge record (commit SHA) are all comments.
- **Branch:** derived, not stored: `<branch_prefix><number>-<slug>`.

**Epic** (recommended option; alternatives in Q1). An epic is a Kaneo task with the `epic`
label that lives in Planned, so it never enters the ready queue. Its child tasks are linked with
`subtask` relations, and Kaneo shows "n/m subtasks complete" on it. Its description holds Goal,
In scope, Out of scope, Success criteria, and the spec (Q2). `refine-backlog` proposes closing an
epic once all its children are final. v1's seven-rule epic-status derivation is dropped.

**Labels** (workspace-level): the five types, `epic`, and `follow-up`.

### 7.3 Verification spike (first piece of work)

Stand up the pinned Kaneo version and confirm each item below. Record the answers in the
architecture doc, and change §7.2 wherever an answer breaks it.

1. Markdown in a description (headings, `- [ ]` checklists, fenced code, tables) round-trips
   unchanged through create → UI edit → API read.
2. `position` semantics: what values the UI writes when dragging, how to insert at the top or
   after a given task, and whether a status change resets `position`.
3. `subtask` relation direction (which side is the parent), and that the UI shows the rollup.
4. Relations across projects work, in case epics get their own project (Q1).
5. Claude Code connects to `/api/mcp`, over OAuth or with an API key header. Check the stdio
   `whoami` issue.
6. Rate limits and error shapes, for REST and MCP.
7. Task keys stay stable, and the Planned status behaves as documented through the API
   (`plannedTasks` bucket).
8. A webhook or Discord notification fires when a task moves to `needs-human`.

## 8. Repository artifacts

### 8.1 Guideline docs (human-owned inputs)

Each project keeps a small set of docs that skills read before they plan, write, implement, or
review. Config lists their paths (§10). The toolkit ships defaults as skill references, and a
project doc overrides the default.

| Doc | Governs | Read by |
|---|---|---|
| Architecture | Components, boundaries, where new code goes, key decisions | `plan-feature`, `implement-task`, critic |
| Testing strategy | Test types, TDD/BDD rules, the Given/When/Then format, `[blocks merge]`, throwaway unit tests | `add-task`, `plan-feature`, `implement-task`, critic |
| Code style | Lint and format rules, naming, comment density, sorting rules | `implement-task`, critic |
| Task style guide | Task structure, wording, acceptance-criteria rules, sizing, titles | `add-task`, `plan-feature`, `refine-backlog` |
| Commit conventions **[suggestion]** | Conventional-commit types, the type → prefix map, and how the task key appears | `implement-task` |

The human writes these docs, possibly drafted with the agent (Q17). This repo writes its own
set first (§14, M0). The current `doc/testing-strategy.md` becomes this repo's testing
strategy once its task-specific parts are removed: the implement-task-v2 references and the
closing plan section.

### 8.2 What each project's repo contains

- **Committed:** code, tests, the guideline docs, `.sdlc/config.toml`, and a `.gitignore` entry
  for `.sdlc/local/`.
- **Gitignored:** `.sdlc/local/` (batch state and batch reports) and the throwaway unit-test
  directory.
- **Nowhere in the repo:** task files, a board, epics, specs, archives, or per-task reports.

### 8.3 No tracker references in committed files

Committed files never cite tracker items: no task keys, and no legacy `TASK-`/`EPIC-`/`SPEC-`
ids. That covers docs, code comments, test names, and skill files.

- **Allowed:** commit messages, and nothing else (Q6).
- **Enforced by:** a deterministic reference check (the project's key pattern plus the legacy
  patterns, with an allow-list for placeholders like `KEY-NNN`). It runs as an `implement-task`
  quality gate, inside `review-docs`, and in CI. This replaces v1's `strip-project-references`
  skill and its portable-surface hook.

## 9. Skills

Every skill:

- is a numbered checklist with explicit **STOP** (wait for the human) and **ASK** (don't
  guess) markers
- loads guideline docs and `references/` only at the step that needs them
- reads the Kaneo project from config and fails fast if Kaneo is unreachable
- starts prose-only against the MCP tools, then moves steps into `scripts/` (§13)

Skill set:

| Skill | Status vs. v1 |
|---|---|
| `add-task` | Kept; Kaneo backend |
| `plan-feature` | Kept; the epic and spec live in Kaneo |
| `refine-backlog` | Kept; slimmed, since Kaneo handles ordering and board state |
| `review-docs` | Kept; absorbs the tracker-reference check, drops the guidelines-mirror check |
| `implement-task` | Replaced by the batch-first design |
| `init-project` | Dropped (§11) |
| `strip-project-references` | Dropped; folded into the reference check (§8.3) |
| `setup-project` | **[suggestion]** New: one-time Kaneo project setup (Q10) |

### 9.1 `add-task`

Turns a rough request into a ready Kaneo task.

1. **Parameters** (each one skips its interview step): description, type, epic, `blocked_by`
   (task keys), placement (`top` | `end` | `after <key>` | `planned`). `plan-feature` and
   `implement-task`'s follow-ups pass all of them.
2. **Interview** until the task has objective acceptance criteria and a testing strategy in the
   testing-strategy format. Nothing is created before then.
3. **Duplicate check [suggestion]:** search Kaneo for similar open tasks and show any matches.
4. **Size check:** if it's more than one branch and one sitting, propose a split, or promote it
   to an epic → **STOP**.
5. **Epic:** attach to an open epic (listed from Kaneo), create one, or leave none → **STOP**.
6. **Dependencies and placement:** **ASK** unless supplied.
7. **Create:** the task in the right column, the description rendered from the template, the
   type label, `blocks` relations from each blocker, a `subtask` relation from the epic, then
   `position`. Show the key and URL.

### 9.2 `plan-feature`

Turns a feature idea into a spec, an epic, and vertical-slice tasks.

1. **Interview** for the problem, goals, non-goals, and alternatives considered. Don't draft
   until all four are concrete.
2. **Architecture check [suggestion]:** read the architecture doc. If the feature changes it,
   draft the doc edit (with no tracker references) for the human to commit.
3. **Draft the spec** → **STOP** for approval.
4. **Decompose** into vertical slices. Each slice gets acceptance criteria and a testing
   strategy in the testing-strategy format, plus its dependencies between slices. Run the cycle
   check.
5. **Review** the epic(s), slices, and dependency graph → **STOP**. At this stop the human also
   marks any `[blocks merge]` manual tests.
6. **Create** the epic(s) in Kaneo, then fan out to `add-task` per slice in dependency order,
   with every answer pre-supplied.
7. **Confirm:** every slice exists, is linked to its epic, and has the right `blocks` relations.
   Show the URLs.

### 9.3 `refine-backlog`

A short, periodic pass. It proposes changes and waits.

1. **Blocked chains:** `to-do` tasks with outstanding blockers, and transitive chains.
2. **Blocked-order problems [suggestion]:** a task ranked above one of its own blockers in
   `to-do`.
3. **Stale tasks:** by active-days-elapsed (days with commits to the default branch since the
   task was created), not calendar age. Each one → **STOP**: `wont-do`, keep, or re-rank.
4. **Under-specified tasks:** descriptions that break the task style guide (missing sections,
   no testing strategy, subjective criteria). Each one → **STOP**: re-interview now with
   `add-task`, or leave it flagged.
5. **Ready check [suggestion]:** Planned tasks that now meet the style guide → propose moving
   them to `to-do`.
6. **Epic closure:** epics whose children are all final → propose `done` or `wont-do`.
7. **Priority:** show the `to-do` order and **ASK** whether to change it. The human usually
   drags cards in Kaneo. The skill applies an order only when the human dictates one.

### 9.4 `review-docs`

A periodic docs health pass. It proposes changes and waits.

1. **Mechanical report:** dangling path references, tracker references (§8.3), claimed file or
   skill lists that don't match the repo, and missing guideline docs.
2. **Judgment pass:** staleness, redundancy, and conflicts between guideline docs.
3. Propose each fix → **STOP** → apply only the confirmed ones → re-run the report.

### 9.5 `implement-task`

The batch-first design planned for v1's replacement, adapted to Kaneo. It's the most complex
skill and the main automation target. Differences from that design:

- Task state lives in Kaneo, so there are no bookkeeping commits and no `sync` gate.
- `gh` isn't required.
- The ready queue is Kaneo's `to-do` column in `position` order.
- Per-task reports are comments on the Kaneo task.

**Argument (optional, free-form):** none (the top unblocked `to-do` task), a list of keys, a
range (`KEY-A..KEY-B` in board order), a stopping task (`..KEY-B`), or an epic key. If it's
ambiguous → **ASK**.

**Steps** (the batch state records these exact names; steps 4–10 repeat per task):

| # | Step | Behavior |
|---|---|---|
| 1 | `ensure clean repo` | Clean tree (outside `ignored_paths`), except when resuming on the active task's branch. Kaneo reachable. `git pull --ff-only` the default branch. Any failure → **STOP**. |
| 2 | `detect interrupted batch` | No state → build. State and an argument → **ASK**: resume or discard. State and no argument → resume at the recorded step, applying the human's decision on the interrupt. |
| 3 | `build batch` | Resolve against `to-do` order. Validate before any work: a task doesn't exist, is final, or isn't in `to-do`; there's no stopping task; the batch is empty; a blocker is outside the batch or ordered after the task it blocks; a range is in the wrong order. Any failure → **STOP**. Then list any `[blocks merge]` tests in the batch → **ASK** whether to proceed. Announce the order and write the batch state. |
| 4 | `start task` | Usage checkpoint. Branch from the default branch. Move the task to `in-progress`, add a "started" comment, and announce the plan. |
| 5 | `write tests` | Failing behavioral tests first (the testing strategy), plus throwaway unit tests where they help. Commit. |
| 6 | `implement task` | Meet the acceptance criteria, update `docs_update_paths`, stay in scope. Out-of-scope work becomes a follow-up. Commit. |
| 7 | `run tests` | Gates: `test_command`, `lint_command`, `format_command`, and the reference check. On failure, loop back to step 6 (or step 5 if a test is wrong). Collect manual steps for the report. |
| 8 | `spawn critic` | Usage checkpoint. A read-only critic subagent on a cheap model answers a fixed boolean checklist in strict JSON and fails closed. On rejection, record the findings as a comment and loop back, up to `critic_rejection_attempts`. |
| 9 | `merge changes` | If the task has a `[blocks merge]` test, pause as `manual_test_required` first. Then: squash-merge into the default branch with the conventional message, push, delete the branch, delete the throwaway tests. Then in Kaneo: move to `done` and add a merge comment with the SHA. If the Kaneo update fails after the push, it's retried on resume (`git log --grep <key>` shows the merge already happened). |
| 10 | `create summary report` | Per-task report as a Kaneo comment. |
| 11 | `batch complete` | Write the batch report (Q4), clear the state (or keep it on a pause), print the headline → **STOP**. |

**Critic checklist:** `criteria_met`, `docs_clean`, `gates_passed`, `nothing_alarming`,
`scope_ok`, `sorted_order`, `tests_behavioral`. `approve` is true only when every item is.
Anything unverifiable, unparseable, missing, or inconsistent is a rejection. The code-style and
architecture docs are part of the critic's input **[suggestion]**.

**Interrupts** pause the batch. The pause writes a Worklog comment, moves the task to
`needs-human` (so Kaneo notifies the human), records the interrupt in the batch state, writes
the batch report, and **STOP**s with the question. Kinds:

- `context_usage_exceeded`
- `critic_rejection`
- `guardrail_denial`
- `infra_failure` (git or remote)
- `manual_test_required`
- `needs_clarification`
- `quality_gate_failure`
- `token_budget_exceeded`
- `tracker_failure` (Kaneo unreachable or erroring) **[suggestion]**
- `unexpected_blocker`

On resume, the human picks one: **resume**, **skip the task** (its branch is deleted and it goes
back to `to-do`), or **discard the batch**.

**Attempt counters** count consecutive failures for the same reason, per task:
`quality_gate_attempts`, `guardrail_denial_attempts`, `critic_rejection_attempts`.

**Usage safety valve:** at `start task` and `spawn critic`, check the estimated context
percentage against `context_usage_halt_pct`, and the transcript token sum against
`token_budget_per_batch`. If the transcript can't be read, the check degrades to the context
estimate alone and never raises an interrupt by itself.

**Follow-up tasks:** created autonomously through `add-task` with every answer pre-supplied,
labeled `follow-up`, with a `related` relation to the parent, and placed in Planned
**[suggestion]** (not at the end of `to-do`; Q5). The cap is `autonomous_new_task_limit`. Past
the cap, the follow-up is recorded as a recommendation in the reports. Neither case is an
interrupt.

**Bail-out:** if a task is wrong or underspecified, comment the findings, move it back to
`to-do`, and pause the batch as `needs_clarification`.

**Batch state:** `.sdlc/local/batch-state.json`, holding the version, argument, order, active
task, step, interrupt, per-task status, attempts, critic rounds, follow-ups, and start time. The
active task is also visible in Kaneo as the one `in-progress` or `needs-human` task.

**Reports:**

- The per-task comment covers: summary, acceptance criteria met, tests added, gates, critic
  rounds, manual testing steps in the testing-strategy format, follow-ups, and notes.
- The batch report covers: status, tasks implemented and not implemented, the early stop,
  follow-ups created and recommended, manual testing, and usage.
- Every section is printed even when empty.

### 9.6 `setup-project` [suggestion]

One-time and idempotent:

1. Connect the repo to a Kaneo project, creating it if needed.
2. Ensure the columns and labels from §7.2 exist.
3. Write `.sdlc/config.toml` (asking for the commands and thresholds) and the `.gitignore` entry.
4. Check the MCP connection and the API key.

It needs REST for the columns, so its setup steps are the first script-backed piece. Without
this skill, the same steps become a setup doc (Q10).

## 10. Configuration

`.sdlc/config.toml` is committed and holds no secrets (format: Q7). The API key comes from the
`KANEO_API_KEY` environment variable. The MCP server connection is configured at user scope in
the agent's own settings.

| Key | Carried from v1? | Used by |
|---|---|---|
| `kaneo.url`, `kaneo.workspace_id`, `kaneo.project_id`, `kaneo.project_slug` | new | all |
| `kaneo.columns` (role → column slug map) | new | all |
| `guidelines.architecture`, `.testing`, `.code_style`, `.task_style`, `.commits` | new | all |
| `test_command`, `lint_command`, `format_command` | yes | `implement-task` |
| `default_branch`, `remote`, `branch_prefix` | yes | `implement-task` |
| `ignored_paths` | yes | `implement-task` |
| `docs_update_paths` (was `docs_paths`) | renamed | `implement-task` |
| `docs_review_paths`, `docs_ignore_paths` | yes | `review-docs` |
| `throwaway_test_dir` | new | `implement-task` |
| `reference_check.allow` | new | reference check |
| `autonomous_new_task_limit` | yes | `implement-task` |
| `quality_gate_attempts`, `guardrail_denial_attempts`, `critic_rejection_attempts` | yes | `implement-task` |
| `context_usage_halt_pct`, `token_budget_per_batch` | yes | `implement-task` |
| `stale_active_days` | new (was a constant) | `refine-backlog` |

Dropped: `workflow_version` (replaced by a `config_version`), `allow_auto_merge`,
`autonomous_merge_cap`, `archive_done`, `ci_checks`, `delete_branch_after_merge`,
`merge_strategy`, `rebase_before_pr`, `tdd_enforced`.

## 11. Packaging and distribution

**Repo layout [suggestion]:**

```
skills/<name>/SKILL.md
skills/<name>/references/*.md
skills/<name>/scripts/*.py
skills/<name>/scripts/_shared/      # generated copy of lib/
lib/                                # single source for shared script code and shared references
.claude-plugin/plugin.json          # Claude Code plugin manifest
.claude-plugin/marketplace.json     # makes the repo installable as a marketplace
hooks/hooks.json                    # optional plugin hooks (§11.1)
tests/
doc/
```

- **Claude Code:** `/plugin marketplace add RobotNerd/sdlc-llm`, then install the plugin. Skills
  are namespaced by the plugin.
- **Other agents:** `npx skills add RobotNerd/sdlc-llm`. It finds `skills/*/SKILL.md` and reads
  `.claude-plugin/` manifests. It installs per skill, at project or global scope.
- **Shared code:** `npx skills` installs skills one at a time, so each skill must be
  self-contained. Shared script code (the Kaneo client, config loader, git helpers) and shared
  references (the default task style guide and testing strategy) live once in `lib/`. A build
  script copies them into each skill, and CI fails if a copy drifts (Q8).
- **Scripts** find their files relative to their own location, never the project's
  `.claude/` directory.
- **Dogfooding:** this repo runs its own skills from the working tree (a local plugin install,
  or symlinks from `.claude/skills/`), so an edit takes effect without a release.
- **Versioning [suggestion]:** semver tags. The plugin manifest version tracks the tag.

### 11.1 Guardrails

v1's hook guardrails mostly protected the markdown tracker, so they go with it. v2's rule:
**every script enforces its own preconditions**, because `npx skills` installs can't ship hooks.
Optional plugin hooks are a backstop only. Candidates, to be rebuilt later (Q15):

- Deny `git push --force` to the default branch.
- Deny `git push` of the default branch outside `implement-task`'s merge step.
- Deny edits to `.sdlc/local/batch-state.json` outside scripts.
- A SessionStart hook that prints the Kaneo tasks that are `in-progress` or `needs-human`
  **[suggestion]**: the replacement for v1's board-context hook.

## 12. Testing the toolkit

This repo follows its own testing-strategy guideline (TDD, BDD, Given/When/Then, throwaway unit
tests). Toolkit-specific rules:

- **Behavioral script tests** drive a script's real CLI in a temp git repo against a **fake
  Kaneo**: a stdlib `http.server` that implements the endpoints the client uses and records
  requests. Assertions check git state, the recorded Kaneo calls, and the JSON output.
- **Contract tests [suggestion]** run the same Kaneo client against the pinned Kaneo version in
  Docker. They're behind a pytest marker, run in a CI job, and are rerun before any Kaneo
  upgrade. They catch API churn (§7.1) before it breaks a batch.
- **Manual skill tests** use a scratch repo, a local bare remote, and a sandbox Kaneo project.
  Each prose-only behavior has a written manual test, which becomes the spec for its automated
  replacement.
- **CI:** tests, lint, the reference check, and the shared-copy drift check. v1's `sync check`
  job is removed.

## 13. Development process

1. **The human's planning inputs:** each feature prompt states the architecture direction and
   the testing procedure. The guideline docs capture the standing rules, so prompts don't have
   to repeat them.
2. **Prose first:** a skill ships as `SKILL.md` + `references/`, driving Kaneo through MCP, and
   is manually tested until it settles.
3. **Extraction, in small chunks:** one deterministic step per task. Each task gets behavioral
   tests written from that step's manual test. **[suggestion]** A step is ready to extract once
   it has passed its manual test in at least two runs with no prose change in between.
4. **Extraction order (proposed):** the Kaneo client and config loader, the reference check,
   `implement-task`'s batch build/validate, the merge step, the reports, the usage checkpoint,
   the follow-up cap, the stale and under-specified scans, and `add-task`'s create-and-place.
5. **Task wording** follows the task style guide, which the agent reads before it writes any
   task.

## 14. Roadmap

| Milestone | Delivers |
|---|---|
| M0: Foundations | Kaneo stood up and pinned. The §7.3 spike. This repo's guideline docs: architecture, testing strategy without task references, code style, task style guide, commit conventions. |
| M1: Restructure | The `skills/` + `lib/` + `.claude-plugin/` layout, `.sdlc/config.toml`, and a tagged v1 snapshot. Legacy removed (§16). |
| M2: Planning skills, prose-only | `add-task` and `plan-feature` on MCP (then used to load the rest of this roadmap into Kaneo), `refine-backlog`, `review-docs`, and the reference check. |
| M3: `implement-task`, prose-only | Slices: the single-task skeleton; reports; the critic gate; batch build and validation; interrupts and `needs-human`; resume; the usage valve; follow-ups; `[blocks merge]` pauses. |
| M4: Script extraction | The §13 order, one step per task. |
| M5: Hardening and distribution | Plugin hooks (§11.1), the SessionStart context hook, marketplace and `npx skills` install checks, and install docs. |

**Bootstrapping:** the current `.tasks/` backlog is frozen now. Until M2 lands, the human tracks
M0–M1 in Kaneo by hand (the UI, or ad-hoc MCP calls). From M2 onward, the toolkit plans its own
work.

## 15. Deferred

- Multi-agent orchestrator/worker roles, per-role model and effort tiering, an external
  (OpenRouter) critic with budget guardrails, and a scope-fence hook (Q14).
- An opt-in PR mode with CI gating and Kaneo's GitHub integration (Q16).
- Parallel batches, and multi-developer use.
- Context compaction and reset strategy beyond the usage safety valve.

## 16. Migration from v1

| v1 component | Disposition |
|---|---|
| `.tasks/` (board, epics, specs, tasks, archive, templates, config, guidelines) | Removed. The open backlog is handled per Q13. `guidelines.md` content moves into the guideline docs. |
| `.tasks/bin/sync` and its tests | Removed. Kaneo does ID allocation, board rendering, ordering, and relations. The batch builder derives "blocked". |
| `.tasks/bin/guardrails.py`, `.claude/hooks/*`, `.dev/hooks/*` and their tests | Removed. A subset is rebuilt per §11.1. |
| v1 `implement-task` (4 phases, PR flow, batch mode, auto-merge marker, `batch_select.py`) | Replaced by §9.5. `batch_select.py` is reference material for the batch-build extraction. |
| `add-task`, `plan-feature`, `refine-backlog`, `review-docs` and their `scaffold.py` | Rewritten prose-first against Kaneo. The old scripts are reference only. |
| `init-project` (scaffold, upgrade, `--target`, migrate-config, vendored copies) | Removed. |
| `strip-project-references` | Removed; replaced by the reference check. |
| `doc/testing-strategy.md` | Kept. Task references and the plan section are removed. |
| `README.md`, `CLAUDE.md` | Rewritten for v2 at M1. |
| CI (`sync-check`, `test`) | Replaced per §12. |
| GitHub PR template | Removed (no PR flow). |

v1 stays reachable through a git tag. Nothing is kept on `main` "just in case".
