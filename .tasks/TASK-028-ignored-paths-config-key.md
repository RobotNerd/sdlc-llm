---
id: TASK-028
title: Replace .tmp/prompts.md special-case with an ignored_paths config key
type: refactor
status: todo
epic: EPIC-001
created: 2026-09-14
branch: task-028-ignored-paths-config-key
pr: null
merge_commit: null
blocked_by: [TASK-024]
blocks: [TASK-029]
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

- [ ] `.tmp/prompts.md` appears nowhere under `.claude/skills/`.
- [ ] `init-project/templates/config.md` includes `ignored_paths: []` as a fixed value (not a
      `{{placeholder}}`), documented under "Key notes".
- [ ] A freshly scaffolded `config.md` (via `scaffold.py`) contains `ignored_paths: []`.
- [ ] `implement-task/SKILL.md` reads `ignored_paths` from `.tasks/config.md` for both the phase 1
      dirty-tree check and the phase 3 pre-rebase stash, and behaves as an unconditional check
      when the key is `[]` or absent.
- [ ] `init-project/templates/guidelines.md`'s phase-1 description notes the `ignored_paths`
      exception.
- [ ] This repo's own `.tasks/config.md` sets `ignored_paths: [.tmp/prompts.md]`, preserving
      today's behavior.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

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

_(empty — appended during implementation)_

## Notes

- Files touched: `init-project/templates/config.md`, `.claude/skills/init-project/scaffold.py`
  (comment only — no `REQUIRED_KEYS` change), `.claude/skills/init-project/SKILL.md` (extend the
  "always fixed, not asked" sentence), `.claude/skills/implement-task/SKILL.md` (the four
  `.tmp/prompts.md` mentions), `init-project/templates/guidelines.md`, and this repo's own
  `.tasks/config.md`.
