---
id: TASK-049
title: "init-project: scaffold and upgrade a separate target repo via --target"
type: bug
status: done
epic: EPIC-001
created: 2026-09-15
branch: task-049-init-project-target-repo
pr: "https://github.com/RobotNerd/sdlc-llm/pull/49"
merge_commit: 2015d2d1a2756b6d914fc41953aacb4652f9974d
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
- A pre-existing managed file already present in the target is a conflict `run` refuses on: show
  a diff and require `--force` to overwrite — the same posture `upgrade` already uses via
  `classify_managed_files`/`locally_modified`, not a silent overwrite.
- `upgrade` gets `--target` in this same task.

## Acceptance criteria

- [x] `scaffold.py run <answers.json> --target <path>` scaffolds `.tasks/`, `.github/`, **and**
      `.claude/skills/**` (every non-repo-only skill) into the target repo's git root; omitting
      `--target` keeps the current cwd behaviour unchanged.
- [x] `run`'s `.claude`-filter behavior is now conditional on `--target`: with no `--target` it's
      unchanged (only the four non-skill entries, matching the original design where installing
      skills is `upgrade`'s job); with `--target` the full `managed_files()` table applies.
- [x] `strip-project-references` stays excluded (`_REPO_ONLY_SKILLS`) from what lands in the
      target.
- [x] `run --target <path>` where the target already has a managed file that differs from the
      incoming source: reuses `classify_managed_files`/a shared `_report_conflicts` helper (now
      used by both `run` and `upgrade`) — prints a diff for each conflicting file, writes nothing,
      exits non-zero, and tells the human to re-run with `--force` to overwrite. Only after
      `--force` are those files written.
- [x] `--target` pointing at a non-existent path, or at a path not inside a git repo, exits
      non-zero with a clear message naming the path.
- [x] `sync` and `sync check` run with the **target** as cwd, and
      `.tasks/.toolkit-manifest.json` is written in the target with hashes covering the skill
      files too — so a later `upgrade --target <same path>` classifies them `up_to_date`, not
      `locally_modified`.
- [x] `scaffold.py upgrade --target <path>` refreshes that target; its existing
      `--source`/`--ref`/`--dry-run`/`--force` semantics are unchanged.
- [x] `SKILL.md` gains a `## 0. Parameters` section documenting `target` (optional; defaults to
      the current repo), and the interview/preflight steps check/act on the target path rather
      than the cwd — the `.tasks/`-exists routing check, the git-repo preflight, the config-hint
      scan, and both command lines shown to the human. (Existing steps 0–4 renumbered to 1–5 to
      make room.)
- [x] `SKILL.md`'s finish step tells the human to start a new Claude Code session inside the
      target repo to use the copied skills.
- [x] `README.md`'s `init-project` bullet mentions the two-clone / `--target` usage.
- [x] `python3 .tasks/bin/sync check` is clean and the full `pytest` suite passes.

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
4. Conflict test: pre-create a managed file in the target (e.g. a hand-edited
   `.claude/skills/add-task/SKILL.md`) that differs from the source, run
   `run answers.json --target <T>`, and assert it exits non-zero, prints a diff naming that file,
   and leaves the target's copy untouched; re-run with `--force` and assert it's overwritten.
5. Regression: the existing no-`--target` `run`/`upgrade` tests still pass unchanged.
6. Manual end-to-end: `git init` a scratch repo `T`, run the skill against it from this clone,
   then `cd T` and confirm `python3 .tasks/bin/sync check` exits 0 and the copied skills are
   present under `.claude/skills/`.

## Worklog

- Added `_resolve_target`/`_report_conflicts` helpers to `scaffold.py`; `cmd_run` now conditions
  its `.claude`-filter on whether `--target` was given (preserving the original no-`--target`
  behavior exactly, which several existing tests document as an actual invariant — "`run` never
  copies sibling skill directories" — not just an incidental side effect of the old filter).
  `cmd_upgrade` now resolves its root via `_resolve_target` too, and reuses `_report_conflicts`
  instead of its own inline diff-printing block.
- New tests: `tests/test_init_project_scaffold.py` — `--target` scaffold (full skill table copied,
  manifest covers skills, negative paths for missing/non-git `--target`, `.tasks/`-exists-in-target
  exit 2, conflict-then-`--force`). `tests/test_init_project_upgrade.py` — `--target` on `run` from
  an unrelated cwd, `run --target` then `upgrade --target --dry-run` sees skills `up_to_date`, and
  `upgrade --target` refreshing a separate project. All existing tests (including the ones
  asserting `run`'s no-`--target` behavior is unchanged) still pass.
- Full suite: `pytest` → 404 passed. `python3 .tasks/bin/sync check` → clean.
- Manual end-to-end (testing strategy step 6): `git init`'d a scratch repo at `/tmp/manual-e2e-target`,
  ran `scaffold.py run <answers> --target /tmp/manual-e2e-target` from this clone. Result: `sync
  check` clean in the target, all six portable skills present under `.claude/skills/`,
  `strip-project-references` absent, `.tasks/bin/sync` executable (`0755`). Scratch repo removed
  afterward.
- `SKILL.md`'s frontmatter YAML-parse fix (originally a separate acceptance criterion the human
  removed once confirmed already done) was verified again unaffected by the rewrite:
  `yaml.safe_load` on the frontmatter still succeeds.

## Notes

- Reuse `_repo_root_of(path)` (already in `scaffold.py`) rather than writing new git plumbing —
  `repo_root()` becomes a thin wrapper that raises `SystemExit` when it returns `None`.
- `managed_files(source_dir)`, `apply_managed_files`, `classify_managed_files`, `load_manifest`,
  and `write_manifest` already take explicit paths; the change is mostly threading a target root
  through `cmd_run`/`cmd_upgrade` and deleting one filter line.
- `run`'s source stays `_repo_root_of(SKILL_DIR)` — no clone, no network, no public repo required.
- `run`'s conflict handling should reuse `classify_managed_files`/the diff-printing block `upgrade`
  already has, rather than a second implementation — `run` has no prior manifest to consult
  (`load_manifest` returns `{}` on a fresh target), so every differing pre-existing file classifies
  as `locally_modified` and needs `--force`; add `--force` to `run`'s argparser alongside `--target`.
- Watch `tests/test_portable_surface.py`: new `SKILL.md` wording must not introduce a banned
  "this repo's own …" phrase or a dangling `TASK-`/`EPIC-` id.
- Files expected to change: `.claude/skills/init-project/scaffold.py`,
  `.claude/skills/init-project/SKILL.md`, `tests/test_init_project_scaffold.py`,
  `tests/test_init_project_upgrade.py`, `README.md`.
