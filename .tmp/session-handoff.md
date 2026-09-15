# Session handoff

Written 2026-09-14, so a fresh session can resume cleanly. Skills, `guidelines.md`, and
`.tmp/workflow-plan.md` are self-documenting for the workflow mechanics — this file only holds
what isn't written down anywhere else.

## State

Nothing is in-progress; `main` is clean. This was a pure planning session — no implementation
happened. `.tasks/BOARD.md`'s epics panel: **EPIC-001 21/31 done, EPIC-002 0/7 done, EPIC-003
0/7 done**. TODO order (top to bottom) is unchanged from before this session for EPIC-001's
existing tasks (TASK-022/024/025/026/023), with everything below appended by today's planning:
TASK-027 through TASK-045.

## What happened this session

Three rounds of planning, each producing a spec + epic + tasks, all placed at the bottom of TODO
and left `todo` (nothing started):

1. **`/add-task` — the portable-surface cleanup wave.** Added TASK-027 (strip `TASK-NNN`/
   `SPEC-NNN`/`EPIC-NNN` provenance references and other project-specific content from
   `.claude/skills/**`, `blocked_by` the four remaining script-extraction tasks), TASK-028
   (`ignored_paths` config key, replacing the hardcoded `.tmp/prompts.md` exception in
   `implement-task`), TASK-029 (`init-project upgrade` — clone-based refresh of an already-
   initialized project, with a `.toolkit-manifest.json` drift-detection manifest so a locally
   modified file gets a diff+STOP instead of being silently overwritten), TASK-030 (additive
   `config.md` schema migration during upgrade — never overwrites existing values), and TASK-031
   (optional `format_command`, run by `implement-task` after rebase/before push, gated on
   TASK-024 since the formatter step belongs in that task's new script, not in prose about to be
   replaced).

2. **`/plan-feature` — EPIC-002, workflow guardrail hooks (SPEC-002).** The core finding: a
   `PreToolUse`/`Bash` hook only sees commands run as a real tool call, so once TASK-024 moves
   `implement-task`'s git/gh actions into a script, a hook watching for `git push` would never
   fire on the normal path — the model's tool call becomes `python3 .../implement-task.py`, not
   `git push` directly. Resolved by a **shared stdlib module**, `.tasks/bin/guardrails.py`
   (vendored like `sync`), that both the hooks and the skills' own scripts call — one definition,
   two enforcement points. Seven tasks (TASK-032–038): infra + shared module + core git/gh
   guardrails; structural edit guardrails (region hand-edits, epic-status hand-edits); a
   branch-name/dirty-tree gate; a pre-PR quality gate (`sync check`/test/lint/format, deny +
   report, never auto-fixes); a repo-only SPEC/TASK-reference scan (deliberately excluded from
   what `init-project`/`upgrade` copy elsewhere); a `SessionStart` board-context hook; and wiring
   all of it into `upgrade`'s manifest/config-merge. Every task blocked on the EPIC-001 work it
   needs (TASK-024/027/028/029/030/031).

3. **`/plan-feature` — EPIC-003, autonomous batch execution for `implement-task` (SPEC-003).**
   The user wants `implement-task` to work through many tasks (by epic, numeric ID range,
   explicit list, or "TODO top-to-here" stopping task) without needing to be re-invoked at every
   mechanical checkpoint. Biggest decision made here: **the user explicitly asked to change the
   standing "a human always reviews and merges" guardrail** — not remove it, but add a narrow,
   opt-in exception. Landed design: auto-merge stays off by default (`allow_auto_merge`,
   currently hardcoded `false`, becomes a real toggle); when enabled, a cheap/fast-model **critic**
   runs a narrow checklist (acceptance criteria met, scope respected, gates green — not an
   open-ended review) and must explicitly approve before `gh pr merge`; a per-batch cap forces a
   human checkpoint regardless of accumulated approvals. I recommended this scoped/capped/opt-in
   shape over an unconditional auto-merge specifically because of the user's stated token-budget
   concern (Pro plan, not unlimited) and because the repo's own `.tmp/workflow-plan.md` already
   documents *why* auto-merge was rejected once before ("defeats the purpose of opening a PR at
   all") — the user agreed with capping it. **Amended TASK-032 (EPIC-002, not yet built)** in the
   same session so its `gh pr merge` guardrail hook is designed from the start as "deny unless a
   verified marker is present," not an unconditional deny that EPIC-003 would need to redesign
   later. Seven tasks (TASK-039–045): batch selection + deterministic validation (a dedicated
   script, not a new `sync` subcommand — keeps `sync` skill-agnostic); an opt-in TDD mode
   (`tdd_enforced`, default `true`, independent of batch mode); the core loop (announce-don't-
   block plans, self-scheduled polling via `ScheduleWakeup` to resume after each merge without
   manual re-invocation); an interrupt taxonomy (4 isolated/skip-task conditions, 1 systemic/
   halt-batch — `git`/`gh` infra failure); a context/token usage safety-valve (explicitly a
   stopgap — the user flagged that real context-management strategy may need its own future
   epic, and that's deliberately out of scope here); a capped follow-up-task-creation policy
   (`autonomous_new_task_limit`, default 3, flag-and-continue past the cap); and the critic-gated
   capped auto-merge itself. Every task blocked, directly or transitively, on all seven EPIC-002
   tasks — this epic is only meant to start once EPIC-002 is fully done, per the user's explicit
   sequencing instruction.

`.tmp/workflow-plan.md` was updated to reflect all of this: the bootstrap-era "Gaps" table is now
marked historical/closed, a new "Where things stand now" section summarizes the three epics, and
two short "planned exception" notes were added inline (determinism-boundary section for the hooks
layer, the STOP/merge section for the future auto-merge exception) — both careful to describe
these as *planned*, since none of it is built yet.

## Conventions established but not yet written into any skill or doc

- **Script-extraction shape** (applies to the remaining `add-task`/`refine-backlog`/`plan-feature`
  script tasks, and now to TASK-024): follow TASK-021's `scaffold.py` + `SKILL.md` rewrite as the
  template. Confirmed answers/inputs go to the script as a JSON file (not CLI flags) when there
  are several or list-valued fields. The script is stdlib-only, never prompts interactively, and
  refuses cleanly (stderr message, non-zero exit, writes nothing) on bad input. `SKILL.md` keeps a
  cheap narrative pre-check for anything the script would refuse on so an interview isn't wasted
  on a doomed run, even though the script independently re-verifies the same thing defensively.
- **Testing a `*-script.py`**: import it in `tests/` via `SourceFileLoader` with a unique module
  name (same pattern `conftest.py` already uses for `.tasks/bin/sync`) — several skills will each
  have a similarly-named script, so a bare `import scaffold` would collide across test files.
  Prefer real subprocess + `tmp_path` integration tests over mocks for anything touching the
  filesystem or git.
- **Scratch-branch dry-run testing**: a throwaway branch off `origin/main`, deleted (never
  merged) once done. Only open a real throwaway PR on it when the task needs to prove actual
  `git`/`gh` mechanics; skip opening a PR for a file-only dry run.
- **Cross-epic `blocked_by` is normal and expected** in this system — EPIC-002 and EPIC-003 both
  block on specific EPIC-001 tasks by id, and `sync` reconciles the corresponding `blocks` fields
  automatically regardless of which epic either task belongs to.
- **Shared logic modules over duplicated logic**: when the same rule needs to be enforced from two
  different call sites (a hook at the tool boundary and a skill's own script on its normal path),
  put the rule in one stdlib module both sides import, rather than writing it twice. This is
  `.tasks/bin/guardrails.py`'s whole reason for existing (EPIC-002) and the same reasoning applies
  to any future case shaped like it.

## Open items for whoever picks this up next

- TASK-032's exact marker format (what proves a `gh pr merge` call came from EPIC-003's
  critic-gated path) is deliberately left undefined — coordinate between TASK-032 and TASK-045 if
  they're picked up in different sittings; both files' Notes point at each other.
- EPIC-003's real context-window-management strategy (beyond TASK-043's minimal safety-valve) is
  explicitly not designed yet — the user flagged it may warrant its own future spec/epic once
  EPIC-003's simpler pieces are further along.
- No open questions on anything actually planned this session — every design fork surfaced was
  resolved with the user before task files were written.
