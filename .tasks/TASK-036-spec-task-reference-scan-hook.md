---
id: TASK-036
title: SPEC/TASK-reference scan hook (repo-only, never copied)
type: feature
status: in-review
epic: EPIC-002
created: 2026-09-14
branch: task-036-spec-task-reference-scan-hook
pr: "https://github.com/RobotNerd/sdlc-llm/pull/69"
merge_commit: null
blocked_by: [TASK-032, TASK-027]
blocks: [TASK-039, TASK-040]
---

# TASK-036: SPEC/TASK-reference scan hook (repo-only, never copied)

## Description

Blocked on TASK-032 (hooks infrastructure) and TASK-027 (strip project-specific references from
the portable surface — so this hook starts from a clean baseline instead of failing on day one).

A script (e.g. `.dev/hooks/check-portable-references.py`, **outside** `.claude/hooks/** ` so it is
trivially excluded from `init-project`'s copy list and from `upgrade`'s managed files) that greps
the portable surface (`.claude/skills/**`, as established in TASK-027) for
`\b(TASK|EPIC|SPEC)-\d{3}\b` and denies `gh pr create` if any are found, listing the offending
files/lines.

Registered **only in this repo's own** `.claude/settings.json` — not in
`init-project/templates/settings.json` — so a scaffolded project never inherits a check that
would be meaningless (and possibly always-failing, since `TASK-NNN` placeholders are legitimate
template content) in someone else's repo.

## Acceptance criteria

- [x] The hook denies `gh pr create` when a concrete `TASK-`/`EPIC-`/`SPEC-` id exists under
      `.claude/skills/` in the diff.
- [x] The hook passes on the current (post-TASK-027) tree.
- [x] The hook file and its `.claude/settings.json` registration are absent from every file
      `init-project`/`upgrade` write to another repo.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit test on the grep/scan function with fixture files containing and lacking concrete ids.
2. A test asserting this hook's own path is excluded from `managed_files()`'s output (or the
   scaffold's copy list) and from a freshly-scaffolded project's tree — extends TASK-029's
   data-loss-guard test with one more excluded path.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- Added `.dev/hooks/check-portable-references.py`: a `PreToolUse`/`Bash` hook that, on
  `gh pr create`, scans `.claude/skills/**` (via `find_id_offenders`) for concrete
  `TASK-`/`EPIC-`/`SPEC-NNN` ids and denies with the offending files/lines if any are found.
  Reuses `strip-project-references/scaffold.py`'s existing `scan_surface` detector (the same
  one `tests/test_portable_surface.py` already uses) rather than reimplementing detection, so
  this gate and that interactive tool can't drift apart. Resolves that script from its own fixed
  location (`Path(__file__).resolve().parents[2]`), not from a tool call's `cwd` — this check is
  repo-only and never runs against another project.
- `.dev/hooks/**` lives entirely outside every directory `managed_files()` (in
  `init-project/scaffold.py`) ever scans (`.claude/skills/**`, `.claude/hooks/**`, and a handful
  of other named files) — excluded from vendoring by construction, no exclusion list needed.
- Registered the new hook as a second entry under `.claude/settings.json`'s existing `Bash`
  matcher — **only** in this repo's own `.claude/settings.json`, not in
  `.claude/skills/init-project/templates/settings.json` (the portable template stays untouched).
- Fixed a now-invalid assumption in `tests/test_guardrails.py`:
  `test_settings_json_template_is_byte_identical_to_this_repos_own` asserted the template and
  this repo's own `settings.json` are always byte-identical — true for every prior guardrail
  hook (all portable) but now broken on purpose by this task's repo-only entry. Replaced with
  `test_settings_json_template_matches_this_repos_own_minus_the_repo_only_hook`, which parses
  both as JSON, confirms the repo-only hook entry is present in the canonical file's `Bash`
  hooks list, strips it back out, and asserts structural equality with the template — so future
  *portable* hook additions still get caught if the two ever drift for a different reason.
- Added `tests/test_check_portable_references.py` (16 tests): `find_id_offenders` unit tests
  (clean tree, a bare id, multiple id kinds, banned-phrase-only lines excluded, the
  `strip-project-references` skill's own directory excluded), hook-script subprocess tests
  (ignores non-`gh pr create`/non-`Bash` calls, denies with the id+location in `stderr`, allows a
  clean surface, allows when no `.claude/skills/` dir exists at all, survives malformed stdin), a
  test against this repo's real `.claude/skills/` tree (clean, as expected post-TASK-027), and
  three tests confirming the vendoring exclusion (script path outside `.claude/**`'s vendored
  subtrees; portable template lacks the registration; this repo's own settings.json has it).
- Full suite: `.venv/bin/pytest -q` → 526 passed (510 existing + 16 new), no existing test
  behavior changed except the one now-corrected assertion above.
- `python3 .tasks/bin/sync check` → exit 0.

## Notes

- Depends on TASK-032's `guardrails.py` module/hook-wiring and TASK-027's cleanup.
- Deliberately the one hook in this epic that is never portable — see SPEC-002's Goals.
