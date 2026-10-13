---
name: plan-feature
description: Plans a feature through a spec in Outline. Use when the developer asks to plan, spec, design, or scope a feature, or something too big for one task, or to continue, resume, or approve a feature plan, or to break an approved spec into tasks and release them.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *), Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/validate_draft.py *)
---

# plan-feature

Turns a feature idea into an approved spec in Outline, through an interview in a questions doc, then into an epic and tasks in Kaneo.

## Parameters

| Parameter | Default | Skips |
|---|---|---|
| feature | none | the request. With none, the skill resumes a spec in progress (step 2). |
| epic | none | creating an epic in step 9. An existing epic the tasks join, as a task key such as `KEY-12`. |

## Asking and stopping

- **ASK** means: run the notify script with `--kind ASK`, then ask with `AskUserQuestion`, with the recommended answer first. If `AskUserQuestion` isn't available, ask in your reply and end your turn. Never guess an answer.
- **STOP** means: run the notify script with `--kind STOP`, then say what's needed, and end your turn.
- **Notify script,** run with every ASK and STOP, even when notifications look off in the config: the script checks that itself. Pass the doc or task the developer needs with `--link`. If it fails or can't run, carry on.

  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py --skill plan-feature --kind <ASK or STOP> --text "<what's needed>" --link "<doc url>"
  ```

The interview always goes through the questions doc in Outline, never the terminal.

## The spec

The spec is a doc under `spec/`, titled with the feature name only, such as `Export tasks to CSV`. Its questions doc is nested under it, titled `<feature> questions`. The spec's first line is its status line:

```markdown
Status: interviewing
```

| Status | Means | Resume at |
|---|---|---|
| `interviewing` | The questions doc has a round open. | step 3, item 3 |
| `drafting` | The spec is drafted and waiting for approval. | step 5, item 4 |
| `approved` | The spec is approved. | step 7 |
| `tasks created` | The tasks are created, waiting for review. | step 11 |
| `released` | Done. Never resumed. | — |

Change the status with DocStore: `update_doc`, `findText` the whole old status line, and `text` the new one.

Once the tasks are created, the line after the status line links the epic:

```markdown
Epic: [<key> <epic title>](<epic url>)
```

## Steps

Read the [Outline backend map](../../lib/references/backends/outline.md) before the first DocStore call. Every DocStore operation below is done the way it says. Values in angle brackets come from `.sdlc/config.toml`.

Read guideline docs from the repo, at the step that needs them:

| Doc | File |
|---|---|
| Testing strategy | `docs/guidelines/testing.md` |
| Documentation style | `docs/guidelines/documentation-style.md` |
| Architecture | `docs/guidelines/architecture.md` |
| Task style guide | `docs/guidelines/task-style.md` |

Copy this checklist into your reply, and tick each step off as you finish it:

```
- [ ] 1. Check the repo
- [ ] 2. Find or start the spec
- [ ] 3. Interview
- [ ] 4. Check the architecture
- [ ] 5. Draft the spec
- [ ] 6. Approve
- [ ] 7. Decompose
- [ ] 8. Validate the draft
- [ ] 9. Create the tasks
- [ ] 10. Review
- [ ] 11. Release
```

### 1. Check the repo (low)

1. Read `.sdlc/config.toml` at the repo root. If it's missing, **STOP**: the repo needs `/sdlc-llm:setup-project` first.
2. DocStore: `find_doc` `spec`. This also checks that Outline answers. If the call fails, **STOP**, and tell the developer to run `/mcp` to see why. If there's no `spec` doc, DocStore: `create_doc` titled `spec` at the top of the collection.

### 2. Find or start the spec (low)

**Resume** when the request names no new feature: no argument, a reply such as "continue" or "approved", or a spec named by its title or link.

1. DocStore: `list_children` of `spec`. These are the specs. When the request names one, take it, and skip to item 4.
2. DocStore: `get_doc` each spec, and read its status line. Leave out the `released` ones.
3. With one left, take it. With several, **ASK** which one, listing each by title and status. With none, **ASK** what feature to plan.
4. Go to the step its status names in the table above. A reply such as "approved" goes with it.

**Start** a new spec when the request describes a feature:

1. Name the feature in a few words, as a noun phrase or imperative, such as `Export tasks to CSV`. If a spec with that title exists, resume it instead.
2. DocStore: `create_doc` under `spec`, titled with the feature name, with this text:

   ```markdown
   Status: interviewing

   ## Request

   > <the developer's request, word for word>
   ```

3. DocStore: `create_doc` under the spec, titled `<feature> questions`. Its text is round 1 (step 3).

### 3. Interview (high)

Read the Testing strategy doc now, for the testing questions.

1. **Write round 1.** It asks about every one of these topics, under these headings, in this order, at least one question each. When the request already settles a topic, ask to confirm it, with that as the recommendation.

   - `### Intent`: the problem, the outcome, the users and systems it affects, and the constraints
   - `### Goals and non-goals`
   - `### Alternatives`: the other ways to get the outcome, and why not
   - `### Architecture`: where the code goes, and what changes in the components or their boundaries. Read the code the feature touches first.
   - `### Testing`: how each goal is tested, automated first. A manual test only for what no automated test, eval, or agent-run check can observe, with why.

   Each question has this shape, numbered Q1, Q2, … through the whole doc:

   ```markdown
   ## Round 1

   ### <topic>

   **Q1.** <question>

   * <option> (recommended)
   * <option>

   > Answer: TODO
   ```

   Give options and a recommendation where there are any. Every question has its own `> Answer: TODO` line.
2. **STOP**, naming the questions doc by its title and link: the developer answers in Outline, replacing each `TODO` with an answer or "agree", then says "continue".
3. **On "continue",** DocStore: `get_doc` the questions doc. An answer that still reads `TODO` is unanswered, and "agree" means the recommendation.
4. **When anything is still open,** DocStore: `append_doc` a `## Round <N>` section, with the open questions numbered on from the last one, in the same shape. Open means unanswered, raised by an answer, or a topic still too vague to write its spec section from. Leave earlier rounds as they are. Then **STOP** again, as in item 2.
5. When nothing is open, go on to step 4.

### 4. Check the architecture (high)

1. Read the Architecture doc. When the file doesn't exist, the spec's Architecture change says `None: the project has no Architecture doc.`, and you skip item 2.
2. Compare the answers with it. Write the change the feature needs: what to add, change, or remove, under which heading of the Architecture doc. A feature that fits the current architecture has `None`.

### 5. Draft the spec (high)

Read the Documentation style doc now.

1. Write the spec's sections from the answers, in this order. Every section is present, with `None` in any that's empty.

   ```markdown
   ## Intent
   ## Goals and non-goals
   ## Alternatives considered
   ## Design
   ## Architecture change
   ## Areas of concern
   ## Deferred
   ## Open questions
   ```

   - **Intent:** the problem, the outcome, the affected users and systems, and the constraints.
   - **Design:** how it works, including how it's tested.
   - **Areas of concern:** risks, conflicts with a guideline, and anything the developer must decide.
   - **Deferred:** what the feature leaves for later, one item per bullet.
   - **Open questions:** anything still undecided, one per bullet.
2. Write them to the spec. The first time, DocStore: `append_doc` every section in one call. On a redraft, DocStore: `update_doc` each section that changes.
3. Set the status to `drafting`. Then **STOP**, naming the spec by its title and link: the developer reviews it in Outline, edits it there if needed, and says "approved", or adds questions to its Open questions.
4. **On a reply,** DocStore: `get_doc` the spec, since the developer may have edited it. On approval, go to step 6. Otherwise, answer what you can from the code and the questions doc, update the spec, and **STOP** again as in item 3. A question only the developer can answer goes in a new round in the questions doc: set the status to `interviewing`, and continue from step 3, item 4.

### 6. Approve (medium)

1. DocStore: `get_doc` the spec.
2. If Open questions has any entry, the spec isn't approved. Leave the status as it is. **STOP**, naming each open question: the developer resolves it in the spec, then approves again.
3. When the Architecture change isn't `None`, apply it to `docs/guidelines/architecture.md`: edit the heading it names, or add a section when the change is a new one.
4. Set the status to `approved`.
5. **STOP**: say the spec is approved, with its title and link, and that on "continue" the skill breaks it into tasks.

### 7. Decompose (high)

Read the Task style guide and the Testing strategy doc now. Approval already applied the architecture change, so leave the Architecture doc alone from here on.

1. DocStore: `get_doc` the spec.
2. Split the Design into vertical slices, by the Task style guide's Sizing rules. Order them so every slice comes after the slices it needs.
3. Write each slice as a task, by the Task style guide: the title, the type, and the description, with every section of the template. Each manual test has its **Why manual:** line and full, copyable steps, and none is marked `[blocks merge]`: the developer decides that in step 10.
4. When any slice has a manual test, add the validation task last: titled `Run the manual tests for <feature>`, with the type `chore`, written from the Validation template in the Task style guide. Its criteria have one line per manual test, `- [ ] <slice title>: <manual test title> passes`. It's blocked by each slice that has a manual test, and by no other.
5. Write each item in the spec's Deferred section as a deferred entry, with the four Deferred sections. Its Source is the spec's title and link.
6. Put them in one JSON draft, in the order of item 2, with the validation task last. Each `id` is a short slug, and `blocked_by` lists the ids of the slices it needs:

   ```json
   {"tasks": [{"id": "<slug>", "title": "<title>", "type": "<type>", "description": "<description>", "blocked_by": ["<slug>"]}], "deferred": [{"id": "<slug>", "title": "<title>", "description": "<description>"}]}
   ```

### 8. Validate the draft (low)

Run the draft validator, with the draft as JSON on one line inside single quotes. Write each `'` in the draft as `'`, so the quoting holds. `<feature slug>` is the feature name in lowercase, with hyphens for spaces.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/validate_draft.py --save .sdlc/local/<feature slug>-draft.json --json '<draft>'
```

Run it exactly as shown, as one command: add nothing before or after it, not even `mkdir`, since `--save` creates the folder. It prints `{"ok": true}` when the draft passes. Otherwise each line is an error, as `<id>: <rule>: <detail>`. Fix every error in the draft and run it again, until it passes. Don't STOP.

### 9. Create the tasks (medium)

Read the [Kaneo backend map](../../lib/references/backends/kaneo.md) before the first tracker call. Every tracker operation below is done the way it says. A task's link is:

```
<kaneo.url>/dashboard/workspace/<kaneo.workspace_id>/project/<kaneo.project_id>/task/<task id>
```

1. **The epic.**
   - With the `epic` parameter: Tracker: `list_column` for `planned`, and find the epic by `number`. If it isn't found, **ASK** for the right key. When its description doesn't link the spec, Tracker: `update_description`, adding `## Spec` and the spec's title and link at the end.
   - Without it: Tracker: `create_task` titled with the feature name, with the status `planned`, and the description from the Epic template in the Task style guide, written from the spec, ending with `## Spec` and the spec's title and link. Then Tracker: `add_label` `epic`.
2. **Link the spec to the epic.** DocStore: `update_doc` the spec, `findText` its status line, and `text` the status line, a blank line, and the `Epic:` line, unless the spec already has one.
3. **Skip what exists.** Tracker: `list_relations` on the epic, and Tracker: `list_column` for `planned`. A draft entry whose title matches one of the epic's subtasks, or a planned `deferred` task, was created by an earlier run: skip it, and take its key and id.
4. **Each task, in draft order,** one at a time. Each task goes through add-task in full, from its step 1, with its own validator run, duplicate check, and labels. When add-task's instructions are already loaded, follow them again for the next task. This skill never calls `create_task` for a task itself. For the validation task, first write each slice's key before its title in the criteria: `- [ ] <key> <slice title>: <manual test title> passes`. Invoke the add-task skill non-interactively with:

   - `invoked_by`: `plan-feature`
   - `title`, `type`, and `description`: from the draft
   - `epic`: `none`, and `blocked_by`: `none`. This skill links them in item 5, since add-task looks for blockers in to-do only.
   - `placement`: `planned`
   - `deferred`: `off`

   add-task reports the task's key, link, and status, and any comment it added. Keep them for step 10.
5. **Link each task** right after add-task creates it:
   - Tracker: `add_relation` `subtask` from the epic.
   - Tracker: `add_relation` `blocks` from each task in its `blocked_by`.
   - For the validation task, Tracker: `add_label` `validation`.
6. **Each deferred entry.** Invoke add-task the same way, with `type` `none`, and `deferred` `on`. Don't link it to the epic. Then DocStore: `update_doc` the spec: `findText` the item's line in Deferred, and `text` the same line ending with the task's key, title, and link, as `[<key> <title>](<link>)`.
7. If add-task reports an error, **STOP**, naming the tasks created so far and the error.

### 10. Review (low)

1. Set the status to `tasks created`.
2. Run the notify script with `--kind STOP` and the epic's link for `--link`. Then **STOP**, listing the epic and each task in draft order, then the deferred tasks, each with its key, title, and full link, and each comment add-task added. The developer reviews and edits the tasks in Kaneo, and marks a manual test `[blocks merge]` only when later work depends on its result. Then they say "approved".

### 11. Release (medium)

1. **On a reply other than approval,** make the changes it asks for, then **STOP** again as in step 10, item 2.
2. **Read the tasks.** DocStore: `get_doc` the spec, and take the epic from its `Epic:` line. Tracker: `list_relations` on the epic, and Tracker: `list_column` for `planned`. The tasks to release are the epic's subtasks still in Planned. Skip any with the `deferred` label.
3. **Tests that block merge.** For each task with a manual test title ending in `[blocks merge]`: Tracker: `update_description` on the validation task, removing that test's line, and Tracker: `remove_relation` `blocks` from the task to the validation task. When the validation task has no criteria left, Tracker: `archive_task` it, with a comment saying every manual test blocks merge, and skip it.
4. **Order.** Sort the tasks so each comes after every task that blocks it, by the `blocks` relations. Break ties by `number`. The validation task goes last.
5. **Move them.** Tracker: `list_column` for to-do, once. Then, in the order of item 4: Tracker: `set_status` `to-do`, then Tracker: `place_task` at `end`. Place each one against the column you read plus the tasks already moved, without reading the column again: a moved task may not be listed in to-do yet.
6. Set the status to `released`.
7. Report each released task in order, with its key, title, and full link, written out for each task.
