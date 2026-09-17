---
id: TASK-062
title: "Worker scope fence: SubagentStop hook denying out-of-scope diffs"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-062-worker-scope-fence
pr: null
merge_commit: null
blocked_by: [TASK-054]
blocks: [TASK-063]
---

# TASK-062: Worker scope fence: SubagentStop hook denying out-of-scope diffs

## Description

Blocked on TASK-054 (agent roster) — this fences the `worker-*` agents it defines.

"Never touch files outside the current task's scope" is currently a prose-only guardrail
(`.tasks/guidelines.md`'s "Guardrails that need your judgement" section states it can't be
hook-enforced because "no hook can supply the judgement" of what counts as in-scope for a given
task). Once a worker is a distinct subagent (this epic's whole premise), its declared task IS a
concrete, checkable scope — so this becomes hook-enforceable the same way EPIC-002 made other
prose guardrails structural.

New `.claude/hooks/subagentstop_scope_fence.py` firing on `SubagentStop`, plus
`guardrails.evaluate_subagent_stop(subagent_type, task_id, cwd)` in `.tasks/bin/guardrails.py`. When
the completing subagent is a `worker-*` variant: run `git diff --name-only` against the current
branch, compare against the task's declared scope (the task file's Acceptance criteria/Testing
strategy content, or an explicit scope list if one is added), and deny the subagent's completion
if any changed path falls outside it — following the existing `GuardrailResult` pattern
(`allow: bool, reason: str`) rather than raising.

## Acceptance criteria

- [ ] A worker subagent that only touches files within its task's declared scope completes
      normally — no false-positive denial on a scoped, correct change.
- [ ] A worker subagent whose diff touches a file outside its task's declared scope is denied at
      `SubagentStop`, with a reason naming the offending path(s).
- [ ] The fence only applies to `worker-*` subagent types — it does not fire for the orchestrator or
      critic (which have no "task scope" of their own in the same sense).
- [ ] The hook script and `.claude/settings.json`'s `SubagentStop` registration are vendored
      byte-identically into `init-project/vendored-hooks/` and `init-project/templates/settings.json`,
      matching the existing pattern for the other guardrail hooks.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on `evaluate_subagent_stop` against fixture diffs: in-scope-only (allow),
   one-file-out-of-scope (deny, correct file named), and a non-`worker-*` subagent type (always
   allow, untouched by this check).
2. Hook-script tests: real subprocess invocation of `subagentstop_scope_fence.py` with representative
   `SubagentStop` payloads and varied working-tree fixtures, matching the existing
   `pretooluse_bash.py`/`pretooluse_edit_write.py` test convention.
3. Byte-identity tests: vendored hook copy matches the canonical one; `.claude/settings.json` and
   `init-project/templates/settings.json` carry matching `SubagentStop` registrations — following
   `tests/test_guardrails.py:301-310`'s existing pattern.
4. `python3 -m pytest -q` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- This closes the one guardrail `.tasks/guidelines.md` currently flags as needing human judgement
  rather than a hook — only possible now because a worker's task boundary is concrete in a way a
  single self-directed session's boundary wasn't.
- Registering a new hook requires updating both `.claude/settings.json` and
  `init-project/templates/settings.json` identically, plus the vendored hook copy and the expected
  file list in `tests/test_init_project_scaffold.py` — see this epic's registration checklist.
