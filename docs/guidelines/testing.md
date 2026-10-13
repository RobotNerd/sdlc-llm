# Testing strategy

How work is tested. The workflow is TDD (tests are written before the implementation) and BDD (the tests that are kept describe behavior, not internals).

## Contents

* Test types
* Behavioral test rules
* Testing strategy format (tasks)
* Manual tests
* Manual tests in a batch
* Unit tests
* Protecting failing tests
* Testing skills

## Test types

| Type | What it checks | Kept? |
|------|----------------|-------|
| Behavioral, automated | One observable behavior, driven through a real entry point (a CLI or a script) | Committed |
| Agent-run check | One observable behavior, checked by the agent against a real system, such as CI's result or the tracker's state | Recorded in the task comment |
| Behavioral, manual | One observable behavior, run by the developer from a written procedure | Lives in the task |
| Unit | Internals: functions, structure, wording | Throwaway by default |

A manual test is the spec for the automated test that later replaces it.

## Behavioral test rules

1. **Test one behavior, observed from outside.** The observable result is what the person invoking the code sees:
   * files, git state, tracker and Outline state
   * what the agent asks, and when and why it stops

   Never test internal structure, such as step headings, prose wording or function calls.
2. **Trace every test to an acceptance criterion.** Each criterion gets at least one test, and each test names the criterion it covers.
3. **Write it as Given / When / Then.**
   * **Given** is the preconditions: a concrete, reproducible setup.
   * **When** is exactly one action.
   * **Then** is the observable outcomes.
4. **Make pass or fail objective.** A Then states exact facts, for example "the branch has one new commit whose message cites the task". Never write "works correctly".
5. **Check lasting results, not wording.** Agent output varies from run to run, so check the files, commits and tracker state it leaves behind. When the behavior is a question or a stop, check that it happens and what it's about, not its exact phrasing.
6. **Check that the test survives a rewrite.** Ask: if the implementation were rewritten without changing what the user sees, would this test still pass? If not, it's a unit test.
7. **Cover failure paths too.** Test the happy path, plus every refusal, stop or error that the acceptance criteria describe.
8. **Keep tests independent.** Each test sets up its own state, and tests can run in any order. For manual tests, reset the sandbox between tests.
9. **Keep tests short.** Under about 10 steps. Split anything longer.
10. **Name the behavior in the title.** Manual tests use "<condition> → <outcome>". Automated tests use `test_<outcome>_when_<condition>`.
11. **Manual and automated tests follow the same rules.**
12. **Automated tests drive the real entry point in a temporary repo.** External systems (Kaneo, Outline, notifiers, model calls) are replaced by fakes.

**Minimum coverage:** at least one test per acceptance criterion, plus every stated failure path.

## Testing strategy format (tasks)

A task's `## Testing strategy` section lists automated tests first, then manual tests. Every test has the same shape: a Given/When/Then summary, then numbered steps.

```markdown
## Testing strategy

### Automated

#### <condition> → <outcome>   (criterion: <which one>)

* **Given:** <preconditions, one line>
* **When:** <the single action>
* **Then:** <the observable outcomes, one line>

1. <setup step>
2. <action>
3. <check> — expected: <exact observable fact>

### Manual

**Why manual:** <the exact behavior, and why no automated test or agent-run check can observe it>

#### <condition> → <outcome>   (criterion: <which one>)

* **Given:** ...
* **When:** ...
* **Then:** ...

1. <step>, with its command in a code block indented under the step
2. <check> — expected: <exact observable fact>
```

* Given / When / Then are bullets, so Outline and Kaneo don't merge them into one line.
* Manual steps follow "Formatting for the reader" in `documentation-style.md`: each command, prompt, and pasted value in its own code block or list, and commands paste-ready.
* Automated covers everything the agent runs without the developer: tests and agent-run checks.
* The Manual section opens with **Why manual:**, one line per test when there are several.
* A blocking test ends its title with `[blocks merge]`. Only the developer decides that a test blocks (see Manual tests).
* Either subsection can be `None` when it has no tests.
* Checks that always apply, such as the test command, lint, and the reference check, go in one closing line. They don't need a Given/When/Then block.

## Manual tests

* **A last resort.** Write a manual test only for a behavior that no automated test or agent-run check can observe. If part of a behavior can be automated, automate that part, and keep the manual test to the rest.
  * Good reasons: the behavior is a live skill session against the real Kaneo and Outline, a notification arriving on a real device, or a judgment only the developer can make.
  * Not a reason: the agent can run it itself. Reading CI's result, querying the tracker, or checking a file is an agent-run check, and goes under Automated.
* **Why manual.** The Manual section opens with a **Why manual:** line for each test: the exact behavior it checks, and why that can't be checked automatically. The developer reads it while reviewing the planned tasks, and decides whether the test blocks.
* **Deferred by default.** A manual test runs at the end of its epic, in the epic's validation task (see `task-style.md`). Its own task merges without it. Write its steps against the default branch, since it runs after the merge.
  * A task with no epic: its manual tests run after its pull request merges, and the task's report comment lists them.
* **Blocking.** A manual test whose title ends in `[blocks merge]` must pass before its task merges. Only the developer decides that a test blocks, while reviewing the planned tasks. Mark it blocking only when later work depends on the result, because it ends a batch at its task.

## Manual tests in a batch

A batch runs to completion without the developer, unless something goes wrong.

* **A blocking test:** `work` commits the task, pushes the branch, and opens the pull request, then stops and says where the test's steps are. The tasks after it wait for the next batch.
  * Pass → the developer merges, and says "merged".
  * Fail → the developer comments on the task, and the fix goes on the same branch.
* **Validation tasks** have nothing to implement. `work` stops on one the same way, and the developer moves it to done when every test passes.

## Unit tests

* **Throwaway by default.** Write unit tests under the throwaway test directory, `throwaway_test_dir` in `.sdlc/config.toml`. It's gitignored, and the test command still runs it. Delete the tests once the task's pull request merges.
* **Why:** unit tests go stale and become a burden, and their count balloons with little value per test, which bloats context.
* **Committing one is rare.** It's allowed for code likely to change often, or code judged likely to regress. Record the reason in a task comment; the review checks for it.

## Protecting failing tests

* Behavioral tests are written first, and must fail for the expected reason: an assertion, not an import error or a missing fixture.
* During implementation, those tests aren't edited. Fix the code, not the test.
* If a test is wrong, change it on purpose, and record why in a task comment.
* Never skip, delete, or weaken a failing test to get a green run.

## Testing skills

* A skill's structure is checked automatically: `tests/test_plugin_layout.py` checks its frontmatter and length.
* A skill's behavior is a live session against the real Kaneo and Outline, so it's checked by manual tests in the sandbox, and by use.
* A misbehavior seen in use becomes a fix, and a manual test when one can catch it again.
