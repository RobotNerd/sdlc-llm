---
id: TASK-021
title: "init-project: move deterministic scaffolding to a stdlib Python script"
type: refactor
status: todo
epic: EPIC-001
created: 2026-09-13
branch: task-021-init-project-scaffold-script
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-021: init-project: move deterministic scaffolding to a stdlib Python script

## Description

`init-project`'s `SKILL.md` currently has the LLM perform every step itself, including the fully
deterministic ones: creating directories, copying `guidelines.md`/`BOARD.md`/the task/epic/spec
templates/the PR template verbatim, substituting `config.md`'s placeholders, vendoring
`.tasks/bin/sync`, and running `sync`/`sync check`. None of that needs judgement — only the
interview (asking for `config.md` values, warning about missing `gh`) and the human confirmation
STOP genuinely need an LLM in the loop. Move everything else into a stdlib-only Python script
(`.claude/skills/init-project/scaffold.py`) that takes the interview's confirmed answers as input
and does the file writing + `sync` invocation itself; `SKILL.md` shrinks to the interview plus one
call to the script.

## Acceptance criteria

- [ ] `.claude/skills/init-project/scaffold.py` (stdlib only, no dependencies) performs every
      deterministic step currently in `SKILL.md`'s "Scaffold" and "Finish" sections: refuse if
      `.tasks/` already exists, confirm it's running inside a git repo, create `.tasks/`,
      `.tasks/bin/`, `.tasks/templates/`, `.github/`, render `config.md` from the supplied
      answers, copy `guidelines.md`/`BOARD.md`/`templates/{spec,epic,task}.md`/
      `pull_request_template.md` verbatim, vendor `sync` to `.tasks/bin/sync` (executable), then
      run `sync` followed by `sync check`.
- [ ] The script takes the interview's confirmed answers as input (e.g. a JSON file path or CLI
      flags) and never prompts interactively itself — all judgement/interview stays in
      `SKILL.md`, run by the LLM.
- [ ] `SKILL.md` is rewritten so its own body covers only: the `.tasks/`-exists STOP, preflight
      (git repo / `gh` warning — still an ASK), the interview, restate-and-STOP for confirmation,
      then a single invocation of `scaffold.py` with the confirmed answers. Every step now owned
      by the script is removed from the skill's prose rather than duplicated in both places.
- [ ] The script exits non-zero with a clear message on stderr (and writes nothing) if `.tasks/`
      already exists, if it isn't run inside a git repo, or if a required answer is missing.
- [ ] `sync check` exits `0` immediately after the script runs against a fresh scratch repo (same
      proof TASK-014 already established, now reachable without an LLM in the loop).
- [ ] Unit tests (`pytest`, consistent with `.tasks/bin/sync`'s own test setup) cover:
      `config.md` placeholder substitution, refusal when `.tasks/` exists, refusal when a required
      answer is missing.

## Testing strategy

1. Run `scaffold.py` directly (no LLM involved) against a scratch git repo with a sample answers
   file; confirm every listed file appears and `sync check` exits 0 immediately after.
2. Run it again in the same repo; confirm it refuses (non-zero exit, nothing written).
3. Run the new unit test suite covering config rendering and both refusal paths.
4. Re-read `SKILL.md` and confirm it's still a numbered checklist with STOP/ASK markers, now only
   around the genuinely non-deterministic parts (interview, `gh` warning, confirmation).

## Worklog

_(empty — appended during implementation)_

## Notes

- No dependencies — TASK-014 (which this refactors) is already done.
- Placed at the bottom of TODO (after TASK-018): the remaining three skills land first, this
  refactor comes after — decided with the user via `add-task`'s priority-placement step.
- Established via `add-task` (TASK-015) — its own testing-strategy scenarios are the template
  this task's testing strategy follows (scratch-repo run, second-run refusal, no LLM required).
