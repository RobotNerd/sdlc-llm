---
name: init-project
description: Scaffold the "kanban in markdown" workflow into this repo — .tasks/ with BOARD.md, config.md, guidelines.md, templates, a vendored sync script, and .github/pull_request_template.md. Refuses if .tasks/ already exists. Named init-project (not init) so it doesn't collide with a generic project-instructions-authoring init skill.
---

# init-project

A numbered checklist, not prose. Each step says exactly what to do; **STOP** means pause for the
human before continuing; **ASK** means don't guess — ask a follow-up question instead.

Everything mechanical — creating directories, writing/copying files, vendoring `sync`, running
`sync`/`sync check` — lives in `scaffold.py` next to this `SKILL.md`, not in this prose. This
skill's own job is the interview and the two STOPs; the script writes only what's already been
confirmed.

## 0. Refuse if already initialized

Quick check: does `.tasks/` already exist at the repo root? If so, **STOP** before running any
interview — tell the human this repo is already using the workflow, and that `init-project`
doesn't support migrating or re-initializing an existing `.tasks/` (a future `upgrade` skill's
job). Change nothing and end here. (`scaffold.py` also refuses on its own if this is somehow
skipped — this step exists so the interview below isn't wasted on a doomed run.)

## 1. Preflight

1. Quick check: is the current directory inside a git repository (`git rev-parse
   --show-toplevel`)? If not, **STOP** and tell the human `init-project` needs to run inside a
   git repo. (Same reasoning as step 0 — `scaffold.py` verifies this independently too.)
2. Run `gh auth status`. If `gh` isn't installed, or isn't authenticated, **warn** the human that
   `implement-task` needs `gh` for PR automation and won't work until it's set up — a warning,
   not a blocker. **ASK** whether to continue anyway or stop to install/authenticate `gh` first.

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
| `docs_paths` | Which files should `implement-task` phase 3 consider "the docs" to keep current? | `["README.md"]` |
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

## 3. Scaffold and finish

Once confirmed: write the answers as a JSON object to a scratch file (your scratchpad directory,
or any temp path — object keys are exactly the table above's, JSON `true`/`false`/`null`/lists as
appropriate), then run:

```
python3 .claude/skills/init-project/scaffold.py run <path-to-answers.json>
```

This performs every mechanical step (directory creation, `config.md` rendering, the verbatim
file copies, vendoring `sync`, running `sync` then `sync check`) and exits non-zero with a clear
message if `.tasks/` already exists, this isn't a git repo, or an answer is missing.

If it exits non-zero for any other reason: **STOP**, show the human the error — that's a bug in
this script or in the vendored `sync`, not something to paper over by hand-editing a generated
region. If it exits `0`, show the human the resulting `.tasks/BOARD.md`.
