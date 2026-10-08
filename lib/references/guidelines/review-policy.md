# Review policy

What the critic checks before a task merges, and what fails a review. The critic reads this doc, the task, its plan comments, the diff, the gate results, and the Architecture, Code style, and Documentation style docs. It never edits anything.

## Checklist

Each item is answered `true` or `false`. If an item can't be verified, it's `false`.

| Item | True when |
|------|-----------|
| `criteria_met` | The diff satisfies every acceptance criterion. |
| `docs_clean` | Docs changed wherever behavior changed. The doc text is concise and accurate, follows the Documentation style doc, and nothing stale is left behind. |
| `gates_passed` | Every quality gate reported passing. |
| `nothing_alarming` | No secrets, destructive or unrelated changes, or disabled tests or guardrails. |
| `plan_followed` | The diff matches the plan comment and any "Plan change" comments. |
| `scope_ok` | Every changed file is within the task's scope. Follow-up task creation is always allowed. |
| `sorted_order` | Lists and structures whose order doesn't matter are sorted, per the Code style doc (code) and the Documentation style doc (docs). |
| `tests_behavioral` | Committed tests exercise behavior through the public surface. Unit tests are committed only with a reason in the worklog. Tests from the test-writing step weren't edited during implementation without a loop-back. |

When the task changes a skill, the critic also checks the Skill authoring doc's rules. A broken rule is a finding.

## Severity

Every finding has a severity:

* `**important**`**:** breaks behavior, leaks data or secrets, fails an acceptance criterion, strays from the plan without a "Plan change" comment, or leaves a checklist item `false`.
* `**nit**`**:** anything else worth fixing: naming, wording, small style points.

Only an `important` finding rejects the task. Nits never reject.

**Nit cap:** report at most ten nits per review. Count the rest: "and 3 more nits".

## Excluded

The critic doesn't comment on:

* generated files
* anything a gate already enforces, such as formatting and lint
* the task's own requirements: whether the task was a good idea is out of scope

## Verdict

Exactly one JSON object:

```json
{
  "approve": false,
  "checklist": {
    "criteria_met": true,
    "docs_clean": true,
    "gates_passed": true,
    "nothing_alarming": true,
    "plan_followed": false,
    "scope_ok": true,
    "sorted_order": true,
    "tests_behavioral": true
  },
  "findings": [
    {"severity": "important", "text": "Touched src/billing/refund.py, which isn't in the plan and has no Plan change comment."},
    {"severity": "nit", "text": "The error message says 'tasks' where it means 'task'."}
  ],
  "nits_omitted": 0
}
```

* `approve` is `true` only when no finding is `important`.
* **Fail closed.** Any of these counts as a rejection: unparseable output, a missing or non-boolean checklist key, a finding without a valid severity, or `approve: true` alongside an `important` finding.
* The verdict is taken verbatim. It's never edited or summarized before it's judged.

## On rejection

The `important` findings are posted as a comment, and the task goes back to implementation (or to test writing, if the findings are about tests). A fresh critic reviews the next attempt.
