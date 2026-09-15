---
id: TASK-026
title: "plan-feature: move mechanical file-writing and cycle checking to a stdlib script"
type: refactor
status: in-progress
epic: EPIC-001
created: 2026-09-14
branch: task-026-plan-feature-script-split
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-027]
---

# TASK-026: plan-feature: move mechanical file-writing and cycle checking to a stdlib script

## Description

Same pattern as TASK-021/022/024/025, applied to `plan-feature` (TASK-018): move its
deterministic steps into a stdlib-only Python script — allocating spec/epic ids
(`sync next-id spec`/`epic`), writing `SPEC-*.md`/`EPIC-*.md` from their templates given
already-decided content, running `sync`/`sync check`, and confirming the new epic appears in the
board `epics` panel and its `children` region. Also replaces the "eyeball it for cycles" step
(a placeholder for not having tooling yet, per `SKILL.md`'s own wording) with a real cycle check
over the proposed `blocked_by`/`blocks` graph among the new slices, run before the
restate-and-confirm STOP.

What stays as LLM/human judgment, unchanged: the interview (problem/goals/non-goals/alternatives),
the vertical-slice decomposition itself (what the slices are, where the real dependencies are),
and both STOP checkpoints (spec draft, and the full decomposition before task creation). The
script only writes what's already been decided and validates it.

## Acceptance criteria

- [x] A stdlib-only Python script under `.claude/skills/plan-feature/` allocates spec/epic ids and
      writes `SPEC-*.md`/`EPIC-*.md` from their templates given filled-in content (Problem/
      Goals/Non-goals/Alternatives for the spec; Goal/In scope/Out of scope/Success criteria for
      each epic, with `spec:` set).
- [x] The same or a sibling script runs `sync` and `sync check`, and reports whether the new
      epic(s) appear correctly in `BOARD.md`'s `epics` panel and their own `children` region.
- [x] The script provides a real cycle check over a proposed `blocked_by`/`blocks` graph (a list
      of slices with their proposed dependencies) and reports any cycle found, replacing
      `SKILL.md`'s "eyeball it" step.
- [x] `SKILL.md` is rewritten so its own prose covers only the interview, the decomposition
      judgment, and the two STOP checkpoints — each backed by one script invocation for the
      mechanical file-writing/validation part.
- [x] Unit tests (`pytest`) cover: the cycle check against both an acyclic and a genuinely cyclic
      fixture graph, and spec/epic file templating given sample content.

## Testing strategy

1. Unit-test the cycle check against a small acyclic fixture graph and a deliberately cyclic one
   (e.g. A blocks B blocks C blocks A); confirm it correctly passes the first and flags the
   second with which edge closes the cycle.
2. Unit-test spec/epic templating against sample content; confirm the leading template comment is
   dropped and every placeholder is filled.
3. Dry-run the full script against a scratch feature (same throwaway-branch approach as TASK-018
   itself used) — confirm the same outcome TASK-018 already proved by hand.
4. Re-read `SKILL.md` and confirm its remaining prose is interview/decomposition/STOP-checkpoint
   only, with one script call per mechanical step it used to describe as prose.

## Worklog

- 2026-09-15: Built `.claude/skills/plan-feature/scaffold.py` (stdlib only), four subcommands:
  `check-cycles`, `write-spec`, `write-epics` (one call for a batch of epics — allocates ids
  sequentially so they never collide), `finish`. Imports the repo's own `.tasks/bin/sync` by file
  path (same technique TASK-022/024/025 used) for `next_id`.
- **Templating**: `spec.md`/`epic.md`'s raw frontmatter placeholders (`id: {{id}}`, `spec:
  {{spec}}`, etc.) aren't valid frontmatter scalars — same `{`-prefix issue TASK-022 hit — so
  `render_spec_file`/`render_epic_file` use plain `{{placeholder}}` string substitution rather
  than a round trip through `sync`'s parser/renderer. One real wrinkle specific to this template:
  `epic.md` reuses the *same* placeholder name (`{{item}}`) for both "In scope" and "Out of
  scope"'s list items — a global find-and-replace would put both sections' content in both
  places. Fixed with `_fill_first_list_line`, which replaces only the *next remaining*
  occurrence of a line placeholder each time it's called, so calling it once per section in
  document order lands each list in the right place. Unit-tested this specifically (asserting
  in-scope content's position is before "## Out of scope" and vice versa), not just that the
  text is present somewhere.
- `find_cycle`: DFS with path tracking, returns the actual closing loop (e.g. `["A","B","C","A"]`)
  rather than just a yes/no — lets `SKILL.md` show the human exactly which slices to fix. Tested
  against an acyclic graph, a 3-node cycle, a cycle coexisting with an unrelated acyclic branch
  (confirms it doesn't false-positive on the wrong subgraph), and a self-referential single-node
  edge case.
- `finish`'s board/children confirmation reuses a small local `_region_content` (marker-slice,
  same technique used elsewhere in this repo for `## TODO`) rather than sync's internal
  `RegionSpan`/`find_region` machinery, since only "is this non-empty" is needed here.
- **Full-chain integration test** (mirrors TASK-018's own dry run): `write-spec` → `check-cycles`
  (on a 2-slice graph, confirmed acyclic) → `write-epics` → two real `add-task run` calls (the
  second `blocked_by` the first) → `finish`. Confirmed `sync` reconciled `blocks` automatically
  (`TASK-001`'s `blocks: [TASK-002]` appeared with no direct write), `finish` reported the epic
  correctly `in_epics_panel`/`children_populated`, and `sync check` stayed clean throughout —
  the acyclic-by-construction proof testing strategy step 1 (and TASK-018's own precedent) asks
  for, now automated rather than performed by hand.
- **Tests** (`tests/test_plan_feature_scaffold.py`, 16 new): `find_cycle` (acyclic, cyclic,
  cycle-with-unrelated-branch, self-reference, empty); `render_spec_file`/`render_epic_file`
  (every placeholder filled, comment dropped, missing-placeholder refusal, the shared-`{{item}}`
  ordering check, null `spec:` rendering); `write-spec`/`write-epics`/`finish`/`check-cycles`
  subcommands and the full chain above, all as real subprocesses against a scratch repo built by
  `init-project`'s own scaffold script.
- Full suite: `pytest` 316 passed (300 prior + 16 new); `python3 .tasks/bin/sync check` exit 0 on
  the real repo throughout.
- Re-read `SKILL.md` (testing strategy step 4): every remaining step is either the interview, the
  decomposition/epic-grouping judgment, a STOP checkpoint, or exactly one `scaffold.py` call.

## Notes

- No hard dependency — TASK-018 (what this refactors) is already done.
- Placed at the bottom of TODO — per the user's explicit instruction when this task was filed.
