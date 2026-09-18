---
id: TASK-066
title: "init-project: merge Python ignore entries into the target repo's .gitignore"
type: feature
status: todo
epic: null
created: 2026-09-17
branch: task-066-gitignore-python-artifacts
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-066: init-project: merge Python ignore entries into the target repo's .gitignore

## Description

`init-project` vendors Python into every target project (`.tasks/bin/sync`,
`.tasks/bin/guardrails.py`, the hooks, every skill's `scaffold.py`), and running any of it produces
`__pycache__/` and `.pytest_cache/` directories. But `init-project` never touches the target's
`.gitignore`, so in a project that isn't already a Python project those artifacts show up as
untracked noise — or get committed. `.gitignore` is project-owned, so it can't be overwritten
wholesale (it's deliberately absent from `managed_files()` in
`.claude/skills/init-project/scaffold.py`). Add a programmatic, additive `.gitignore` merge,
modelled on the existing `merge_settings_hooks` function, applied by both `run` and `upgrade`.

## Acceptance criteria

- [ ] A new pure function in `scaffold.py` (e.g. `merge_gitignore(project_text: str) -> tuple[str, list[str]]`)
      returns the merged text plus the list of entries added; it returns the input unchanged and
      `[]` when every entry is already present.
- [ ] The entry set is exactly `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, written under a
      `# Python (added by init-project)` comment header.
- [ ] Recognition of an existing entry is tolerant of common equivalent spellings so nothing is
      duplicated — for `__pycache__`: bare, trailing-slash, and `**/`-prefixed forms; for the
      pyc glob: `*.pyc` and `*.py[cod]`; for pytest cache: bare and trailing-slash. Comments and
      blank lines are ignored when scanning.
- [ ] `cmd_run` applies the merge to `<target>/.gitignore`, creating the file if the target has
      none, and its final stdout line mentions the entries added (or says nothing was needed).
- [ ] `cmd_upgrade` applies the same merge and reports it in its JSON summary under a new
      `gitignore_added` key; `--dry-run` reports `gitignore_would_add` and writes nothing.
- [ ] `.gitignore` is **not** added to `managed_files()` — it stays project-owned, never
      hash-classified, never a `locally_modified` conflict.
- [ ] Nothing already in the target's `.gitignore` is removed, reordered, or rewritten; the merge
      appends only, and preserves a missing trailing newline correctly.
- [ ] Running `run` (or `upgrade`) twice produces no second copy of the block — idempotent.
- [ ] `init-project/SKILL.md` documents the behavior: a sentence in step 4 (Scaffold and finish)
      and one in step 5 (Upgrade) noting the additive `.gitignore` merge and its no-STOP posture,
      phrased portably (no task/epic ids, so `strip-project-references` stays clean).

## Testing strategy

1. Add unit tests for the merge function to `.tasks/bin/tests/test_init_project_scaffold.py`:
   empty/missing file, file with none of the entries, file already containing all three, file
   containing equivalent spellings (`__pycache__` bare, `**/__pycache__/`, `*.pyc`), file with no
   trailing newline, and a double-apply idempotency check.
2. Extend the existing `run` end-to-end test in `test_init_project_scaffold.py`: scaffold a temp
   git repo with no `.gitignore`, assert the file is created with the three entries.
3. Extend `test_init_project_upgrade.py`: a target that already has a `.gitignore` with unrelated
   entries gains only the missing Python ones, keeps its own lines untouched, and the JSON summary
   lists them under `gitignore_added`; a `--dry-run` writes nothing and reports
   `gitignore_would_add`.
4. Run `python3 -m pytest .tasks/bin/tests` — must pass.
5. Run `python3 .tasks/bin/sync check` — must exit 0.
6. Manual: run `upgrade --dry-run` against a scratch clone with no `.gitignore` and confirm the
   preview, then `upgrade` and confirm the written file.

## Worklog

_(empty — appended during implementation)_

## Notes

- Out of scope: broader Python ignores (`.venv/`, `*.egg-info/`, …) and any non-Python ignore
  entries — the toolkit-artifact-only set was chosen deliberately.
- Out of scope: `.gitignore` becoming a managed/hash-classified file.
