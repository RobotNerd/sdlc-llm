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
* Skill evals

## Test types

| Type | What it checks | Kept? |
|------|----------------|-------|
| Behavioral, automated | One observable behavior, driven through a real entry point (a CLI or a script) | Committed |
| Agent-run check | One observable behavior, checked by the agent against a real system, such as CI's result or the tracker's state | Recorded in the report |
| Behavioral, manual | One observable behavior, run by the human from a written procedure | Lives in the task and the reports |
| Skill eval | One skill behavior, run with `claude plugin eval` against a scratch repo and mocked backends | Committed |
| Unit | Internals: functions, structure, wording | Throwaway by default |

A manual test is the spec for the automated test or eval that later replaces it.

## Behavioral test rules


 1. **Test one behavior, observed from outside.** The observable result is what the person invoking the code sees:
    * files, git state, tracker and doc-store state, reports
    * what the agent asks, and when and why it stops

    Never test internal structure, such as step headings, prose wording or function calls.
 2. **Trace every test to an acceptance criterion.** Each criterion gets at least one test, and each test names the criterion it covers.
 3. **Write it as Given / When / Then.**
    * **Given** is the preconditions: a concrete, reproducible setup.
    * **When** is exactly one action.
    * **Then** is the observable outcomes.
 4. **Make pass or fail objective.** A Then states exact facts, for example "the default branch has one new commit whose message cites the task". Never write "works correctly".
 5. **Check lasting results, not wording.** Agent output varies from run to run, so check the files, commits and backend state it leaves behind. When the behavior is a question or a stop, check that it happens and what it's about, not its exact phrasing.
 6. **Check that the test survives a rewrite.** Ask: if the implementation were rewritten without changing what the user sees, would this test still pass? If not, it's a unit test.
 7. **Cover failure paths too.** Test the happy path, plus every refusal, stop or error that the acceptance criteria describe.
 8. **Keep tests independent.** Each test sets up its own state, and tests can run in any order. For manual tests, reset the scratch repo and sandbox between tests.
 9. **Keep tests short.** Under about 10 steps. Split anything longer.
10. **Name the behavior in the title.** Manual tests use "<condition> → <outcome>". Automated tests use `test_<outcome>_when_<condition>`.
11. **Manual and automated tests follow the same rules.**
12. **Automated tests drive the real entry point in a temporary repo.** External systems (Kaneo, Outline, notifiers, model calls) are replaced by fakes. Contract tests run the same code against the real tools, on demand.

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

**Why manual:** <the exact behavior, and why no automated test, eval, or agent-run check can observe it>

#### <condition> → <outcome>   (criterion: <which one>)

* **Given:** ...
* **When:** ...
* **Then:** ...

1. <step>, with its command in a code block indented under the step
2. <check> — expected: <exact observable fact>
```

* Given / When / Then are bullets, so Outline and Kaneo don't merge them into one line.
* Manual steps follow "Formatting for the reader" in the Documentation style doc: each command, prompt, and pasted value in its own code block or list, and commands paste-ready.
* Automated covers everything the agent runs without the human: tests, evals, and agent-run checks.
* The Manual section opens with **Why manual:**, one line per test when there are several.
* A blocking test ends its title with `[blocks merge]`. Only the human decides that a test blocks (see Manual tests).
* Either subsection can be `None` when it has no tests.
* Gates that always apply, such as `test_command`, lint, and the reference check, go in one closing line. They don't need a Given/When/Then block.
* The per-task report's Manual testing section copies the manual tests in this same format.

## Manual tests

* **A last resort.** Write a manual test only for a behavior that no automated test, eval, or agent-run check can observe. If part of a behavior can be automated, automate that part, and keep the manual test to the rest.
  * Good reasons: the behavior needs the real tracker or doc store (evals mock them), a notification arriving on a real device, or a judgment only the human can make.
  * Not a reason: the agent can run it itself. Reading CI's result, querying the tracker, or checking a file is an agent-run check, and goes under Automated.
* **Why manual.** The Manual section opens with a **Why manual:** line for each test: the exact behavior it checks, and why that can't be checked automatically. The human reads it while reviewing the planned tasks, and decides whether the test blocks.
* **Deferred by default.** A manual test runs at the end of its epic, in the epic's validation task (see the Task style guide). Its own task merges without it. Write its steps against the default branch, since it runs after the merge.
  * A task with no epic: its manual tests are listed in the batch report's Manual testing section, and run after the batch.
* **Blocking.** A manual test whose title ends in `[blocks merge]` must pass before its task merges. Only the human decides that a test blocks, while reviewing the planned tasks or when asked by the skill that writes the task. Mark it blocking only when later work depends on the result, because it ends a batch at its task.

## Manual tests in a batch

A batch runs to completion without the human, unless something goes wrong.

* **At batch start:** after the batch is validated, its tasks are scanned in order for `[blocks merge]` tests. The first task with one becomes the batch's last task.
  * If that shortens the batch, the human is told before any work starts: which task now ends the batch, which requested tasks are dropped, and why. They choose to continue with the shorter batch, or cancel it.
  * If it's already the last task, the batch starts, and says it will end with a manual test.
* **At the end:** the batch pauses before squashing that task, with the interrupt kind `manual_test_required`. The human runs the test and reports pass or fail.
  * Pass → merge, and the batch completes.
  * Fail → the failure is recorded in the worklog, the task isn't merged, and the batch stops. The batch report records the failure.
* **Validation tasks** have nothing to merge. The batch pauses on one the same way, and on pass moves it to done.

## Unit tests

* **Throwaway by default.** Write unit tests under the throwaway test directory. It's gitignored, and the test command still runs it. Delete the tests once the task's branch is squash-merged.
* **Why:** unit tests go stale and become a burden, and their count balloons with little value per test, which bloats context.
* **Committing one is rare.** It's allowed for code likely to change often, or code judged likely to regress. Record the reason in the worklog; the critic checks for it.

## Protecting failing tests

* Behavioral tests are written and committed first, and must fail for the expected reason: an assertion, not an import error or a missing fixture.
* During implementation, those tests aren't edited. Fix the code, not the test.
* If a test is wrong, go back to the test-writing step, change it there, and record why in the worklog.
* Never skip, delete, or weaken a failing test to get a green run.

## Skill evals

* Skill evals run with Claude Code's `claude plugin eval`. The rules above apply.
* **One case per directory** under `evals/<skill>/<case>/`:
  * `prompt.md`: the prompt as a user would type it, plus `max_turns`, `timeout_seconds`, `allowed_tools`, and `tags: [<skill>]` in its frontmatter. The tag lets the gate run one skill's cases.
  * `case.yaml`: a `scaffold_script` that builds the scratch repo (the Given)
  * `graders/`: one check per file (the Then)
* **Graders check lasting results:**
  * `tool_used` and `tool_order` on the Kaneo and Outline MCP calls
  * a question or a stop: `AskUserQuestion` isn't available in an eval run, so Claude asks in its final message instead. Grade the question with an `llm` grader on `last_message`, and add a `tool_used` grader with `min: 0` and `max: 0` on the call that mustn't happen before the answer, such as creating the task.
  * `regex` or `file_exists` on files the run leaves behind
  * `llm` only for short output, with a rubric written as concrete PASS and FAIL conditions. Not on `mock_calls` when a call carries a long document: the judge sees only part of the calls. Use `input_match` on a `tool_used` grader instead.
  * There are no custom-code graders. When a check needs code, the prompt asks Claude to write the result to a file, and a `regex` grader reads that file.
* **Backends are mocked.** Each Kaneo or Outline MCP tool a skill calls gets a file under `evals/mocks/<server>/`. Put an `expect:` guard on any mock whose arguments matter, so a wrong call fails the run.
* **Triggering:** each case has a `tool_used: Skill` grader for its skill, and prompts vary their wording. At least one case per skill is a request that must not trigger it (`min: 0`, `max: 0`, `arm: both`).
* **Running the suite:**
  * Per-task gate: run once, with no baseline.

    ```bash
    claude plugin eval . --tag <skill> --runs 1 --ablation none --scaffold
    ```
  * At epic close: run the full suite with the default three runs and the no-plugin baseline, with a cost ceiling.

    ```bash
    claude plugin eval . --max-cost-usd <ceiling> --scaffold
    ```
  * `--scaffold` runs each case's scaffold script. Without it, every case starts in an empty directory.
  * Pin the model in both, so a model release isn't mistaken for a regression.
* Before trusting a low score, check the run's error for a usage-limit message. A limit hit mid-suite scores later runs 0 without marking the suite partial.
* Each skill starts with at least three evals, written before its prose. New evals come from misbehavior seen in real use. Evals that no longer fail anything can be retired.
* When a task changes a skill, that skill's evals run as a gate. The full suite runs when an epic closes.
