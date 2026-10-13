# CLAUDE.md

sdlc-llm is a Claude Code plugin: skills that plan, track, and implement work for a solo
developer. Tasks live in Kaneo. Specs and reports live in Outline, in the
`sdlc-llm` collection. This repo holds only code, tests, and config.

## Verifying your work

- **Tests:** `.venv/bin/python -m pytest`. Healthy output ends with `passed`, and no `failed`
  or `error` lines. Python 3.11 or later, standard library only; `pytest` and `ruff` are the
  dev dependencies, installed in `.venv`.
- **Lint:** `.venv/bin/ruff check .`. Healthy output is `All checks passed!`.
- **Format:** `.venv/bin/ruff format --check .`. Healthy output ends with
  `files already formatted`, and no `Would reformat` lines

## Running the plugin

This repo runs the plugin as released on `main` on GitHub. `.claude/settings.json` declares
the `sdlc-llm` marketplace and enables `sdlc-llm@sdlc-llm` at project scope, but enabling a plugin doesn't install it. Install it
once from the repo root:

```bash
claude plugin marketplace add RobotNerd/sdlc-llm && claude plugin install sdlc-llm@sdlc-llm --scope project
```

Then start `claude` here with no flags. The first session asks for the Kaneo and Outline
URLs. Don't load this repo with `--plugin-dir`: the session would then run the files it
edits.

The manifest has no `version`, so Claude Code versions the install by commit SHA, and every
merge to `main` reaches it. Auto-update brings a merge in the background. To bring it in
right away, run this from the repo root, then start a new session:

```bash
claude plugin marketplace update sdlc-llm && claude plugin update sdlc-llm@sdlc-llm
```

A branch is tested in the sandbox, `~/dev/sdlc-sandbox`, from a scratch checkout at
`~/dev/sdlc-llm-review`. Create the checkout once:

```bash
git -C ~/dev/sdlc-llm worktree add --detach ~/dev/sdlc-llm-review
```

Before each test, set `BRANCH` to the branch under test, then move the checkout to it and
start the sandbox session:

```bash
git -C ~/dev/sdlc-llm-review fetch && git -C ~/dev/sdlc-llm-review checkout --detach "origin/$BRANCH"
```

```bash
cd ~/dev/sdlc-sandbox && claude --plugin-dir ~/dev/sdlc-llm-review
```

## Guidelines

The guideline docs live in `docs/guidelines/`. Read the one a step needs, when it needs it:

- `docs/guidelines/architecture.md`: before deciding where new code goes.
- `docs/guidelines/code-style.md`: before writing or reviewing code.
- `docs/guidelines/commit-conventions.md`: before committing.
- `docs/guidelines/documentation-style.md`: before writing any doc, task text, or comment.
- `docs/guidelines/review-policy.md`: when reviewing a change.
- `docs/guidelines/skill-authoring.md`: before changing a skill.
- `docs/guidelines/task-style.md`: before writing or refining a task.
- `docs/guidelines/testing.md`: before writing tests or a task's testing strategy.

The PRD (`spec/PRD v2: sdlc-llm` in Outline) is the authority for the v2 design.

## Rules

- Never push to `main`, and never merge a pull request. The developer merges.
- Force-push only with `--force-with-lease`, and only on the current task's branch.
- Committed files never cite tracker items: no task keys, epic keys, or spec ids.
- `.tmp/prompts.md` is the developer's private scratch pad. Don't read it or act on it.
- Never read `.env`. Only scripts read secrets.

## Things Claude gets wrong

None yet.
