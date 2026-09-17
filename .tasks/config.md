---
workflow_version: 1
test_command: python3 -c "import sys; sys.exit(1)"
lint_command: null
format_command: null
docs_paths: [README.md, CLAUDE.md]
docs_review_paths: [CLAUDE.md, README.md, .tasks/guidelines.md, .claude/skills/init-project/templates/guidelines.md]
docs_ignore_paths: [.tmp/prompts.md]
default_branch: main
branch_prefix: task-
remote: origin
rebase_before_pr: true
merge_strategy: squash
delete_branch_after_merge: true
allow_auto_merge: false
ci_checks: [sync-check, test]
archive_done: true
ignored_paths: [.tmp/prompts.md]
---

# Workflow config

Per-project settings every skill and `sync` (`.tasks/bin/sync`) read. This is the seam SPEC-001
describes: the skills' logic stays identical across projects, only this file changes. See
`.tasks/specs/SPEC-001-llm-sdlc-workflow.md` §`.tasks/config.md` for the schema.

## Key notes

- **`workflow_version`** — lets a future `upgrade` path migrate a repo whose workflow predates a
  schema change. Bump it whenever a breaking change lands in the data model or `sync`'s contract.
- **`lint_command: null`** — no linter is configured yet. `.tasks/bin/sync` and its tests are
  stdlib-only plus `pytest` (TASK-004's sole dev dependency); adding a linter (e.g. `ruff`) is a
  separate decision, not bundled into this bootstrap. `null` means skills skip the lint step
  rather than fail on a command that doesn't exist. Update this once a linter is chosen.
- **`format_command: null`** — no formatter is configured yet. `null` means `implement-task`
  skips the formatting step entirely. Once set, `implement-task` runs it after phase 3's rebase
  and before the push, amending any resulting changes into the existing commit rather than adding
  a second one.
- **`docs_paths`** — files `implement-task` phase 3 considers touching as part of "update docs".
- **`docs_review_paths`** / **`docs_ignore_paths`** — `review-docs`'s own lists: which docs it
  always audits for staleness, and which paths it never scans into or flags. Deliberately
  separate from `docs_paths` (a different concern — per-task doc updates, not periodic audit) and
  from `ignored_paths` (`implement-task`'s dirty-tree/rebase-stash scope). This repo's own
  `docs_review_paths` includes the portable-template mirror
  (`.claude/skills/init-project/templates/guidelines.md`) that only this dogfooding repo has.
- **`remote` / `rebase_before_pr` / `merge_strategy` / `delete_branch_after_merge`** — the git
  automation settings from SPEC-001's `implement-task` phases 1/3/4. `merge_strategy: squash`
  documents how the *human* merges; the skill itself never merges (see `guidelines.md`).
- **`ci_checks: [sync-check, test]`** — the two `.github/workflows/ci.yml` job names (TASK-020):
  `sync-check` runs `.tasks/bin/sync check` (drift detection, stdlib only), `test` runs the
  `test_command` suite. `implement-task` phase 4 (and a human eyeballing `gh pr checks`) gates
  merge on both being green.
- **`allow_auto_merge: false`** — reinforces the never-merge guardrail; not currently read by
  anything since the skill never attempts to merge regardless, but kept for parity with
  SPEC-001's schema and as a documented intent if that ever changes.
- **`ignored_paths: [.tmp/prompts.md]`** — paths `implement-task` never treats as dirty-tree
  blockers (phase 1's start check, phase 3's pre-rebase stash). `.tmp/prompts.md` is the human's
  own prompt scratchpad, not part of any task's actual work — a fresh project scaffolded by
  `init-project` starts with this empty and adds project-specific paths the same way.
