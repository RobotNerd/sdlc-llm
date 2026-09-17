---
id: TASK-032
title: Hooks infrastructure + shared guardrails module + core git/gh guardrail hooks
type: feature
status: done
epic: EPIC-002
created: 2026-09-14
branch: task-032-hooks-infra-core-guardrails
pr: "https://github.com/RobotNerd/sdlc-llm/pull/59"
merge_commit: e3209d60ff3dfdc74fac42f3a76bba541d6fb1d9
blocked_by: []
blocks: [TASK-033, TASK-034, TASK-035, TASK-036, TASK-037, TASK-038, TASK-039, TASK-040, TASK-045]
---

# TASK-032: Hooks infrastructure + shared guardrails module + core git/gh guardrail hooks

## Description

Foundational slice for EPIC-002 (see SPEC-002). No blockers — proves the whole hooks mechanism
end to end with the guardrails that need no other in-flight task.

Introduce:
- `init-project/templates/settings.json` (new; copied to `.claude/settings.json`), registering
  `PreToolUse` hooks on `Bash`.
- A vendored hook-scripts location under `.claude/skills/init-project/` (naming to match the
  `vendored-sync` convention), copied into `.claude/hooks/` in the target project.
- `.tasks/bin/guardrails.py` — stdlib only, vendored the same way as `sync` — holding every
  guardrail as a pure function.

Three guardrails, as functions in `guardrails.py` plus their hook wiring:
1. Deny `gh pr merge` **unless** it is invoked through the future autonomous-merge path
   (SPEC-003/EPIC-003, not yet built) with a recorded critic approval and under that batch's
   merge cap. Concretely: allow only when a to-be-defined marker/record exists (e.g. a field or
   file EPIC-003's merge step writes just before calling `gh pr merge`) proving the call is the
   scripted, critic-gated path — not a bare model decision to merge. Until EPIC-003 lands, no such
   marker can ever exist, so this hook denies every `gh pr merge` unconditionally in practice; the
   exception is future-proofed now instead of built as an absolute deny that would need loosening
   later. Coordinate with EPIC-003 slice 7 (its own task) on the exact marker shape when that
   slice is implemented — don't invent one speculatively here beyond leaving the hook's structure
   able to check for it.
2. Deny `git push` of task work to `default_branch`. Allow only the phase-4 bookkeeping
   pattern: a push to `default_branch` whose diff touches only board-managed paths (`BOARD.md`,
   `EPIC-*.md`, a task file's `status`/`merge_commit`/`pr` fields, `.tasks/archive/**`).
3. Deny `git push --force` that isn't `--force-with-lease`, and deny `--force-with-lease` on any
   branch but the current task's own (cross-check `.tasks/config.md`'s `branch_prefix` and the
   in-progress task's `branch:`).

`scaffold.py`'s `cmd_run` gains these paths to its write set (and to `managed_files()` if that
helper already exists by the time this is implemented; otherwise the inline copy list).

This slice defines the shared-module pattern that TASK-024 (and any other script-extraction task
still open) is expected to call into for the same rules, rather than reimplementing them — see
SPEC-002's Alternatives for why.

## Acceptance criteria

- [ ] A fresh scaffold includes `.claude/settings.json` wired to hook scripts that call
      `.tasks/bin/guardrails.py`.
- [ ] Each of the three guardrails has a unit test on its pure function.
- [ ] Each has a hook-script test: feed the documented `PreToolUse` JSON shape on stdin, assert
      the `deny` decision for a violating `tool_input.command` and `allow` (or no output) for
      everything else.
- [ ] The `gh pr merge` guardrail's structure supports a future "verified critic-gated merge"
      exception without redesign — it denies unconditionally today (no marker can exist yet) but
      the check is written as "deny unless marker present," not a bare unconditional deny, so
      EPIC-003 slice 7 can wire in the real marker later without touching this hook's shape.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests per guardrail function with crafted git/task-file states (fixture repos in
   `tmp_path`, following the existing `tests/` conventions).
2. Hook-script tests: real subprocess invocation of the hook script with representative
   `PreToolUse` stdin JSON for `Bash` (`gh pr merge`, a `git push` to `default_branch` with
   non-board changes, a bare `--force` push, a `--force-with-lease` push on the wrong branch) and
   confirm denial; confirm an ordinary allowed command passes through untouched.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.
5. Scratch-branch dry run (throwaway branch off `origin/main`, deleted — not merged — when done):
   attempt a real `gh pr merge` in a live Claude Code session against a scaffolded scratch
   project and confirm the hook refuses it end to end. Human-run — record in the Worklog.

## Worklog

Implemented the full hooks-infra slice:

- `.tasks/bin/guardrails.py` (canonical) — `GuardrailResult(allow, reason)` plus three checks:
  `check_gh_pr_merge` (deny unless a `marker_present` flag is set -- nothing can set it yet, so
  it denies unconditionally today without being a bare unconditional check in shape),
  `check_push_to_default_branch` (fetches `<remote>/<default_branch>`, diffs `...HEAD`, and
  denies unless every changed path is `BOARD.md`, `EPIC-*.md`, `.tasks/archive/**`, or a task
  file whose only changed frontmatter fields -- via `sync.parse_frontmatter` -- are
  `status`/`merge_commit`/`pr`), and `check_force_push` (bare `--force` always denied;
  `--force-with-lease` denied unless its target branch matches an `in-progress` task's own
  `branch:`). `evaluate_bash_command` runs all three and loads `.tasks/config.md` itself.
- `.claude/hooks/pretooluse_bash.py` (canonical) — reads the `PreToolUse` stdin JSON, calls
  `evaluate_bash_command` for a `Bash` tool call, exits `2` + stderr reason to deny, `0` with no
  output to allow (or on anything it can't make sense of).
- `.claude/settings.json` (canonical) — registers that hook on `PreToolUse`/`Bash`, invoked as
  `python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pretooluse_bash.py` (no reliance on the exec bit).
- Vendored, portable copies (byte-identical, enforced by new tests):
  `.claude/skills/init-project/vendored-guardrails`,
  `.claude/skills/init-project/vendored-hooks/pretooluse_bash.py`,
  `.claude/skills/init-project/templates/settings.json`. Both the module and the hook script
  had their docstrings written id/citation-free from the start (portable surface).
- `managed_files()` in `init-project/scaffold.py` gained the three new entries (settings.json,
  vendored-guardrails -> `.tasks/bin/guardrails.py`, every file under `vendored-hooks/` ->
  `.claude/hooks/<name>`); `apply_managed_files` chmods the new executables 0o755 alongside
  `sync`. `SKILL.md`'s two managed-file descriptions updated to match.
- Extended `test_run_with_target_scaffolds_full_skill_table_into_a_separate_repo` to assert the
  three new files exist (and are executable where relevant) in a fresh scaffold.

Testing strategy:
1. Unit tests per guardrail function (`tests/test_guardrails.py`) against crafted `tmp_path`
   git fixtures (bare origin + clone, matching `test_implement_task_scaffold.py`'s
   conventions) -- covering both allow and deny cases for all three, including an
   archive-move edge case (delete + re-add under `.tasks/archive/`, allowed) and a sneaky
   task-title change hiding among an allowed field set (denied). **Pass.**
2. Hook-script tests: real subprocess invocation of `.claude/hooks/pretooluse_bash.py` with the
   documented `PreToolUse` stdin JSON shape, for `gh pr merge`, a `git push` to `main` with a
   non-board change, a bare `--force` push, and `--force-with-lease` on the wrong branch --
   all confirmed denied (exit 2, reason on stderr); an ordinary command and a non-`Bash` tool
   call confirmed to pass through with exit 0 and no output. **Pass.**
3. `python3 -m pytest -q` -- 438 passed (410 + 28 new), no regressions. **Pass.**
4. `python3 .tasks/bin/sync check` -- exit 0. **Pass.**
5. Scratch-branch dry run (human-run): a throwaway branch/PR off `origin/main` in this repo,
   fresh Claude Code session so `.claude/settings.json` was actually loaded, `gh pr merge`
   attempted for real -- **blocked as expected**, confirming Claude Code wires the hook up
   correctly end to end, not just that the script works in isolation. PR closed unmerged,
   scratch branch deleted locally and on `origin`. Confirmed by the human running it.

## Notes

- This is the foundational slice for EPIC-002 — every other task in the epic depends on it.
- The shared-module decision (hooks and skill scripts both call `guardrails.py`) is documented in
  SPEC-002; keep new guardrail logic there, not duplicated into a hook script or a skill script.
- Amended 2026-09-14 (before implementation started) to future-proof the `gh pr merge` guardrail
  for EPIC-003/SPEC-003's opt-in, critic-gated, capped auto-merge — see guardrail 1's Description
  and its acceptance criterion above. No behavior change today; this only shapes the check so it
  doesn't need a redesign later.
