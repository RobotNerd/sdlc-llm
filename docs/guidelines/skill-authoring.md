# Skill authoring

How this plugin's skills are written. Based on Anthropic's [skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

## When to write a skill

Only for repeated work with rules. When a plain request works as well, there's no skill: the repo's guidelines and `CLAUDE.md` carry the rules.

## Frontmatter

* `name`: a short verb or verb–object, lowercase with hyphens: `plan`, `groom`, `work`. Never `verify` or `simplify`: Claude Code runs a skill with either name before every commit.
* `description`: a trigger. It tells the agent when to invoke the skill, and nothing else. Third person. One short sentence on what the skill does, then when to use it, with the words a user would say to trigger it. Under 1,024 characters.
* The `description` never says how the skill works inside: no steps, checks, or templates. Those belong in the body.
* `allowed-tools`: the exact script commands the skill runs, such as `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *)`.
* `model`: the model the skill runs on. `opus` for judgment, such as planning and grooming; `sonnet` for following a fixed process, such as `work`.

## Size and shape

A skill is about 30 to 50 lines, and under 60. It states:

1. **The goal:** one or two sentences on what the skill produces, and where its settings come from.
2. **Hard rules:** what must always or never happen, and the facts about Kaneo or Outline that Claude would otherwise get wrong.
3. **When to stop:** each condition that needs the developer, and the notify command to run first.
4. **Steps:** a short numbered list of outcomes, in order. Each says what must be true when it's done, not which tool to call.

No background or rationale: Claude already knows the general concepts. Only add what it doesn't know.

## Tools and scripts

* Leave tool calls to Claude. Name an MCP tool only when Claude would otherwise pick the wrong one.
* Show the exact command for a script, in its own code block, and what a passing run prints.
* A script runs as one command, with nothing chained before or after it, so `allowed-tools` matches it.
* Feedback loops are explicit: run the check, fix, re-run, and only continue when it passes.

## Stopping

* **ASK** is a question for the developer. **STOP** is anything else they must do: review, approve, merge, or fix.
* Every ASK and STOP runs the notify script first, then says what's needed and ends the turn.
* Never guess an answer the developer owns.

## Wording

* Short and plain, per `documentation-style.md`.
* One term per concept, used the same way in every skill.
* No time-sensitive wording.
* Forward slashes in every path.

## Checking a skill

* `tests/test_plugin_layout.py` checks each skill's frontmatter and length.
* A skill's behavior is checked by manual tests in the sandbox, per `testing.md`, and by use. A misbehavior seen in use becomes a fix and, where it can be, a manual test.

## Template

```markdown
---
name: verb-object
description: Does X for Y. Use when the developer asks to ..., or when ...
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *)
model: opus
---

# verb-object

<The goal: what this skill produces. Where its settings come from.>

## Hard rules

- <What must always or never happen.>

## Stop

To stop, run the notify script, then say what you need, and end your turn:

    python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py --skill verb-object --kind <ASK or STOP> --text "<what's needed>"

Stop when:

- <condition>

## Steps

1. **<Outcome>.** <What must be true when it's done.>
2. **<Outcome>.** <...>
```
