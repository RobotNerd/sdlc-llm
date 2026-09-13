---
name: init-project
description: Scaffold the "kanban in markdown" workflow (SPEC-001) into this repo — .tasks/ with BOARD.md, config.md, guidelines.md, templates, a vendored sync script, and .github/pull_request_template.md. Refuses if .tasks/ already exists. Named init-project (not init) so it doesn't collide with a generic CLAUDE.md-authoring init skill.
---

# init-project

A numbered checklist, not prose. Each step says exactly what to do; **STOP** means pause for the
human before continuing; **ASK** means don't guess — ask a follow-up question instead. Files this
skill reads (never modifies) live under `templates/` next to this `SKILL.md`, plus a vendored copy
of `.tasks/bin/sync` at `vendored-sync` next to it.

## 0. Refuse if already initialized

Check whether `.tasks/` already exists at the repo root.

- If it does: **STOP**. Tell the human this repo is already using the workflow, and that
  `init-project` doesn't support migrating or re-initializing an existing `.tasks/` — that's a
  future `upgrade` skill's job. Change nothing and end here.
- If it doesn't: continue.

## 1. Preflight

1. Confirm the current directory is inside a git repository (`git rev-parse --show-toplevel`). If
   not, **STOP** and tell the human `init-project` needs to run inside a git repo.
2. Run `gh auth status`. If `gh` isn't installed, or isn't authenticated, **warn** the human that
   `implement-task` (the task-execution skill) needs `gh` for PR automation and won't work until
   it's set up — but this is a warning, not a blocker. **ASK** whether to continue anyway or stop
   to install/authenticate `gh` first.

## 2. Interview for `.tasks/config.md`

Ask for every value below — never fill one in without an answer. Look at the repo first for
hints (a `package.json` `scripts.test`, a `Makefile` target, an existing CI config, a
`pyproject.toml`) to propose a sensible default, but always **ASK** the human to confirm or
override rather than writing a guessed value. If an answer is ambiguous (e.g. "the usual" without
saying what that is), **ASK** a follow-up rather than picking for them.

| Key | What to ask | A reasonable default if the repo gives no better hint |
|---|---|---|
| `test_command` | How are tests run? | none — leave `null` if the human doesn't have one yet |
| `lint_command` | How is linting run, if at all? | `null` |
| `docs_paths` | Which files should `implement-task` phase 3 consider "the docs" to keep current? | `[README.md]` |
| `default_branch` | Default branch name? | `main` |
| `branch_prefix` | Prefix for task branches? | `task-` |
| `remote` | Git remote name? | `origin` |
| `rebase_before_pr` | Rebase onto the default branch before opening a PR? | `true` |
| `merge_strategy` | How does the human merge PRs — squash, merge, or rebase? | `squash` |
| `delete_branch_after_merge` | Delete the task branch after merge? | `true` |
| `ci_checks` | Names of any CI checks that already exist to gate merge on | `[]` (empty — nothing to gate on yet) |
| `archive_done` | Move `done`/`wont-do` tasks out to `.tasks/archive/`? | `true` |

`workflow_version` is always `1` and `allow_auto_merge` is always `false` — don't ask about
either; they're fixed by the template.

Once every value is answered, **restate the full `config.md` you're about to write and STOP** for
the human's go-ahead before creating any files.

## 3. Scaffold

Once confirmed:

1. Create `.tasks/`, `.tasks/bin/`, and `.tasks/templates/`.
2. Write `.tasks/config.md`: take `templates/config.md`, drop its leading `<!-- ... -->` comment
   block, and substitute the interview answers for its `{{placeholder}}`s.
3. Write `.tasks/guidelines.md` as a verbatim copy of `templates/guidelines.md` — it's already
   generic, no substitution needed.
4. Write `.tasks/BOARD.md` as a verbatim copy of `templates/board.md`.
5. Copy `templates/spec.md`, `templates/epic.md`, and `templates/task.md` into
   `.tasks/templates/` verbatim — these are the project's own task/epic/spec authoring templates
   (for `add-task`/`plan-feature`), a different thing from this skill's own `templates/`.
6. Write `.github/pull_request_template.md` (create `.github/` if it doesn't exist) as a verbatim
   copy of `templates/pull_request_template.md`.
7. Copy `vendored-sync` (next to this `SKILL.md`) to `.tasks/bin/sync` and make it executable
   (`chmod +x`). This isn't in SPEC-001's `init` file list, but nothing after this step works
   without it — see TASK-014's Worklog for why it's vendored here rather than referenced.

## 4. Finish

1. Run `python3 .tasks/bin/sync` (bare — it writes).
2. Run `python3 .tasks/bin/sync check` and confirm it exits `0`.
3. Show the human the resulting `.tasks/BOARD.md`.

If `sync check` is *not* clean at this point, that's a bug in this skill or in the vendored
`sync` — **STOP**, show the diff, and don't paper over it by hand-editing a generated region.
