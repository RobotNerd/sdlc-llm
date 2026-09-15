---
id: TASK-047
title: "review-docs skill: periodic pass to catch stale docs and dangling references"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-15
branch: task-047-review-docs-skill-periodic-pass-to-catch-stale-docs-and-dangling-references
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-047: review-docs skill: periodic pass to catch stale docs and dangling references

## Description

A new skill, `review-docs`, that turns TASK-023's manual docs-cleanup pass into a repeatable,
periodic one the human invokes directly (not run automatically) — same "propose, don't act
unilaterally" shape as `refine-backlog`, but for docs instead of the backlog.

`.tasks/config.md` gains two new keys, both fixed defaults from `init-project`'s template (not
asked in its interview, same treatment as `allow_auto_merge`):

- `docs_review_paths` — the docs this skill always checks, seeded with `CLAUDE.md`, `README.md`,
  `.tasks/guidelines.md`, `.claude/skills/init-project/templates/guidelines.md`.
- `docs_ignore_paths` — paths this skill never touches or scans into, seeded with
  `.tmp/prompts.md`. Deliberately **separate** from TASK-028's planned `ignored_paths` key —
  that one is scoped to `implement-task`'s dirty-tree/rebase-stash check, a different concern;
  conflating the two names under one meaning was considered and rejected when this task was
  filed. (Investigated whether `sync` itself already has an `ignored_paths` notion: it doesn't —
  only `implement-task/scaffold.py` hardcodes `.tmp/prompts.md` today, and TASK-028 already covers
  generalizing that specific case. No fix needed there.)

**Mechanical vs. judgment split** (mirrors TASK-025's script-extraction shape): reading a doc and
deciding whether its prose is still accurate, redundant, or should be relocated is judgment — that
stays in `SKILL.md`. What's genuinely mechanical, and belongs in a paired `scaffold.py`:

- **Mirror-diff check** — do `.tasks/guidelines.md` and its portable-template mirror
  (`.claude/skills/init-project/templates/guidelines.md`) still match, module the documented
  SPEC-001-pointer differences? (Exactly what TASK-023 did by hand with `diff`.)
- **Dangling-reference check** — for each doc in `docs_review_paths`, extract file/path-like
  references it makes (a `` `.tasks/foo.md` ``-style backtick token, a bare relative path) and
  confirm each still exists in the repo, skipping `docs_ignore_paths` and anything that's
  obviously a URL or a code-fence example rather than a real repo path.
- **Skill-list check** — if a doc enumerates skill names (as README/CLAUDE.md do), confirm that
  list matches `ls .claude/skills/` exactly (nothing missing, nothing stale).

## Acceptance criteria

- [ ] `.tasks/config.md` and `.claude/skills/init-project/templates/config.md` both gain
      `docs_review_paths` and `docs_ignore_paths`, seeded as described above; both are fixed
      values in the template (not `{{placeholder}}`s), documented under "Key notes".
- [ ] A stdlib-only Python script under `.claude/skills/review-docs/` provides the mirror-diff
      check, the dangling-reference check, and the skill-list check, each callable individually
      and via one combined `report` subcommand (same shape as `refine-backlog`'s `report`).
- [ ] `docs_ignore_paths` is honored by every check — an ignored path is never scanned into or
      flagged as a dangling target.
- [ ] `.claude/skills/review-docs/SKILL.md` is a checklist: run `report`; for each doc in
      `docs_review_paths`, read it and judge staleness/redundancy against current reality (the
      actual skill files, `sync`'s real behavior, `.tasks/specs/*`); propose concrete edits; where
      something can't be resolved by reading the repo (a design-rationale claim, a "why" that
      isn't checkable by grep), **ASK** the human rather than guessing; **STOP** for confirmation
      before editing any doc; apply confirmed edits; re-run `report` plus `sync check` afterward.
- [ ] Unit tests cover: the mirror-diff check against a matching and a deliberately diverging
      fixture pair, the dangling-reference check against a fixture doc with one real and one
      broken reference, and the skill-list check against a fixture directory with a
      missing/extra skill.

## Testing strategy

1. Unit-test each of the three mechanical checks against small fixtures (matching/diverging
   mirror pair; a doc with a real and a broken reference; a skill directory missing one skill and
   containing one extra).
2. Run `report` against this repo's real, current docs — confirm it finds nothing (TASK-023 just
   cleaned everything up), the same "healthy repo, nothing destructive proposed" proof TASK-017's
   and TASK-025's own real-board dry runs used.
3. Deliberately break something reversibly (e.g. rename a skill directory on a scratch branch, or
   introduce a stale reference in a fixture copy of a real doc) and confirm `report` catches it;
   revert before finishing.
4. `python3 .tasks/bin/sync check` stays clean throughout.

## Worklog

_(empty — appended during implementation)_

## Notes

- Complements `refine-backlog` (backlog hygiene) with docs hygiene — same periodic,
  human-invoked, propose-and-wait shape, never auto-edits without confirmation.
- `docs_ignore_paths` vs. TASK-028's `ignored_paths`: decided as two separate keys with the human
  when this task was filed — different scopes (docs-review vs. dirty-tree-check), and coupling
  this task to TASK-028 via `blocked_by` wasn't worth it for a one-key overlap.
- Placed at the top of TODO per explicit instruction.
