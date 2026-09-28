---
workflow_version: 1
test_command: .venv/bin/pytest
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
allow_auto_merge: true
ci_checks: [sync-check, test]
archive_done: true
tdd_enforced: true
context_usage_halt_pct: 85
token_budget_per_batch: null
autonomous_new_task_limit: 3
ignored_paths: [.tmp/prompts.md]
quality_gate_attempts: 3
guardrail_denial_attempts: 3
critic_rejection_attempts: 3
---

# Workflow config

Settings every skill and `sync` (`.tasks/bin/sync`) read.

## Key notes

- **`workflow_version`** — lets a future `upgrade` path migrate a repo whose workflow predates a schema change. Bump it whenever a breaking change lands in the data model or `sync`'s contract.
- **`lint_command`** — Linter command to run on the code. If null, no tool is configured.
- **`format_command`** — Code autoformatting tool to run.  If null, no tool is configured.
- **`docs_paths`** — files `implement-task` phase 3 considers touching as part of "update docs".
- **`docs_review_paths`** / **`docs_ignore_paths`** — files updated by the `review-docs` skill.
- **`remote` / `rebase_before_pr` / `merge_strategy` / `delete_branch_after_merge`** — the git automation settings for `implement-task`.
- **`ci_checks`** — the github actions workflows that must pass before a PR can be merged.
- **`allow_auto_merge`** — When true, the workflow automatically merges PRs it creates as long as CI checks pass and the critic agent approves the changes. If false, the human user manually merges PRs.
- **`tdd_enforced: true`** — follow a test-driven development workflow when true.
- **`ignored_paths: [.tmp/prompts.md]`** — paths the `implement-task` skill never treats as dirty-tree blockers.
- **`context_usage_halt_pct`** / **`token_budget_per_batch`** — `implement-task` batch mode's usage safety valve: crossing either threshold halts the batch. `null` token budget means no cap.
- **`autonomous_new_task_limit`** — max follow-up tasks that can be automatically created when running the `implement-task` skill. `null` removes the cap. Reaching the limit never halts the batch.
- **`quality_gate_attempts`** - max allowed failures of any of `test_command`/`lint_command`/`format_command`/`sync check` while implementing a task before interrupting the workflow
- **`guardrail_denial_attempts`** - max allowed failures of any `PreToolUse` hook while implementing a task before interrupting the workflow
- **`critic_rejection_attempts`** - max allowed rejections by the critic agent while implementing a task before interrupting the workflow
