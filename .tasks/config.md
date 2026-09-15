---
workflow_version: 1
test_command: pytest
lint_command: null
docs_paths: [README.md, CLAUDE.md]
default_branch: main
branch_prefix: task-
remote: origin
rebase_before_pr: true
merge_strategy: squash
delete_branch_after_merge: true
allow_auto_merge: false
ci_checks: [sync-check, test]
archive_done: true
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
- **`docs_paths`** — files `implement-task` phase 3 considers touching as part of "update docs".
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
