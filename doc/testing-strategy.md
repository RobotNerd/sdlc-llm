# Testing strategy

How tasks in this repo are tested. The workflow is TDD (tests are written before the
implementation) and BDD (the tests that are kept describe behavior, not internals). The last
section is the plan for applying this strategy to `implement-task-v2` (EPIC-005).

## Test types

| Type | What it checks | Kept? |
|---|---|---|
| Behavioral, automated | One observable behavior, driven through a real entry point (a CLI or a script) | Committed |
| Behavioral, manual | One observable behavior, run by the human from a written procedure | Lives in the task file and the reports |
| Unit | Internals: functions, structure, wording | Throwaway by default (see [Unit tests](#unit-tests)) |

Behavioral tests of `implement-task-v2` will be manual until its behavior moves into scripts. A
manual test is the spec for the automated test that later replaces it.

## Behavioral test rules

1. **Test one behavior, observed from outside.** The observable result is what the person
   invoking the skill sees:
   - files, git state, `.tasks/` frontmatter, the board and reports
   - what the agent asks, and when and why it stops

   Never test internal structure, such as step headings, prose wording or function calls.
2. **Trace every test to an acceptance criterion.** Each criterion gets at least one test, and
   each test names the criterion it covers.
3. **Write it as Given / When / Then.**
   - **Given** is the preconditions: a concrete, reproducible setup.
   - **When** is exactly one action.
   - **Then** is the observable outcomes.
4. **Make pass or fail objective.** A Then states exact facts, for example "`origin/main` has
   one commit whose message cites the task". Never write "works correctly".
5. **Check lasting results, not wording.** The agent's output varies from run to run, so check
   the files, commits and frontmatter it leaves behind. When the behavior is a question or a
   stop, check that it happens and what it's about, not its exact phrasing.
6. **Check that the test survives a rewrite.** Ask: if the implementation were rewritten
   without changing what the user sees, would this test still pass? If not, it's a unit test.
7. **Cover failure paths too.** Test the happy path, plus every refusal, stop or error that the
   acceptance criteria describe.
8. **Keep tests independent.** Each test sets up its own state, and tests can run in any order.
   For manual tests, reset the scratch repo between tests.
9. **Keep tests short.** Under about 10 steps. Split anything longer.
10. **Name the behavior in the title.** Manual tests use "\<condition\> → \<outcome\>". Automated
    tests use `test_<outcome>_when_<condition>`.
11. **Manual and automated tests follow the same rules.**
12. **Automated behavioral tests drive the real entry point in a temporary repo.** Faking
    external systems (the network, `gh`, model or subagent calls) is acceptable for now.

**Minimum coverage:** at least one test per acceptance criterion, plus every stated failure path.

## Testing strategy format (task files)

A task's `## Testing strategy` section lists automated tests first, then manual tests. Every
test uses the same shape: a short summary labeled with Given/When/Then, followed by numbered
steps that give the detailed procedure.

```markdown
## Testing strategy

### Automated

#### <condition> → <outcome>   (criterion: <which one>)

Given: <preconditions, one line>
When: <the single action>
Then: <the observable outcomes, one line>

1. <setup step>
2. <action>
3. <check> — expected: <exact observable fact>

### Manual

#### <condition> → <outcome>   (criterion: <which one>) [blocks merge]

Given: ...
When: ...
Then: ...

1. ...
```

- Either subsection can be `None` when it has no tests.
- Gate steps that always apply, such as running `test_command` and `sync check`, go in a single
  closing line. They don't need a Given/When/Then block.
- The report's Manual testing section copies the manual tests in this same format.

## Blocking manual tests

- **Marking:** a manual test whose title ends in `[blocks merge]` must pass before its task
  merges. The label is added during planning, when the human reviews the generated tasks.
  Nothing adds it later.
- **Check at invocation:** after `build batch` validates the batch, `implement-task-v2` scans
  every task in it for `[blocks merge]` tests. If it finds any, it lists them and ASKs whether
  to proceed or adjust the batch.
- **At merge:** for a task with a blocking test, if the human chose to proceed, the agent pauses
  at `merge changes`, before squashing.
  - The pause kind is `manual_test_required`.
  - The agent presents the test and waits for the human's pass or fail.
  - Pass → merge.
  - Fail → the failure is recorded in the Worklog, the task isn't merged, and the batch stops.
    The batch report records the failure.

## Unit tests

- **Throwaway by default.** Write unit tests under `tests/throwaway/`. That directory is
  gitignored, and `test_command` still runs it. Delete the tests once the task's branch is
  squash-merged.
- **Why:** unit tests go stale and become a burden, and their count balloons with little value
  per test, which bloats context.
- **Committing one is rare.** It's allowed for code likely to change often, or for code judged
  likely to regress. Record the justification in the task's Worklog; the critic checks for it.

## Plan: applying this strategy to EPIC-005

| # | Change | Where |
|---|---|---|
| 1 | Replace the proposed `testing-strategy.md` content with this document's rules, format, blocking-test and unit-test sections. Add `manual_test_required` to the interrupt kinds. | SPEC-005 §Design |
| 2 | Rewrite every task's Testing strategy into the format above. Each keeps its current tests: Automated (throwaway unit tests aren't listed; they're chosen during implementation) and Manual. None is marked `[blocks merge]`; the human adds those during review. | TASK-073 – TASK-081 |
| 3 | `references/testing-strategy.md` is written from this document. | TASK-073 (acceptance criterion updated) |
| 4 | The report's Manual testing section uses the Given/When/Then + steps format. | TASK-074 (acceptance criterion updated) |
| 5 | After validation, `build batch` scans for `[blocks merge]` tests and ASKs whether to proceed or adjust the batch. | TASK-076 (new acceptance criterion and manual test) |
| 6 | The `manual_test_required` pause at `merge changes`: pass → merge; fail → the batch stops. | TASK-077 (new acceptance criterion and manual test) |
| 7 | `plan-feature` and `add-task` write Testing strategy sections in this format. `plan-feature`'s review STOP prompts the human to mark `[blocks merge]` tests. | New follow-up task, outside EPIC-005 (v1 and the other skills aren't in the epic's scope) |
| 8 | The task template's `## Testing strategy` placeholder shows the new format. | Same follow-up as #7 |

For now this document is the master copy, and the skill's reference doc is derived from it.
Whether that stays the arrangement, since vendored projects don't get `doc/`, will be revisited
later.
