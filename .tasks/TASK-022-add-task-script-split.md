---
id: TASK-022
title: "add-task: move deterministic portions to a stdlib script, define its parameters"
type: refactor
status: in-review
epic: EPIC-001
created: 2026-09-13
branch: task-022-add-task-script-split
pr: https://github.com/RobotNerd/sdlc-llm/pull/32
merge_commit: null
blocked_by: []
blocks: [TASK-027]
---

# TASK-022: add-task: move deterministic portions to a stdlib script, define its parameters

## Description

Same pattern as TASK-021 (`init-project`'s scaffold script), applied to `add-task`: several of
its checklist steps are fully deterministic and shouldn't need the LLM to execute them by hand.
Move those into a stdlib-only Python script, and formalize the skill's own parameters in
`SKILL.md` so a future caller (SPEC-001 describes `plan-feature`, TASK-018, as "fanning out to
`add-task`" per slice) can pre-supply answers instead of triggering an interactive interview for
every one.

Specifically:

- **Open-epic listing** (current step 3's "read every `.tasks/EPIC-*.md`... list the ones whose
  status is not `done`/`wont-do`") — mechanical file-reading and filtering, no judgement.
- **Step 6.2 (write the task file) splits in two**: 2a is the script creating
  `.tasks/TASK-<id>-<slug>.md` from `.tasks/templates/task.md` with every frontmatter field
  mechanically filled (`id`, `type`, `epic`, `created`, `branch`, `blocked_by` — everything that
  isn't the LLM's own interview content); 2b is the LLM filling in the body's
  Description/Acceptance criteria/Testing strategy/Notes from what the interview produced. The
  file the script hands back to the LLM in 2a still has those body sections as placeholders.
- **Other deterministic steps found during implementation** — TODO placement at a requested rank
  (step 6.4, currently described as a manual cut-paste) and running `sync`/`sync check` (steps
  6.3/6.5) are strong candidates; confirm and fold in whatever else turns out mechanical once the
  script exists, same as TASK-021's own Worklog is expected to surface things.
- **Defined parameters**: `SKILL.md` gains an explicit parameter list (name, required/optional,
  default) — at minimum `description`, `type`, `epic`, `blocked_by`, `priority`. When a caller
  supplies one, the corresponding interview step is skipped rather than asked anyway; when it's
  omitted, the interview runs as it does today. This is what makes fan-out from `plan-feature`
  (not yet built) practical later without redesigning `add-task` again.

## Acceptance criteria

- [x] A stdlib-only Python script under `.claude/skills/add-task/` lists every open epic (status
      not `done`/`wont-do`, scanning `.tasks/` and `.tasks/archive/`) instead of the LLM reading
      files by hand.
- [x] The same or a sibling script provides step 2a: given an id/type/epic/branch/blocked_by (and
      today's date), writes `.tasks/TASK-<id>-<slug>.md` from the template with frontmatter (and
      both title occurrences) filled, leaving the body's Description/Acceptance
      criteria/Testing strategy/Notes as placeholders for the LLM to fill in (step 2b).
- [x] TODO placement at a requested rank (append / top / after a named task) and the
      `sync` + `sync check` calls are also done by the script, not by hand — unless
      implementation surfaces a reason one of them can't be, which gets documented rather than
      silently dropped.
- [x] `SKILL.md` documents `add-task`'s parameters explicitly (name, required/optional, default)
      — at least `description`, `type`, `epic`, `blocked_by`, `priority` — and the checklist skips
      the interview step for any parameter that's already supplied.
- [x] Unit tests (`pytest`) cover: open-epic listing against a mixed-status fixture, step 2a's
      frontmatter templating, and TODO placement for at least "append" and "after a named task".
- [x] `SKILL.md`'s remaining prose is still a numbered checklist with STOP/ASK only around
      genuinely non-deterministic steps (interview content, size-check judgement, confirmation).

## Testing strategy

1. Run the epic-listing function against a fixture with a mix of `todo`/`in-progress`/`done`/
   `wont-do` epics; confirm only open ones come back.
2. Run step 2a with sample values; confirm the frontmatter is correct, both title occurrences are
   filled, and the body sections are still placeholders for 2b.
3. Run the TODO-placement logic for "append" and "after TASK-NNN"; confirm `sync check` stays
   clean after each.
4. Run the new unit test suite (`pytest`).
5. Walk `SKILL.md`'s parameter section against a hypothetical fully-parameterized call (every
   parameter pre-supplied) and confirm no interview step would trigger.

## Worklog

- 2026-09-14: Built `.claude/skills/add-task/scaffold.py` (stdlib only) with two subcommands:
  `list-open-epics` (JSON array of `{id, title}` for epics not `done`/`wont-do`) and
  `run <answers.json>` (validates input, allocates the id, writes the task file, runs `sync`,
  repositions the TODO line if the rank isn't "end", runs `sync check`). Rather than
  re-implementing frontmatter parsing/TODO-line matching, it imports the repo's own
  `.tasks/bin/sync` by file path (same `SourceFileLoader` technique `tests/conftest.py` uses) and
  reuses `discover`, `next_id`, `load_config`, `render_value`, and the private
  `_TODO_HEADING`/`_TODO_LINE_RE` constants.
- Two implementation surprises, both fixed:
  - `sync`'s `Artifact` dataclass looks itself up via `sys.modules[cls.__module__]` at class-body
    execution time; the loader must register the module in `sys.modules` *before* calling
    `exec_module`, not after — missing this crashed every subprocess invocation with
    `AttributeError: 'NoneType' object has no attribute '__dict__'`.
  - The task template's frontmatter placeholders (`id: {{id}}`, `epic: {{epic}}`, etc.) are not
    valid frontmatter scalars — `{` is a rejected token prefix in `sync.parse_frontmatter`
    (`_BLOCK_SCALAR_PREFIXES`). Step 2a therefore can't round-trip the raw template through
    `sync`'s own parser/renderer the way originally planned; it uses plain `{{placeholder}}`
    string substitution instead (the same technique `init-project`'s `render_config` already
    uses), while still delegating `null`/list formatting for `epic`/`blocked_by` to `sync`'s own
    `render_value` so those two fields stay byte-identical to what `sync` itself would produce.
  - TODO placement (`reposition_todo_line`) also needed to filter the raw section slice down to
    lines actually matching `_TODO_LINE_RE` before reordering — the raw slice includes a trailing
    blank separator line (per `sync`'s own `apply_todo_merge` boundary logic), which without
    filtering ended up preserved mid-list after a reorder.
- TODO placement done by the script for all three ranks (`top`/`end`/`after`), by moving the exact
  line a prior bare `sync` run just appended — no hand-composed line, matching the AC.
- Rewrote `SKILL.md`: added a step 0 parameter table (`description`, `type`, `epic`, `blocked_by`,
  `priority_mode`/`priority_after`) with skip semantics; step 3 now calls `list-open-epics` instead
  of hand-reading every `EPIC-*.md` (new-epic creation stays interview-driven — out of scope per
  this task's own AC); steps 4/5 skip when pre-supplied; step 6 collapsed to "write the answers to
  JSON, run `scaffold.py run`" plus the one genuinely non-deterministic remainder (filling the
  written file's body from the interview).
- **Tests** (`tests/test_add_task_scaffold.py`, 26 new): `missing_keys`/`slugify` unit tests;
  `list_open_epics` against a hand-built mixed-status epic fixture (todo/in-progress kept,
  done/wont-do dropped); `render_task_file` (frontmatter + both title/id occurrences filled, body
  placeholders untouched, `epic: null` rendering); `reposition_todo_line` (top, after-named-task,
  end-as-noop, both not-found error paths) as pure string-manipulation tests; `run`/`list-open-epics`
  subcommands exercised as real subprocesses against a scratch repo built by `init-project`'s own
  `scaffold.py` (the same dogfooding chain the real skills use) — refusal cases (missing key,
  unknown type/epic/blocked_by/priority_mode, missing `priority_after`) and successful full runs at
  "end", "top", and "after a named task" with `sync check` staying clean after each, plus a run
  that sets both `epic` and `blocked_by`.
- Walked `SKILL.md`'s parameter table against a hypothetical fully-parameterized call
  (`description`+`type`+`epic`+`blocked_by`+`priority_mode` all supplied): steps 3/4/5 all skip,
  step 1 only needs to verify (not ask) since the description already yields concrete AC/testing
  strategy, step 2's size judgement is inherent (not parameter-skippable, by design), step 6 is a
  single script call plus the LLM filling in the body it already has from the description — no
  interview STOP/ASK would trigger.
- Full suite: `pytest` 246 passed (220 prior + 26 new); `python3 .tasks/bin/sync check` exit 0 on
  the real repo throughout.

## Notes

- No hard dependency on TASK-021 — different skill, independent code path — though implementing
  it second may reuse whatever script/testing shape TASK-021 settles on.
- Placed at the bottom of TODO, after TASK-021 — decided with the user via `add-task`'s
  priority-placement step.
- The parameter work here is what unblocks a future `plan-feature` (TASK-018) from fanning out to
  `add-task` per SPEC-001's description without redesigning this skill again.
