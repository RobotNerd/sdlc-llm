---
name: plan
description: Turns an idea into Kaneo tasks, with an Outline spec when the work needs one. Use when the developer asks to plan, spec, design, scope, or break down a feature or a change, to add a task, or to continue or approve a plan.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *), Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/validate_draft.py *)
model: opus
---

# plan

Interviews the developer, writes a spec when the work needs one, and creates the epic and its tasks in Kaneo. The Kaneo project and the Outline collection are in `.sdlc/config.toml`.

## Hard rules

- The interview happens in an Outline questions doc, never in chat.
- Read `docs/guidelines/task-style.md`, `testing.md`, and `documentation-style.md` before writing a task, and `architecture.md` before a design. Read no guidelines from Outline.
- Every task passes the draft validator before anything is created.
- Work that fits one task gets no spec and no epic.
- Kaneo tools take a task's id, not its key: find a task by its `number`. Labels attach by the workspace label whose `taskId` is null. Outline doc text never starts with an H1, and lines that must stay apart need a blank line between them.

## Stop

To stop, run the notify script, then say what you need, with the doc or task link, and end your turn:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py --skill plan --kind <ASK or STOP> --text "<what's needed>" --link "<url>"
```

Stop for each interview round, for spec approval, for task review, and when a Kaneo or Outline call fails.

## Steps

On "continue" or "approved", find the plan in progress in the collection's `spec` folder, and pick up at its step.

1. **Interview.** Create a doc in the `spec` folder titled `Questions: <short name unique to the plan>`. Ask about intent, goals and non-goals, alternatives, architecture, and testing, skipping what the request already settles. Number the questions, give options with a recommendation, and put a `> Answer: TODO` line under each. Stop. On "continue", read the answers; append a new round for anything still open, and stop again. Skip the interview when the request settles everything.
2. **Spec,** only for work bigger than one task. Create a doc in the `spec` folder titled with the feature name. Its first line is `Status: drafting`, then the sections Intent, Goals and non-goals, Alternatives considered, Design, Architecture change, Deferred, and Open questions, with `None` in any that's empty. Move the questions doc under it. Stop for approval. On "approved", read the spec again, since the developer may have edited it; if Open questions isn't `None`, stop. Set the status to `approved`.
3. **Draft.** Split the work into vertical slices, ordered so each comes after the slices it needs. A changed architecture gets a task that updates `docs/guidelines/architecture.md`. Write each task by `task-style.md`. A manual test makes a validation task, last, blocked by each task with one. Each Deferred item becomes a deferred task. Then run, with the draft as JSON on one line in single quotes, each `'` in it written as `\u0027`:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/lib/validate_draft.py --save .sdlc/local/<slug>-draft.json --json '<draft>'
   ```

   Fix every error it prints, and run it again until it prints `{"ok": true}`.
4. **Create.** With a spec, create the epic in Planned from the Epic template in `task-style.md`, with the `epic` label and a link to the spec, and add `Epic: <link>` under the spec's status line. Create each task in Planned with its type label, skipping any the epic already has. Link each as a `subtask` of the epic, add a `blocks` relation from each blocker, and give the validation task the `validation` label. Set the spec's status to `tasks created`. Stop, listing each task's key, title, and link, for the developer to review.
5. **Release.** On "approved", move the tasks to the end of To Do, each after its blockers, the validation task last. Leave deferred tasks in Planned. Set the spec's status to `released`, and list the released tasks.
