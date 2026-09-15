---
id: TASK-049
title: "init-project: scaffold and upgrade a separate target repo via --target"
type: bug
status: todo
epic: EPIC-001
created: 2026-09-15
branch: task-049-init-project-target-repo
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-049: init-project: scaffold and upgrade a separate target repo via --target

## Description

`init-project` only works on the repo the session is running in. `scaffold.py cmd_run` resolves
its target from the cwd's git root (`repo_root()`) and then deliberately strips every `.claude/**`
entry out of `managed_files()` before applying it:

```python
files = {s: t for s, t in managed_files(own_repo_root).items() if t.parts[0] != ".claude"}
```

That filter exists because `run` assumed source repo == target repo, so the portable skills were
"already sitting exactly where they'd be copied to." The consequence: there is no way to stand up
the workflow in a separate project `T`. You'd have to be inside `T` to invoke the skill, but the
skill only lives in this toolkit clone — and even if you somehow got there, `run` would never copy
`.claude/skills/**` into `T` anyway.

Fix: add `--target <path>` to both `run` and `upgrade` so a human can clone this toolkit repo and
the target repo `T` side by side, launch Claude Code in the toolkit clone, and scaffold/refresh
`T` by path. Source stays "this clone" (no cloning/`--source` added to `run`); only the target
moves. `upgrade` already clones its own source, so giving it `--target` too is a small, symmetric
addition in the same task.

Decisions already made (do not re-litigate in implementation):
- Source location is `--target` only — no `--source`/clone added to `run`.
- A pre-existing managed file already present in the target is overwritten silently by `run`;
  `.tasks/` already existing is still the only thing that makes `run` refuse.
- `upgrade` gets `--target` in this same task.

## Acceptance criteria

- [ ] `scaffold.py run <answers.json> --target <path>` scaffolds `.tasks/`, `.github/`, **and**
      `.claude/skills/**` (every non-repo-only skill) into the target repo's git root; omitting
      `--target` keeps the current cwd behaviour unchanged.
- [ ] The `t.parts[0] != ".claude"` filter in `cmd_run` is removed — `run` applies the full
      `managed_files()` table. `apply_managed_files`'s existing self-copy guard keeps the
      degenerate source==target case (no `--target` given) a no-op, as today.
- [ ] `strip-project-references` stays excluded (`_REPO_ONLY_SKILLS`) from what lands in the
      target.
- [ ] A managed file already present in the target is overwritten without prompting — the chosen
      behaviour; `run` still refuses only when the target already has `.tasks/`.
- [ ] `--target` pointing at a non-existent path, or at a path not inside a git repo, exits
      non-zero with a clear message naming the path.
- [ ] `sync` and `sync check` run with the **target** as cwd, and
      `.tasks/.toolkit-manifest.json` is written in the target with hashes covering the skill
      files too — so a later `upgrade --target <same path>` classifies them `up_to_date`, not
      `locally_modified`.
- [ ] `scaffold.py upgrade --target <path>` refreshes that target; its existing
      `--source`/`--ref`/`--dry-run`/`--force` semantics are unchanged.
- [ ] `SKILL.md` gains a `## 0. Parameters` section documenting `target` (optional; defaults to
      the current repo), and the interview/preflight steps check/act on the target path rather
      than the cwd — the `.tasks/`-exists routing check, the git-repo preflight, the config-hint
      scan, and both command lines shown to the human.
- [ ] `SKILL.md`'s finish step tells the human to start a new Claude Code session inside the
      target repo to use the copied skills.
- [ ] `SKILL.md`'s frontmatter `description` parses as valid YAML — the bare `: ` inside the
      scalar is gone — and its wording reflects scaffolding "a target repo" rather than only
- [ ] `README.md`'s `init-project` bullet mentions the two-clone / `--target` usage.
- [ ] `python3 .tasks/bin/sync check` is clean and the full `pytest` suite passes.

## Testing strategy

1. New tests in `tests/test_init_project_scaffold.py`, reusing its `_init_git_repo` helper to
   build **two** scratch repos under `tmp_path`: run `scaffold.py run answers.json --target <T>`
   and assert `T/.tasks/BOARD.md`, `T/.tasks/bin/sync` (mode `0o755`),
   `T/.github/pull_request_template.md`, and `T/.claude/skills/add-task/SKILL.md` all exist, and
   that `T/.claude/skills/strip-project-references` does **not**.
2. Assert the target's `.tasks/.toolkit-manifest.json` contains an entry for a skill file, then
   run `scaffold.py upgrade --target <T> --source <this repo's path> --dry-run` and assert the
   classification reports `locally_modified: []` with the skill files under `up_to_date`.
3. Negative tests: `--target /nonexistent` and `--target <a plain non-git tmp dir>` both exit
   non-zero naming the path; `--target` at a repo that already has `.tasks/` exits 2.
4. Regression: the existing no-`--target` `run`/`upgrade` tests still pass unchanged.
5. Confirm `SKILL.md`'s frontmatter parses as YAML (e.g. load it with `yaml.safe_load` on the
   text between the `---` markers, or open the file in VS Code and confirm the parse error is
   gone).
6. Manual end-to-end: `git init` a scratch repo `T`, run the skill against it from this clone,
   then `cd T` and confirm `python3 .tasks/bin/sync check` exits 0 and the copied skills are
   present under `.claude/skills/`.

## Worklog

_(empty — appended during implementation)_

## Notes

- Reuse `_repo_root_of(path)` (already in `scaffold.py`) rather than writing new git plumbing —
  `repo_root()` becomes a thin wrapper that raises `SystemExit` when it returns `None`.
- `managed_files(source_dir)`, `apply_managed_files`, `classify_managed_files`, `load_manifest`,
  and `write_manifest` already take explicit paths; the change is mostly threading a target root
  through `cmd_run`/`cmd_upgrade` and deleting one filter line.
- `run`'s source stays `_repo_root_of(SKILL_DIR)` — no clone, no network, no public repo required.
- Watch `tests/test_portable_surface.py`: new `SKILL.md` wording must not introduce a banned
  "this repo's own …" phrase or a dangling `TASK-`/`EPIC-` id.
- Files expected to change: `.claude/skills/init-project/scaffold.py`,
  `.claude/skills/init-project/SKILL.md`, `tests/test_init_project_scaffold.py`,
  `tests/test_init_project_upgrade.py`, `README.md`.
