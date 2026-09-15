---
id: TASK-028
title: Replace .tmp/prompts.md special-case with an ignored_paths config key
type: refactor
status: done
epic: EPIC-001
created: 2026-09-14
branch: task-028-ignored-paths-config-key
pr: "https://github.com/RobotNerd/sdlc-llm/pull/46"
merge_commit: d4c2f27f97132fe7c4b29b3d466d25958c6f2145
blocked_by: [TASK-024]
blocks: [TASK-029, TASK-034]
---

# TASK-028: Replace .tmp/prompts.md special-case with an ignored_paths config key

## Description

`implement-task/SKILL.md` hardcodes `.tmp/prompts.md` as a standing dirty-tree exception in four
places: the phase-1 dirty-tree check ignores it, and phase 3 stashes it before rebasing if it's
dirty. That file is a personal scratch pad convention specific to this project/user, not something
every project using the toolkit has — a fresh project scaffolded by `init-project` should not
inherit a reference to a file it doesn't have.

Generalize it into an `ignored_paths` config key: paths whose dirty state `implement-task`
ignores when deciding whether the working tree is clean enough to start or rebase. Default `[]`,
fixed by the template like `allow_auto_merge` — not asked in the `init-project` interview, so the
interview stays the same length. A human adds paths later by editing `config.md` directly.

Blocked on TASK-024, which rewrites `implement-task/SKILL.md` wholesale for its own script split;
doing this first would guarantee a conflict.

`workflow_version` stays `1`: adding an optional key with a safe default (`[]`, behaving as today's
unconditional dirty-tree check when empty) is not a breaking data-model change, and skills must
tolerate its absence in a repo scaffolded before this task lands.

## Acceptance criteria

- [x] `.tmp/prompts.md` appears nowhere under `.claude/skills/`.
- [x] `init-project/templates/config.md` includes `ignored_paths: []` as a fixed value (not a
      `{{placeholder}}`), documented under "Key notes".
- [x] A freshly scaffolded `config.md` (via `scaffold.py`) contains `ignored_paths: []`.
- [x] `implement-task/SKILL.md` reads `ignored_paths` from `.tasks/config.md` for both the phase 1
      dirty-tree check and the phase 3 pre-rebase stash, and behaves as an unconditional check
      when the key is `[]` or absent.
- [x] `init-project/templates/guidelines.md`'s phase-1 description notes the `ignored_paths`
      exception.
- [x] This repo's own `.tasks/config.md` sets `ignored_paths: [.tmp/prompts.md]`, preserving
      today's behavior.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Extend `tests/test_init_project_scaffold.py` to assert the scaffolded `config.md` parses (via
   `sync.parse_frontmatter`) with `ignored_paths == []`.
2. Run the full `pytest` suite — confirm `sync` tolerates the new key in this repo's
   `config.md` without treating it as unexpected.
3. Run `python3 .tasks/bin/sync check` — exit 0.
4. Scratch-branch dry run (throwaway branch off `origin/main`, deleted — not merged — when done,
   no PR needed for a file-only check): dirty `.tmp/prompts.md`, invoke `implement-task` phase 1,
   confirm it proceeds; then dirty an unlisted file and confirm it refuses. Human-run —
   non-automatable — record the result in the Worklog.

## Worklog

- `dirty_files` and `wrap-up`'s pre-rebase stash now derive `ignore`/the stash pathspec from
  `config.get("ignored_paths")` at all three call sites (`resume-state`, `start`, `wrap-up`)
  instead of a module-level `_IGNORED_DIRTY_PATHS = (".tmp/prompts.md",)` constant, which is
  removed. `wrap-up`'s stash now covers every dirty `ignored_paths` entry in one `git stash push`
  (was hardcoded to the single `.tmp/prompts.md` path).
- Found and fixed two real latent bugs while writing integration tests against synthetic fixtures
  (both pre-existing, invisible in this repo only because `.tmp/prompts.md` happens to already be
  a tracked file here):
  1. `git status --porcelain` collapses a brand-new, entirely untracked directory into one
     `?? dirname/` line instead of listing the file inside — an `ignored_paths` entry naming a
     file that's never yet been committed would silently fail to match. Fixed by adding
     `--untracked-files=all` to the `git status` call in `dirty_files`.
  2. `git stash push -- <path>` refuses to stash a pathspec that only matches untracked files
     ("did not match any file(s) known to git") unless `-u`/`--include-untracked` is also given.
     Fixed by adding `-u` to `wrap-up`'s stash command.
- Testing strategy steps 1-3: automated, all passed (`tests/test_init_project_scaffold.py` now
  asserts a scaffolded `config.md` parses with `ignored_paths == []`; full `pytest` — 373 passed;
  `sync check` exit 0). Also added 5 new integration tests to
  `tests/test_implement_task_scaffold.py` beyond what the testing strategy asked for, covering
  the exact scenario step 4 wanted (a dirty configured path never blocks start/resume and is
  correctly excluded from what unlisted-dirty-file refusal reports; a dirty *unlisted* file still
  refuses; the stash survives `wrap-up`'s rebase and pops back uncommitted, not swept into the
  pushed commit) plus a direct `dirty_files`-with-`ignore` unit test.
- Step 4 (human-run, scratch-branch dry run against this repo's own dirty `.tmp/prompts.md`):
  discussed with the human — I won't touch `.tmp/prompts.md` myself per CLAUDE.md's instruction
  not to read or act on it, and it wasn't already dirty in my working tree to observe passively.
  Confirmed with the human that the fixture-based integration tests above exercise the identical
  mechanism end to end (proven further by the two real bugs they caught), and that's sufficient —
  no live dry run performed against this repo's real file.

## Notes

- Files touched: `init-project/templates/config.md`, `.claude/skills/init-project/scaffold.py`
  (comment only — no `REQUIRED_KEYS` change), `.claude/skills/init-project/SKILL.md` (extend the
  "always fixed, not asked" sentence), `.claude/skills/implement-task/SKILL.md` (the four
  `.tmp/prompts.md` mentions), `init-project/templates/guidelines.md`, and this repo's own
  `.tasks/config.md`.
