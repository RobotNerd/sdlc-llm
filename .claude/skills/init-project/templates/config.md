<!--
  Template for .tasks/config.md, filled in by the init-project skill from
  its interview answers. `workflow_version` always starts at 1;
  `allow_auto_merge` always starts `false` (reinforces the never-merge
  guardrail — not something init-time should offer to turn on);
  `docs_review_paths`/`docs_ignore_paths` always start at the generic
  defaults below — a human adds project-specific paths later by editing
  config.md directly.
  Placeholders:
    {{test_command}}               e.g. `pytest`, `npm test`, or `null`
    {{lint_command}}                 e.g. `ruff check .`, or `null`
    {{docs_paths}}                    e.g. `[README.md]`
    {{default_branch}}               e.g. `main`
    {{branch_prefix}}                e.g. `task-`
    {{remote}}                       e.g. `origin`
    {{rebase_before_pr}}             `true` or `false`
    {{merge_strategy}}               `squash` | `merge` | `rebase`
    {{delete_branch_after_merge}}    `true` or `false`
    {{ci_checks}}                    e.g. `[]` or `[test]` — CI job names, if any exist yet
    {{archive_done}}                 `true` or `false`
-->
---
workflow_version: 1
test_command: {{test_command}}
lint_command: {{lint_command}}
docs_paths: {{docs_paths}}
docs_review_paths: [CLAUDE.md, README.md, .tasks/guidelines.md]
docs_ignore_paths: []
default_branch: {{default_branch}}
branch_prefix: {{branch_prefix}}
remote: {{remote}}
rebase_before_pr: {{rebase_before_pr}}
merge_strategy: {{merge_strategy}}
delete_branch_after_merge: {{delete_branch_after_merge}}
allow_auto_merge: false
ci_checks: {{ci_checks}}
archive_done: {{archive_done}}
---

# Workflow config

Per-project settings every skill and `.tasks/bin/sync` read. This is the seam SPEC-001 describes:
skill logic stays identical across projects, only this file changes.

## Key notes

- **`workflow_version`** — lets a future `upgrade` path migrate a repo whose workflow predates a
  schema change. Bump it whenever a breaking change lands in the data model or `sync`'s contract.
- **`lint_command`** — `null` means skills skip the lint step rather than fail on a command that
  doesn't exist. Set it once a linter is configured.
- **`docs_paths`** — files `implement-task` phase 3 considers touching as part of "update docs".
- **`docs_review_paths`** / **`docs_ignore_paths`** — `review-docs`'s own lists: which docs it
  always audits for staleness, and which paths it never scans into or flags. Not something
  init-time offers to change beyond these generic defaults.
- **`remote` / `rebase_before_pr` / `merge_strategy` / `delete_branch_after_merge`** — the git
  automation settings `implement-task`'s phases 1/3/4 read. `merge_strategy` documents how the
  *human* merges; the skill itself never merges.
- **`ci_checks`** — CI job names, so `implement-task` phase 4 (and a human eyeballing
  `gh pr checks`) can gate merge on them. Empty until CI exists.
- **`allow_auto_merge: false`** — reinforces the never-merge guardrail; not something init-time
  offers to change.
