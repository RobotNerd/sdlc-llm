---
id: TASK-057
title: "Pre-send safety: opt-in flag, secret scan, diff-size cap for external review"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-057-pre-send-safety
pr: null
merge_commit: null
blocked_by: [TASK-055]
blocks: [TASK-063]
---

# TASK-057: Pre-send safety: opt-in flag, secret scan, diff-size cap for external review

## Description

Blocked on TASK-055 (OpenRouter client) — this gates every call that client can make.

Sending a diff (and its surrounding context) to a third-party provider is an outward-facing,
effectively irreversible action once it leaves the box. Three checks, all run before any
`openrouter.send()` call:

1. **Opt-in required.** `external_review` (from TASK-054's config keys) must be `true`. When
   `false` (the default), the critic client (TASK-056) must fall back to the Anthropic path or
   refuse — it must never silently send externally anyway.
2. **Secret scan.** Scan the diff and any composed prompt context for credential-shaped patterns
   (API keys, tokens, private key headers, common cloud-provider secret formats) before sending;
   refuse and report on a hit, naming the file/line, not the secret's value.
3. **Diff-size cap.** A configurable `max_review_bytes` (new config key, template-fixed with a
   sane default). Exceeding it **halts and asks the human** rather than silently truncating the
   diff — a truncated diff sent for review is worse than no review, since it can pass a check while
   hiding the part that matters.

Also add a `PreToolUse`/Bash guardrail rule in `.tasks/bin/guardrails.py` denying any command that
would invoke `critic.py` with an external provider when `external_review` is `false` in
`.tasks/config.md` — the structural backstop for when the model bypasses the script's own check.

## Acceptance criteria

- [ ] With `external_review: false` (default), no code path reaches `openrouter.send()` — verified
      by a test that patches `send()` to raise if called and confirms it is never invoked.
- [ ] A diff or context containing a recognizable secret pattern is refused before sending, with a
      message naming the location, never echoing the secret value itself.
- [ ] A diff exceeding `max_review_bytes` halts with a clear message and does not truncate or send
      a partial diff.
- [ ] The `PreToolUse`/Bash hook denies invoking the critic against an external provider when
      `external_review` is `false`, even if called directly via `Bash` rather than through the
      skill.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the secret scanner against fixture diffs: known secret-shaped strings (API key
   formats, private-key PEM headers, common token prefixes) are caught; ordinary code (including
   strings that merely look sensitive-adjacent, e.g. a variable named `api_key` with no real value)
   is not a false positive.
2. Unit tests on the size cap: a diff at/under the limit passes through unchanged; one over it halts
   without ever calling `send()`.
3. Unit tests on the opt-in gate: `external_review: false` blocks the call; `true` allows it to
   proceed to the other two checks.
4. Hook-script tests: real subprocess invocation of the `PreToolUse`/Bash hook with a command
   invoking the critic externally, against `external_review: false`/`true` config fixtures.
5. `python3 -m pytest -q` — full suite green.
6. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- This is a guardrail task by nature (SPEC-002's "define guardrail logic once" pattern applies
  here too): the deterministic scan/cap logic lives in a script; the hook is the structural
  backstop for the same rule.
- The secret-pattern list should be a data table (list of regexes with names), not scattered
  literals, so it's easy to extend without touching the scanning logic itself.
