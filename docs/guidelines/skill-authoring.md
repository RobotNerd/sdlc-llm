# Skill authoring

How this plugin's skills are written. `implement-task` and the critic apply these rules when a task changes a skill. Based on Anthropic's [skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

## Contents

* Frontmatter
* Size and structure
* References
* Steps
* Backends and MCP tools
* Scripts
* Wording
* Evals
* Template

## Frontmatter

* `name`: verb–object, lowercase with hyphens: `plan`, `groom`. Never `verify` or `simplify`: Claude Code runs a skill with either name before every commit.
* `description`: a trigger. It tells the agent when to invoke the skill, and nothing else. Third person. One short sentence on what the skill does, then when to use it, with the words a user would say to trigger it. Under 1,024 characters.
* The `description` never says how the skill works inside: no steps, checks, templates, labels, or relations. Those belong in the body. Good: "Adds a task to the project's Kaneo backlog. Use when the developer asks to add, create, file, or log a task…". Bad: "Interviews the developer until the task has objective acceptance criteria, checks for duplicates and size, then creates the task with…".

## Size and structure

* The `SKILL.md` body stays under 500 lines. Detail goes into references.
* `SKILL.md` holds the steps and nothing else: no background, no rationale. Claude already knows the general concepts; only add what it doesn't know.

## References

* Every reference is linked directly from `SKILL.md`, at the step that needs it. One level deep: a reference never sends the reader on to another reference.
* A reference longer than 100 lines starts with a table of contents.
* File names say what's inside: `batch-validation.md`, not `notes.md`.

## Steps

* Numbered steps. Each step's name is short and stable; batch state and evals refer to it.
* Each step is marked with its degree of freedom:
  * **low:** exact commands, one safe way. These are the candidates for scripts.
  * **medium:** a template or a script with parameters.
  * **high:** judgment decisions made by Claude.
* **STOP** means wait for the human. **ASK** means don't guess; ask. Every STOP and ASK also runs the notify script.
* A long workflow tells the agent to copy its step checklist into the reply and tick each step off.
* A skill that can be called by another skill with every parameter supplied runs without STOPs or ASKs, and records what it would have asked as a comment.
* Feedback loops are explicit: run the check, fix, re-run, and only continue when it passes.

## Backends and MCP tools

* Steps name interface operations ("Tracker: set status `in-progress`"), not a specific tool.
* The backend map says which MCP tool performs each operation, using the full name (server plus tool).

## Scripts

* Say whether to run a script or read it: "Run `scripts/validate.py <draft>`", or "See `scripts/validate.py` for the rules."
* Show the exact command and what its output looks like.
* Scripts follow the script rules in `architecture.md`.

## Wording

* Short and plain, per `documentation-style.md`.
* One term per concept, used the same way in every skill.
* No time-sensitive wording.
* One default approach per step. Mention an alternative only when it's needed, with when to use it.
* Forward slashes in every path.

## Evals

* At least three eval cases per skill, written before its prose, in the `claude plugin eval` format that `testing.md` describes.
* Vary the prompt wording, to check that the skill triggers when it should. Include one prompt that must not trigger it.
* A misbehavior seen in real use becomes a new eval.
* After changing a skill's `description`, re-run its cases. A Δ near zero with the skill-fired grader failing means the description doesn't trigger.

## Template

```markdown
---
name: verb-object
description: Does X for Y. Use when the user asks to ..., or when ...
---

# verb-object

<One sentence: what this skill produces.>

## Parameters

| Parameter | Default | Skips |
|---|---|---|

## Steps

Copy this checklist and tick each step off:

- [ ] 1. <step name>
- [ ] 2. <step name>

### 1. <step name> (low)

<Instructions. Link a reference here if this step needs one.>

### 2. <step name> (high)

<Instructions.> → **STOP**: <what the human decides>.
```
