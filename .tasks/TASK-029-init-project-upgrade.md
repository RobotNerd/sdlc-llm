---
id: TASK-029
title: "init-project upgrade: refresh an initialized project from the toolkit repo"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-14
branch: task-029-init-project-upgrade
pr: null
merge_commit: null
blocked_by: [TASK-027, TASK-028]
blocks: [TASK-030, TASK-038]
---

# TASK-029: init-project upgrade: refresh an initialized project from the toolkit repo

## Description

`init-project` is one-shot: `scaffold.py`'s `cmd_run` refuses outright when `.tasks/` already
exists ("migrating an existing setup is a future `upgrade` skill's job"), and `SKILL.md` step 0
says the same. A project scaffolded months ago is frozen at whatever the toolkit looked like that
day — its `.tasks/bin/sync`, `guidelines.md`, templates, PR template, and all five skills drift
further behind this repo with every merged task here. `workflow_version` was added to
`config.md`/`guidelines.md` from the start precisely to support a future migration path, but
nothing consumes it yet.

There is no distribution mechanism today: no plugin manifest, no `~/.claude/skills/`, no release
artifact — the skills exist only as files in this repo's `.claude/skills/`. So `upgrade` needs an
explicit source, fetched by **cloning the toolkit repo**
(`https://github.com/RobotNerd/sdlc-llm`, going public before this is used elsewhere).

The hard requirement: **no spec/epic/task data is ever lost.** `BOARD.md` (its TODO order is
hand-maintained and unrecoverable), `config.md`, every `SPEC-*`/`EPIC-*`/`TASK-*`, and
`.tasks/archive/` are project-owned and must come through an upgrade byte-identical. `config.md`'s
own schema migration is TASK-030's job, not this task's.

### Command

```
python3 .claude/skills/init-project/scaffold.py upgrade \
    [--source <git-url-or-path>] [--ref <ref>] [--dry-run] [--force]
```

`--source` defaults to the toolkit repo URL, `--ref` to `main`. Fetch with
`git clone --depth 1 [--branch <ref>] <source> <tmpdir>` into a `tempfile.TemporaryDirectory`.
`git clone` accepts a local path as readily as a URL, which is how tests drive the exact
production code path offline — no network in CI.

### Managed vs project-owned

Reuse and extend `repo_root()`. Extract the copy list currently inlined in `cmd_run` into a shared
`managed_files(source_dir) -> dict[Path, Path]` (source → target) so `run` and `upgrade` cannot
drift apart:

| Source (in the clone) | Target |
|---|---|
| `.claude/skills/<name>/**` (all five, minus `__pycache__`) | same path |
| `init-project/templates/guidelines.md` | `.tasks/guidelines.md` |
| `init-project/templates/{spec,epic,task}.md` | `.tasks/templates/` |
| `init-project/vendored-sync` | `.tasks/bin/sync` (mode `0o755`) |
| `init-project/templates/pull_request_template.md` | `.github/pull_request_template.md` |

**Never touched by `upgrade`:** `BOARD.md`, `config.md` (TASK-030), every
`SPEC-*`/`EPIC-*`/`TASK-*`, `.tasks/archive/`. `BOARD.md` needs no rewrite even if the board gains
a new section — `sync`'s `ensure_region` already inserts a missing region at an anchor, so the
post-upgrade `sync` run self-heals it.

### Drift detection via a manifest

`.tasks/.toolkit-manifest.json`, written by **both** `run` and `upgrade` so a freshly-initialized
project has a baseline from day one:

```json
{"source": "...", "ref": "main", "commit": "<sha>", "updated": "YYYY-MM-DD",
 "files": {"<repo-relative path>": "<sha256>"}}
```

Classify each managed path (`hashlib.sha256`):

- target missing → **new**
- target hash == source hash → **up to date**, skip
- target hash == manifest hash → **clean update**, safe to write
- otherwise (including no manifest entry at all, e.g. a pre-manifest project) → **locally
  modified**

If anything is locally modified and `--force` was not given: print a `difflib.unified_diff` per
conflicted file, **write nothing at all**, exit non-zero. All-or-nothing — never a partial
application. `--dry-run` prints the same classification and exits 0 without writing.

Otherwise write the new/clean-update files, rewrite the manifest with fresh hashes and the
resolved source commit, then run the newly-installed `.tasks/bin/sync` followed by `sync check`.

### Skill changes

`init-project/SKILL.md` step 0 currently dead-ends when `.tasks/` exists; it now routes to a new
`upgrade` section instead. That section keeps the cheap narrative pre-check the skill already uses
(does `.tasks/` exist? is this a git repo?), invokes the script, presents any conflict diffs at a
**STOP**, and re-runs with `--force` only after the human approves. The frontmatter `description`
gains the upgrade capability so the skill is discoverable for it. `cmd_run`'s existing refusal
message changes from "a future `upgrade` skill's job" to naming the real subcommand.

## Acceptance criteria

- [ ] `scaffold.py upgrade` exists with `--source`, `--ref`, `--dry-run`, `--force`; stdlib only.
- [ ] Refuses (non-zero, writes nothing) when `.tasks/` is absent, pointing at `run`.
- [ ] Refreshes all five skills plus `guidelines.md`, `.tasks/templates/*`, `.tasks/bin/sync`
      (executable), and `.github/pull_request_template.md` from the cloned source.
- [ ] `BOARD.md`, `config.md`, every `SPEC-*`/`EPIC-*`/`TASK-*` and `.tasks/archive/` are
      byte-identical before and after an upgrade.
- [ ] Both `run` and `upgrade` write `.tasks/.toolkit-manifest.json`.
- [ ] A locally-modified managed file produces a unified diff, a non-zero exit, and **zero** writes
      anywhere; `--force` overrides it.
- [ ] Running `upgrade` twice against the same ref is a true no-op: nothing written, exit 0,
      `git status` clean.
- [ ] `sync` then `sync check` run after a successful upgrade; a non-clean check fails loudly
      rather than being papered over (same posture as `cmd_run`).
- [ ] `init-project/SKILL.md` documents the upgrade flow and its STOP.

## Testing strategy

1. New `tests/test_init_project_upgrade.py`, importing `scaffold.py` by path with the
   `SourceFileLoader` + unique module name pattern already used in
   `tests/test_init_project_scaffold.py`.
2. Fixture: build a "toolkit source" git repo in `tmp_path` by copying this repo's
   `.claude/skills/` tree and committing it; point `--source` at that local path so the real
   `git clone` path is exercised offline.
3. Subprocess + `tmp_path` integration cases (real filesystem/git, not mocks): refuses with no
   `.tasks/`; upgrades a deliberately-staled file; second run is a no-op; locally-modified file →
   non-zero + diff + nothing written; `--force` overrides; `--dry-run` writes nothing.
4. **Data-loss guard:** hash every file under `.tasks/` and `.github/` before and after an
   upgrade; assert every non-managed path is unchanged. This is the criterion that matters most.
5. `pytest` and `python3 .tasks/bin/sync check` both pass on this repo.
6. Scratch-branch dry run against a real throwaway clone of an older commit of this repo,
   confirming a realistic multi-file upgrade reads sensibly. Human-run — record in the Worklog.

## Worklog

_(empty — appended during implementation)_

## Notes

- Depends on TASK-027 and TASK-028 having already landed in `scaffold.py` and
  `init-project/SKILL.md` to avoid a guaranteed rewrite conflict.
- `config.md` migration is deliberately out of scope here — see TASK-030.
