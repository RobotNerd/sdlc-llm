---
id: TASK-048
title: "Add strip-project-references skill: detect and fix portable-surface reference leaks"
type: feature
status: in-progress
epic: EPIC-001
created: 2026-09-15
branch: task-048-strip-project-references-skill
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-048: Add strip-project-references skill: detect and fix portable-surface reference leaks

## Description

TASK-027 stripped project-specific references (`TASK-`/`EPIC-`/`SPEC-NNN` ids, `CLAUDE.md`,
`.tmp/workflow-plan.md`, "this repo's own …") out of the portable skills surface
(`.claude/skills/**`), by hand, once. That surface keeps regressing: `add-task`, `plan-feature`,
and `review-docs` all reintroduced the same class of reference after TASK-027 was written (each
added a new `scaffold.py` with its own `(TASK-NNN)` provenance comment), and every future
skill-authoring task will do it again. This task turns that one-off manual pass into a periodic,
human-invoked skill — `strip-project-references` — following the same shape as `review-docs`
(mechanical scan lives in `scaffold.py`, judgment lives in `SKILL.md`, propose-then-STOP before
editing).

**Repo-only, never copied.** This skill exists to keep *this* repo's own shipped surface clean —
meaningless (and possibly always-failing, same reasoning as TASK-036's hook) once copied into a
project that didn't author that surface itself. TASK-029 (`init-project upgrade`, still `todo`)
will be the first thing that ever copies `.claude/skills/*` into another repo; its Notes have been
updated to exclude `.claude/skills/strip-project-references/` from that copy list. There is no
copy mechanism to test against today (TASK-029 isn't built yet) — this task's acceptance criteria
only needs the skill itself to exist and work correctly in this repo; there's nothing to enforce
the exclusion against until TASK-029 lands.

### Detection (mechanical, in `scaffold.py`)

Reuse and extend the exact grep TASK-027 built for `tests/test_portable_surface.py`:
`\b(?:TASK|EPIC|SPEC)-\d{3}\b`, plus the banned phrases `CLAUDE.md` (with the same two narrow
exemptions TASK-027 carved out: `templates/config.md`'s `docs_review_paths` default and
`review-docs/scaffold.py`'s `_ROOT_DOC_NAMES` constant), `.tmp/workflow-plan.md`, and
`"this repo's own"`. Move this scanning function into the new skill's `scaffold.py` as the single
canonical implementation, and change `tests/test_portable_surface.py` to import it (by file path,
same `SourceFileLoader` pattern every other test module already uses for its skill's
`scaffold.py`) instead of keeping its own copy of the regex/exemption list — one implementation,
can't drift apart.

### Auto-fix scope (mechanical, in `scaffold.py`) vs. judgment (in `SKILL.md`)

Not every offender is safe to fix by pattern substitution — TASK-027's own diff shows why: a
`SPEC-001 §'Epic status derivation'` citation needed the *sentence* rewritten
("Implements the seven ordered epic-status-derivation rules"), not a text swap, and
`"this repo's own"` was resolved differently every time (sometimes reworded, sometimes the whole
clause dropped). Split the offenders TASK-027's own diff already demonstrates into two buckets:

- **Mechanically safe (auto-fix)**:
  - A parenthetical whose *entire* trimmed content is one or more ids and nothing else — e.g.
    `(TASK-024)`, `(TASK-021/022/024)` — strip the whole parenthetical plus its leading space.
    (Contrast with a *mixed* parenthetical like `(SPEC-001 §implement-task phase 2)`, which is
    NOT auto-fixable — see below.)
  - Any remaining concrete `TASK-\d{3}`/`EPIC-\d{3}`/`SPEC-\d{3}` that is *not* part of a `§`
    citation (i.e., not in the same sentence/clause as a `§` mark) — replace its digits with
    `NNN` (`TASK-016` → `TASK-NNN`, `[TASK-004, TASK-006]` → `[TASK-NNN, TASK-NNN]`,
    `task-021-my-task` → `task-NNN-my-task`). These are format examples, not citations.
- **Flagged for judgment (SKILL.md proposes, human/LLM confirms, then edits by hand)**:
  - Any sentence/clause containing a `SPEC-NNN §...`-style citation — needs the rule restated
    without the citation (TASK-027's own diff is full of worked examples of this).
  - Any occurrence of `CLAUDE.md` (outside the two allowlisted defaults), `.tmp/workflow-plan.md`,
    or `"this repo's own"` — needs contextual rephrasing or clause removal, not a fixed swap.

### Skill shape

Same structure as `review-docs`: `SKILL.md` is a numbered checklist (run `scan`, walk the
mechanically-fixable offenders and confirm applying them, walk the judgment-needing offenders one
at a time proposing a specific rewrite for each and **STOP** for confirmation before editing,
apply confirmed edits, re-run `scan` + `pytest` + `sync check` to verify clean). `scaffold.py`
exposes at least `scan` (report both buckets as JSON) and `apply-mechanical` (auto-fix only the
safe bucket, report what changed) — no subcommand ever touches the judgment bucket's content,
that's `SKILL.md`'s job same as everywhere else in this toolkit.

### Docs

`CLAUDE.md`'s "All six skills exist: ..." line (in `docs_paths`) needs updating to name and count
seven, same as it should have when `review-docs` (TASK-047) landed — note it explicitly says
"repo-only" for this one so a future reader doesn't assume it's part of what gets vendored.

## Acceptance criteria

- [x] `.claude/skills/strip-project-references/SKILL.md` exists: numbered checklist, STOP before
      editing anything, same shape as `review-docs`.
- [x] `.claude/skills/strip-project-references/scaffold.py` exists, stdlib only, exposing at least
      `scan` (reports both the mechanically-fixable and judgment-needing offenders, each with
      file/line) and `apply-mechanical` (fixes only the mechanically-safe bucket).
- [x] `apply-mechanical` never modifies a `§`-citation sentence or a banned-phrase occurrence —
      only the two mechanical patterns described above.
- [x] `tests/test_portable_surface.py` imports its scan logic from the new skill's `scaffold.py`
      instead of keeping its own copy of the regex/exemption list.
- [x] Running `scan` against the current (post-TASK-027, clean) tree reports zero offenders of
      either kind.
- [x] `CLAUDE.md`'s skill list/count is updated to include `strip-project-references`, marked
      repo-only.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests for `scan`'s pure detection function against fixture strings covering every
   category from TASK-027's actual diff: an id-only parenthetical, a mixed parenthetical (must
   NOT be flagged as mechanically-safe), a bare id-as-example, a `SPEC-NNN §'...'` citation, each
   banned phrase (including both `CLAUDE.md` exemption spots, which must not be flagged).
2. Unit tests for `apply-mechanical` on the same fixtures: confirms the two safe patterns are
   fixed byte-for-byte as expected, and every judgment-bucket fixture is left untouched.
3. Run `scan` against this repo's actual `.claude/skills/` tree (post-TASK-027) — asserts zero
   offenders, proving the categories match what TASK-027 already cleaned up.
4. Idempotency: run `apply-mechanical` against the current clean tree — asserts it's a no-op
   (nothing written, `git status` clean).
5. `pytest` — full suite green, including `tests/test_portable_surface.py` now importing the
   shared scanner.
6. `python3 .tasks/bin/sync check` — exit 0.
7. Human-run: invoke the finished skill for real (`/strip-project-references` or equivalent) once
   against this repo's current tree, confirming the interview/report reads sensibly end-to-end
   even though there's nothing to fix right now. Non-automatable — record the result in the
   Worklog.

## Worklog

- Detection design settled on **paragraph-level classification** (blank-line-delimited blocks of
  the raw file text): a paragraph containing `§` or a (non-exempt) banned phrase routes every id
  in it to the judgment bucket, even across a line break — this was necessary because the real
  `SPEC-001\n    §'ID allocation'` citation in `.tasks/bin/sync` has the id and `§` mark on
  *different* lines; a same-line-only check would have misclassified it as mechanically safe.
  Verified against 7 hand-built fixtures reproducing TASK-027's real diff categories before
  writing the formal test suite — all classified correctly.
- Discovered mid-implementation: this skill's own `scaffold.py`/`SKILL.md` necessarily document
  real ids and the banned phrases themselves as examples of what they detect, which tripped the
  scanner against its own files. Resolved by excluding the skill's own directory
  (`_EXCLUDED_SKILL_DIRS`) from `iter_skill_surface_files` — sound because "repo-only, never
  vendored" (this skill's own premise) means it has nothing to be portable *for*. Same reasoning
  will apply to any future repo-only skill.
- Refactoring `tests/test_portable_surface.py` to import `scan_surface` surfaced no behavior
  change (3/3 tests still pass) — confirms the extracted scanner matches the original inline
  regex exactly.
- Adding the skill made `review-docs`'s own `skill_list_check` fail against README.md (real
  regression caught by existing tooling, not a bug in this task) — README.md's `## Skills` bullet
  list was missing `strip-project-references`. Added it, marked repo-only. Also fixed two
  pre-existing stale skill-count mentions in README.md ("Six" skills, "the five skills below")
  while touching the same doc, unrelated to this task's own change but trivial and directly
  adjacent.
- Testing strategy steps 1-6: all automated, all passed (22 new unit tests in
  `tests/test_strip_project_references_scaffold.py`; full suite 368 passed; `sync check` exit 0).
- Step 7 (human-run, flagged non-automatable in the task's own Testing strategy): turned out to
  be self-runnable — invoking a skill costs nothing and needs no credentials, so I invoked
  `/strip-project-references` directly via the Skill tool against this repo's real tree. It ran
  scan, got `{"mechanical": [], "judgment": []}`, correctly skipped straight to the summary step
  per its own step 1 instruction ("If both are empty, skip to step 5"), and reported nothing to
  do. Reads sensibly end-to-end.

## Notes

- TASK-029's own Notes have already been updated (this session) to exclude
  `.claude/skills/strip-project-references/` from its future `managed_files()` copy list — no
  action needed here, just don't undo that note.
- Precedent for every judgment-bucket rewrite lives in TASK-027's merged diff
  (`25669e6718dc0fcfedcfd46d40d59253d4e0b653`) — use it as worked examples when writing this
  skill's `SKILL.md` guidance and its tests' fixtures.
- Out of scope: actually wiring a pre-PR enforcement hook (that's TASK-036, a separate
  never-copied `.dev/hooks/` script with its own deny-on-match behavior, not this interactive
  skill).
