# Task style guide

How tasks are structured and worded. `add-task`, `plan-feature`, and `refine-backlog` read this, along with the Documentation style and Testing strategy docs it builds on. A task that breaks these rules gets flagged as under-specified.

## Contents

* Principles
* Title
* Description template
* Sections
* Sizing
* Special tasks
* Examples

## Principles

* Short and plain. Short sentences, common words, no filler.
* A reader who knows the codebase can do the task from its text alone.
* Every statement is checkable. If it can't be checked, cut it or make it concrete.
* One term per concept. "Task", never "ticket" or "story".

## Title

* An imperative verb phrase: "Add batch state resume", not "Batch state resume" or "Adds…".
* Says the outcome, not the activity: "Reject batches with out-of-order blockers", not "Work on batch validation".
* Under about 70 characters. No trailing period. No task key.

## Description template

```markdown
## Description
## Acceptance criteria
- [ ] ...
## Testing strategy
### Automated
### Manual
## Notes
```

All four top-level sections are always present. A section with nothing in it says `None`.

## Sections

**Description**

* Two to five sentences: what changes, and why.
* Name the files, commands, or skill steps involved when they're known.
* Out of scope: list it here in one line when there's an obvious neighbor the task doesn't touch.

**Acceptance criteria**

* A `- [ ]` checklist. No hard limit on count, but each one earns its place.
* One observable behavior per criterion.
* Objective: two people would agree whether it's met. "Exits 1 with the message `no tasks found`", not "handles errors well".
* Behavior, not implementation: say what the user sees, not which function changes. Name a file only when the file itself is the outcome.

**Testing strategy**

* Follows the format in the Testing strategy doc: automated tests first, then manual, each as Given/When/Then plus steps, each naming the criterion it covers.
* Every criterion has at least one test.
* Manual tests are only for what can't be automated.
* Manual steps are formatted for copying: commands, agent prompts, and values to paste each stand in their own code block or bulleted list, never inline in a sentence. A file to create is given as its name, then its content, each in its own block. See "Formatting for the reader" in the Documentation style doc.

**Notes**

* Context the implementer needs that isn't a requirement: links to the spec, known pitfalls, related tasks.
* Not a place for requirements. If it must be true, it's a criterion.

## Sizing

* One task is one branch, one squash commit, and one sitting.
* Split it if the criteria describe separately shippable pieces, the changes span unrelated areas, or the testing needs several unrelated setups.
* Split by behavior (vertical slices), not by layer. "Add the endpoint and show it in the UI" is a slice; "do the backend" is not.

## Special tasks

**Epic** (label `epic`): Goal, In scope, Out of scope, Success criteria, and a link to the spec. No testing strategy; its tasks have their own.

**Deferred** (label `deferred`):

```markdown
## Deferred
<what was deferred>
## Why
<why it was deferred>
## Brings it back
<what would make it worth doing>
## Source
<link to the spec or PRD that deferred it>
```

**Follow-up** (label `follow-up`, created during a batch): the normal template. Notes says which task it came from and why it was split off.

**Needs refinement:** a task created with gaps carries a `needs-refinement` comment listing them. It stays in Planned until the gaps are filled.

## Examples

**Good**

```markdown
Title: Reject batches whose blockers come later in the order

## Description
Batch validation accepts a task whose blocker is in the same batch but ordered after it. The batch then starts a task before its blocker is merged. Add the check to `build batch`.

## Acceptance criteria
- [ ] A batch where a task's blocker is later in the order stops before any work, naming both tasks.
- [ ] A batch where every blocker comes first starts normally.

## Testing strategy
### Automated
#### Blocker after its dependent → batch refused   (criterion: first)
* **Given:** two to-do tasks, B blocked by A, ordered B then A
* **When:** a batch is built from that range
* **Then:** it exits non-zero, names A and B, and no branch is created
1. Set up the fake tracker with A and B.
2. Run the batch builder with the range — expected: exit 1, message names A and B.
3. Check `git branch` — expected: no new branch.
### Manual
None

## Notes
None
```

**Bad**

```markdown
Title: Batch validation improvements

## Description
Make batch validation better and handle more edge cases.

## Acceptance criteria
- [ ] Validation is more robust.
```

It has no outcome in the title, a vague description, a criterion nobody can check, and no testing strategy.
