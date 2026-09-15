---
id: TASK-047
title: "review-docs skill: periodic pass to catch stale docs and dangling references"
type: feature
status: in-review
epic: EPIC-001
created: 2026-09-15
branch: task-047-review-docs-skill-periodic-pass-to-catch-stale-docs-and-dangling-references
pr: "https://github.com/RobotNerd/sdlc-llm/pull/42"
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

- [x] `.tasks/config.md` and `.claude/skills/init-project/templates/config.md` both gain
      `docs_review_paths` and `docs_ignore_paths`, seeded as described above; both are fixed
      values in the template (not `{{placeholder}}`s), documented under "Key notes".
- [x] A stdlib-only Python script under `.claude/skills/review-docs/` provides the mirror-diff
      check, the dangling-reference check, and the skill-list check, each callable individually
      and via one combined `report` subcommand (same shape as `refine-backlog`'s `report`).
- [x] `docs_ignore_paths` is honored by every check — an ignored path is never scanned into or
      flagged as a dangling target.
- [x] `.claude/skills/review-docs/SKILL.md` is a checklist: run `report`; for each doc in
      `docs_review_paths`, read it and judge staleness/redundancy against current reality (the
      actual skill files, `sync`'s real behavior, `.tasks/specs/*`); propose concrete edits; where
      something can't be resolved by reading the repo (a design-rationale claim, a "why" that
      isn't checkable by grep), **ASK** the human rather than guessing; **STOP** for confirmation
      before editing any doc; apply confirmed edits; re-run `report` plus `sync check` afterward.
- [x] Unit tests cover: the mirror-diff check against a matching and a deliberately diverging
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

- 2026-09-15: Added `docs_review_paths`/`docs_ignore_paths` to `.tasks/config.md` (this repo's
  full list, including the portable-template mirror only this repo has) and the init-project
  template (a generic default, `[]` for ignore since `.tmp/prompts.md` is a personal convention
  not every project has) — both fixed values, not `{{placeholder}}`s, matching `allow_auto_merge`'s
  treatment; updated `scaffold.py`'s `REQUIRED_KEYS` comment accordingly (no actual `REQUIRED_KEYS`
  change needed, since fixed values have no placeholder to fill).
- Built `.claude/skills/review-docs/scaffold.py` (stdlib only): `mirror-diff`, `dangling-refs`,
  `skill-list-check`, and a combined `report` reading `.tasks/config.md`'s two new lists. No `sync`
  region/frontmatter writes here — this skill only reads and reports; edits are `SKILL.md`'s job.
- **Dangling-reference detection is a documented best-effort heuristic**, not exhaustive parsing:
  a backtick-quoted token counts as a path candidate only if it's a bare `README.md`/`CLAUDE.md`,
  or contains a `/` and either has a file extension or starts with a known root dir
  (`.tasks/`/`.claude/`/`.tmp/`/`.github/`) — filters out commands, flags, and placeholder patterns
  (`sync check`, `--force-with-lease`, `origin/main`, `<remote>/<default_branch>`, `TASK-NNN`,
  `EPIC-*.md`). Verified this doesn't false-positive on any of those forms (unit tests).
- **Real dry run against this repo's own current docs (testing strategy step 2) caught two genuine
  gaps, not test bugs:**
  1. The skill-list check (matches a doc's `- **`name`**` bullets against `.claude/skills/`)
     found README.md's Skills section only bold-backtick-bullets `init-project` — the other four
     skill names live inside a fenced-code diagram and a phase table, neither of which the check
     (correctly) treats as a claim. This is a real regression from TASK-023's own README rewrite,
     which dropped the original per-skill bullet list in favor of the diagram/table. Fixed by
     restoring bullets for all five (now six, with this task's own `review-docs`) skills alongside
     the diagram — the diagram stays as a quick "how it fits together" view, the bullets make the
     list mechanically checkable again. Also updated CLAUDE.md's "all five skills" count to six.
  2. Confirms this task's own new skill is real-world exercised, not just fixture-tested — running
     `report` against the real repo immediately after building the skill directory is what
     surfaced gap 1, exactly the kind of thing this skill exists to catch going forward.
- **Deliberate-break demo** (testing strategy step 3, done directly against the real repo since it
  was quick and fully reversible): renamed `.claude/skills/plan-feature` to
  `plan-feature-renamed`, ran `report` — correctly reported `missing: ["plan-feature-renamed"],
  extra: ["plan-feature"]` in README's skill-list mismatch — then renamed it back and re-ran
  `report` to confirm clean. `git status` and `sync check` confirmed no residue afterward.
- `guidelines_mirror_diff` against the real repo is (correctly) non-empty: `.tasks/guidelines.md`
  and its portable-template mirror have four documented intentional differences (three SPEC-001
  pointers plus one explicit skill-path mention) — `mirror_diff` reports the raw diff always,
  judging whether a difference is expected is `SKILL.md`'s own step 2, not the script's job.
- **Tests** (`tests/test_review_docs_scaffold.py`, 24 new): `mirror_diff` (identical/diverging);
  `find_path_references`/`dangling_references` (real path extraction, every excluded-pattern case
  parametrized, trailing-punctuation stripping, ignore-list honored); `claimed_skill_names`/
  `skill_list_mismatch` (matching, missing+extra, doc with no recognized skill list); all four
  subcommands against a minimal real git-repo fixture (not the full init-project/add-task chain —
  this skill never touches `.tasks/` task files, so a lighter fixture suffices); `report` against
  this repo's own real, current docs (asserts clean dangling-refs/skill-list, non-empty but
  expected mirror diff).
- Full suite: `pytest` 342 passed (318 prior + 24 new); `python3 .tasks/bin/sync check` exit 0 on
  the real repo throughout, including after the deliberate-break demo's revert.

## Notes

- Complements `refine-backlog` (backlog hygiene) with docs hygiene — same periodic,
  human-invoked, propose-and-wait shape, never auto-edits without confirmation.
- `docs_ignore_paths` vs. TASK-028's `ignored_paths`: decided as two separate keys with the human
  when this task was filed — different scopes (docs-review vs. dirty-tree-check), and coupling
  this task to TASK-028 via `blocked_by` wasn't worth it for a one-key overlap.
- Placed at the top of TODO per explicit instruction.
