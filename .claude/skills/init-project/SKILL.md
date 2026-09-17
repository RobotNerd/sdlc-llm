---
name: init-project
description: Scaffold the "kanban in markdown" workflow into a repo — .tasks/ with BOARD.md, config.md, guidelines.md, templates, a vendored sync script, guardrail hooks (.claude/settings.json, .claude/hooks/), and .github/pull_request_template.md — or, if already initialized, upgrade it by refreshing every portable skill plus those same toolkit files from a source clone, never touching project-owned data (BOARD.md, config.md, spec/epic/task files, archive). Named init-project (not init) so it doesn't collide with a generic project-instructions-authoring init skill.
---

# init-project

A numbered checklist, not prose. Each step says exactly what to do; **STOP** means pause for the
human before continuing; **ASK** means don't guess — ask a follow-up question instead.

Everything mechanical — creating directories, writing/copying files, vendoring `sync`, running
`sync`/`sync check` — lives in `scaffold.py` next to this `SKILL.md`, not in this prose. This
skill's own job is the interview and the two STOPs; the script writes only what's already been
confirmed.

## 0. Parameters

A caller (a human, or a future skill) may supply:

| Parameter | Required? | Default if omitted |
|---|---|---|
| `target` | optional | the current repo (cwd) |

`target` is a path to the project to scaffold or upgrade — a separate local clone, not the repo
this skill itself is running from. When it's given, every step below (the `.tasks/`-exists check,
the git-repo preflight, the config-hint scan, and both `scaffold.py` command lines) acts on
`target` instead of the current directory; the session stays running from wherever this skill's
own files live the whole time, since that's where `scaffold.py`/the templates actually are. To
bring this workflow into another project: clone it alongside this toolkit repo, start a session in
the toolkit clone, and pass its path as `target`. Once scaffolding or upgrading finishes, tell the
human to start a **new** Claude Code session inside `target` — that's the session that will
actually use the copied skills.

## 1. Already initialized? Route to Upgrade instead

Quick check: does `.tasks/` already exist at `target`'s root (or the current repo's root, if no
`target` was given)? If so, this isn't a fresh scaffold — skip the interview entirely and go
straight to **## 5. Upgrade** below. (`scaffold.py run` also refuses on its own if this is somehow
skipped — this step exists so the interview below isn't wasted on a doomed run.)

## 2. Preflight

1. Quick check: is `target` (or the current directory, if no `target` was given) inside a git
   repository (`git rev-parse --show-toplevel`, run against that path)? If not, **STOP** and tell
   the human `init-project` needs a git repo to scaffold into. (Same reasoning as step 1 —
   `scaffold.py` verifies this independently too, for whichever path it's given.)
2. Run `gh auth status`. If `gh` isn't installed, or isn't authenticated, **warn** the human that
   `implement-task` needs `gh` for PR automation and won't work — in whichever repo it's later
   run in — until it's set up. A warning, not a blocker. **ASK** whether to continue anyway or
   stop to install/authenticate `gh` first.

## 3. Interview for `.tasks/config.md`

Ask for every value below — never fill one in without an answer. Look at `target` (or the current
repo, if no `target` was given) first for hints (a `package.json` `scripts.test`, a `Makefile`
target, an existing CI config, a `pyproject.toml`) to propose a sensible default, but always
**ASK** the human to confirm or override rather than writing a guessed value. If an answer is
ambiguous (e.g. "the usual" without saying what that is), **ASK** a follow-up rather than picking
for them.

| Key | What to ask | A reasonable default if the repo gives no better hint |
|---|---|---|
| `test_command` | How are tests run? | none — leave `null` if the human doesn't have one yet |
| `lint_command` | How is linting run, if at all? | `null` |
| `format_command` | How is code formatting run, if at all? | `null` |
| `docs_paths` | Which documents should be automatically updated in this repository when working on tasks? | `["README.md"]` |
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

## 4. Scaffold and finish

Once confirmed: write the answers as a JSON object to a scratch file (your scratchpad directory,
or any temp path — object keys are exactly the table above's, JSON `true`/`false`/`null`/lists as
appropriate), then run:

```
python3 .claude/skills/init-project/scaffold.py run <path-to-answers.json> [--target <path>]
```

Omit `--target` to scaffold the current repo (the original behavior — only `.tasks/`, `.github/`,
and the toolkit's core files are written; the skills already sitting in this repo aren't
recopied). Pass `--target <path>` to scaffold a separate project instead — in that case the full
`.claude/skills/**` table (every portable skill, `strip-project-references` excluded) is copied
into `target` too, since that's the only way a project you haven't started a session inside
actually ends up with the skills.

This performs every mechanical step (directory creation, `config.md` rendering, the verbatim
file copies, vendoring `sync`, running `sync` then `sync check` — all against `target` when given)
and exits non-zero with a clear message if `.tasks/` already exists there, `target` doesn't exist
or isn't a git repo, or an answer is missing.

If `target` already has a managed file that conflicts with the incoming source (e.g. it already
has its own `.claude/skills/add-task/SKILL.md`), it exits non-zero and prints a diff for each
conflicting file, writing nothing — **STOP**, show the human the diffs, and only re-run with
`--force` once they've explicitly accepted overwriting all of them.

If it exits non-zero for any other reason: **STOP**, show the human the error — that's a bug in
this script or in the vendored `sync`, not something to paper over by hand-editing a generated
region. If it exits `0`, show the human the resulting `.tasks/BOARD.md`, and — if `target` was
given — tell them to start a new Claude Code session inside `target` to actually use the skills
just copied there.

## 5. Upgrade (an already-initialized project)

Reached from step 1 when `.tasks/` already exists. No interview — just run:

```
python3 .claude/skills/init-project/scaffold.py upgrade [--target <path>] [--source <git-url-or-path>] [--ref <ref>]
```

Omit `--target` to refresh the current repo; pass it to refresh a separate project by path instead
(the human still starts a fresh session inside `target` afterward to pick up any changed skill
prose). (`--source`/`--ref` default to the toolkit repo's own URL and `main` — only pass them to
pull from somewhere else, e.g. a fork or a specific tag.) This refreshes every portable skill
under `.claude/skills/` plus `guidelines.md`, `.tasks/templates/*`, `.tasks/bin/sync`,
`.tasks/bin/guardrails.py`, `.claude/hooks/*`, `.claude/settings.json`, and
`.github/pull_request_template.md` from a fresh clone of the source. It never touches `BOARD.md`,
`config.md`, any `SPEC-*`/`EPIC-*`/`TASK-*` file, or `.tasks/archive/` — those are project-owned.

- Exit `0` with no locally-modified files reported: show the human the JSON summary
  (`new`/`updated`/`up_to_date` counts), then continue to **config.md migration** below.
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

### config.md migration

`config.md` is project-owned, so it's never part of `upgrade`'s own manifest/hash-classified
table above — it's only ever additively merged, and always gets its own STOP, run once `upgrade`
itself has succeeded (so `.tasks/bin/sync` is the refreshed one doing the parsing):

```
python3 .claude/skills/init-project/scaffold.py migrate-config [--target <path>]
```

This previews only — it reports `{"added": [...], "workflow_version_bumped_to": ..., "applied":
false, "diff": "..."}` and writes nothing. If `added` is empty and `workflow_version_bumped_to` is
`null`, the schema is already current — nothing further to do. Otherwise, restate the reported
`diff` to the human and **STOP** for explicit approval before writing anything. Once approved, run:

```
python3 .claude/skills/init-project/scaffold.py migrate-config --apply [--target <path>]
```

which writes the merged `config.md`, re-runs `sync` + `sync check`, and reports
`{"added": [...], "workflow_version_bumped_to": ..., "applied": true}` — show this to the human as
the final summary alongside step 5's own JSON. A non-zero exit here (parse failure, `sync`/`sync
check` failing after the write) is the same posture as everywhere else: **STOP**, show the error,
don't paper over it by hand-editing `config.md`.
