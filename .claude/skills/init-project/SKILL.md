---
name: init-project
description: Scaffold the "kanban in markdown" workflow into this repo — .tasks/ with BOARD.md, config.md, guidelines.md, templates, a vendored sync script, and .github/pull_request_template.md — or, if already initialized, upgrade it by refreshing every portable skill plus those same toolkit files from a source clone, never touching project-owned data (BOARD.md, config.md, spec/epic/task files, archive). Named init-project (not init) so it doesn't collide with a generic project-instructions-authoring init skill.
---

# init-project

A numbered checklist, not prose. Each step says exactly what to do; **STOP** means pause for the
human before continuing; **ASK** means don't guess — ask a follow-up question instead.

Everything mechanical — creating directories, writing/copying files, vendoring `sync`, running
`sync`/`sync check` — lives in `scaffold.py` next to this `SKILL.md`, not in this prose. This
skill's own job is the interview and the two STOPs; the script writes only what's already been
confirmed.

## 0. Already initialized? Route to Upgrade instead

Quick check: does `.tasks/` already exist at the repo root? If so, this isn't a fresh scaffold —
skip the interview entirely and go straight to **## 4. Upgrade** below. (`scaffold.py run` also
refuses on its own if this is somehow skipped — this step exists so the interview below isn't
wasted on a doomed run.)

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

`workflow_version` is always `1`, `allow_auto_merge` is always `false`, and `ignored_paths` always
starts `[]` — don't ask about any of them; they're fixed by the template.

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

## 4. Upgrade (an already-initialized project)

Reached from step 0 when `.tasks/` already exists. No interview — just run:

```
python3 .claude/skills/init-project/scaffold.py upgrade [--source <git-url-or-path>] [--ref <ref>]
```

(`--source`/`--ref` default to the toolkit repo's own URL and `main` — only pass them to pull from
somewhere else, e.g. a fork or a specific tag.) This refreshes every portable skill under
`.claude/skills/` plus `guidelines.md`, `.tasks/templates/*`, `.tasks/bin/sync`, and
`.github/pull_request_template.md` from a fresh clone of the source. It never touches `BOARD.md`,
`config.md`, any `SPEC-*`/`EPIC-*`/`TASK-*` file, or `.tasks/archive/` — those are project-owned.

- Exit `0` with no locally-modified files reported: done, show the human the JSON summary
  (`new`/`updated`/`up_to_date` counts).
- Exit non-zero listing locally-modified files: it wrote nothing. Show the human the printed diffs
  — each one is a managed file edited by hand since the last `run`/`upgrade`, which a plain
  overwrite would silently destroy. **STOP** and ask whether to keep the local edit (leave that
  file alone, rerun `upgrade` some other time), resolve it by hand first, or accept the incoming
  version. Only after the human explicitly accepts overwriting **all** the listed files, re-run
  with `--force` — it re-clones and reapplies the exact same classification, this time writing the
  previously-conflicting files too.
- Exit non-zero for any other reason (clone failure, `sync`/`sync check` failing after a write):
  **STOP**, show the human the error — same posture as `run`, not something to paper over.

Use `--dry-run` first if the human wants to preview the classification without committing to
either path — it prints the same JSON and writes nothing, `locally_modified` included, regardless
of `--force`.
