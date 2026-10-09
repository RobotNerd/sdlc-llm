# CLAUDE.md

sdlc-llm is a Claude Code plugin: skills that plan, track, and implement work for a solo
developer. Tasks live in Kaneo. Specs, guideline docs, and reports live in Outline, in the
`sdlc-llm` collection. This repo holds only code, tests, evals, and config.

## Verifying your work

- **Tests:** `.venv/bin/python -m pytest`. Healthy output ends with `passed`, and no `failed`
  or `error` lines. Python 3.11 or later, standard library only; `pytest` and `ruff` are the
  dev dependencies, installed in `.venv`.
- **Lint:** `.venv/bin/ruff check .`. Healthy output is `All checks passed!`.
- **Format:** `.venv/bin/ruff format --check .`. Healthy output ends with
  `files already formatted`, and no `Would reformat` lines

## Guidelines

The guideline docs live in Outline under `docs/guidelines`. Read the one a step needs, when
it needs it:

- **Architecture:** before deciding where new code goes.
- **Code style:** before writing or reviewing code.
- **Documentation style:** before writing any doc, task text, or comment.
- **Task style guide:** before writing or refining a task.
- **Testing strategy:** before writing tests or a task's testing strategy.
- **Commit conventions:** before committing.
- **Review policy:** when reviewing a change.
- **Skill authoring:** before changing a skill.

The PRD (`spec/PRD v2: sdlc-llm` in Outline) is the authority for the v2 design.

## Rules

- Never push to `main`, and never merge a pull request. The developer merges.
- Force-push only with `--force-with-lease`, and only on the current task's branch.
- Committed files never cite tracker items: no task keys, epic keys, or spec ids.
- `.tmp/prompts.md` is the developer's private scratch pad. Don't read it or act on it.
- Never read `.env`. Only scripts read secrets.

## Things Claude gets wrong

None yet.
