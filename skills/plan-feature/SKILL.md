---
name: plan-feature
description: Plans a feature through a spec in Outline. Use when the developer asks to plan, spec, design, or scope a feature, or something too big for one task, or to continue, resume, or approve a feature plan.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *)
---

# plan-feature

Turns a feature idea into an approved spec in Outline, through an interview in a questions doc.

## Parameters

| Parameter | Default | Skips |
|---|---|---|
| feature | none | the request. With none, the skill resumes a spec in progress (step 2). |

## Asking and stopping

- **ASK** means: run the notify script with `--kind ASK`, then ask with `AskUserQuestion`, with the recommended answer first. If `AskUserQuestion` isn't available, ask in your reply and end your turn. Never guess an answer.
- **STOP** means: run the notify script with `--kind STOP`, then say what's needed, and end your turn.
- **Notify script,** run with every ASK and STOP. Pass the doc the developer needs with `--link`. If it fails or can't run, carry on.

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
| `approved` | The spec is approved. | step 6, item 5 |
| `tasks created` | The tasks are created, waiting for review. | step 6, item 5 |
| `released` | Done. Never resumed. | — |

Change the status with DocStore: `update_doc`, `findText` the whole old status line, and `text` the new one.

## Steps

Read the [Outline backend map](../../lib/references/backends/outline.md) before the first DocStore call. Every DocStore operation below is done the way it says. Values in angle brackets come from `.sdlc/config.toml`.

Read guideline docs from Outline with `mcp__plugin_sdlc-llm_outline__fetch` (`resource` `document`, `id` from the config), at the step that needs them. When an id is empty, read the plugin's default copy instead:

| Doc | Config key | Default copy |
|---|---|---|
| Testing strategy | `guidelines.testing` | [testing-strategy.md](../../lib/references/guidelines/testing-strategy.md) |
| Documentation style | `guidelines.doc_style` | [documentation-style.md](../../lib/references/guidelines/documentation-style.md) |
| Architecture | `guidelines.architecture` | none |

Copy this checklist into your reply, and tick each step off as you finish it:

```
- [ ] 1. Check the repo
- [ ] 2. Find or start the spec
- [ ] 3. Interview
- [ ] 4. Check the architecture
- [ ] 5. Draft the spec
- [ ] 6. Approve
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

1. Read the Architecture doc. When `guidelines.architecture` is empty, DocStore: `find_doc` `docs/guidelines/Architecture`. When there's none, the spec's Architecture change says `None: the project has no Architecture doc.`, and you skip item 2.
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
3. When the Architecture change isn't `None`, apply it to the Architecture doc: DocStore: `update_doc` the heading it names, or `append_doc` when the change is a new section.
4. Set the status to `approved`.
5. **STOP**: say the spec is approved, with its title and link, and that breaking it into tasks comes next.
