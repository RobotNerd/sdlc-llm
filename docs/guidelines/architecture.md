# Architecture

How sdlc-llm is built, where new code goes, and the decisions behind it.

## Contents

* What it is
* Components
* Where state lives
* Backend interfaces
* Repo layout
* Scripts
* Key decisions

## What it is

A Claude Code plugin: a set of skills that plan, track, and implement work for a solo developer. Work items live in Kaneo. Planning and guideline docs live in Outline. The project's repo holds only code, tests, config, and agent instructions.

## Components

| Component | Role |
|-----------|------|
| Skills (`skills/<name>/SKILL.md`) | Judgment: interviews, decomposition, implementation, review. Numbered steps with STOP and ASK markers. |
| Scripts (`skills/<name>/scripts/`, `lib/`) | Mechanical steps: backend calls, git, validation, reports. Stdlib Python. |
| Backends (`lib/backends/`) | One module per external tool, behind an interface. |
| Backend maps (`lib/references/backends/`) | For prose skills: each interface operation → the MCP tool that performs it. |
| Hooks (`hooks/hooks.json`) | The notification Stop hook. Guardrails later. |
| Evals (`evals/<skill>/<case>/`, `evals/mocks/`) | Regression tests for skill behavior, run with `claude plugin eval` against mocked Kaneo and Outline MCP servers. |
| MCP config (`mcp.json`) | Declares the `kaneo` and `outline` MCP servers, with URLs from the plugin's `userConfig`. Eval mocks only work for servers declared here. The manifest names it, because a root `.mcp.json` would also load as the repo's own project MCP config. |

## Where state lives

| State | Owner |
|-------|-------|
| Tasks, epics, deferred work, status, order, dependencies, worklog | Kaneo |
| Specs, questions docs, guideline docs, epic and batch reports | Outline |
| Code, tests, evals, config | The repo |
| Batch state, drafts | `.sdlc/local/` (gitignored) |
| Secrets | `.env` (gitignored), read only by scripts |

The only links between Kaneo and the repo are task keys in commit messages, and merge SHAs in Kaneo comments. Committed files never cite tracker items.

## Backend interfaces

Skills never call a tool directly. They call operations on an interface:

* **Tracker:** tasks, columns, order, labels, relations, comments, search, archive.
* **DocStore:** docs, nesting, patch updates, search, archive.
* **Notifier:** send a one-line message to each enabled channel.
* **Critic:** review a task's diff against the review policy, and return a verdict.

Each interface has one module per backend, chosen in `.sdlc/config.toml`. Only the backend module knows an endpoint or a field name. Swapping a tool means adding a module and a backend map, not editing skills.

While a skill is prose-only, it uses MCP tools through the backend map. When a step moves into a script, the script uses the backend module, which calls the tool's REST API.

## Repo layout

```
.claude-plugin/        plugin and marketplace manifests
skills/<name>/         SKILL.md, references/, scripts/
lib/                   shared code: config, .env loader, git helpers
lib/backends/          interface implementations
lib/references/        backend maps, default guideline docs
hooks/                 plugin hooks
mcp.json               Kaneo and Outline MCP servers
evals/<skill>/<case>/  skill eval cases
evals/mocks/<server>/  MCP mocks for the evals
tests/                 script tests, backend fakes, contract tests
```

Shared code lives only in `lib/`. A script finds `lib/` by a path relative to its own file.

## Scripts

* Python ≥ 3.11, standard library only.
* One subcommand per deterministic step.
* JSON in (a file path argument), JSON out on stdout. Exit 0 on success. On failure, exit non-zero with a specific message on stderr.
* Each script checks its own preconditions. Hooks are a backstop, not the enforcement.
* Idempotent where it can be: running a step twice leaves the same state.

## Key decisions

* **A real tracker, not files in the repo.** v1's markdown tracker needed a generator, region markers, and hooks just to stay consistent, and its archives went stale in the repo.
* **Prose first, scripts later.** A step moves into a script only after it settles. Scripting an unsettled step means rewriting it.
* **Local squash merge, no PRs.** A critic gates each merge instead of a human PR review. A PR mode is deferred.
* **The core data model uses only what the MCP servers expose**, so prose-only skills never need REST.
* **Plan, validate, then execute** before any bulk write to a backend.
* **Claude Code's eval runner, not our own.** `claude plugin eval` already isolates runs, mocks MCP servers, compares against a no-plugin baseline, and gates CI. Contract tests cover the real backends.
