# Architecture

How sdlc-llm is built, where new code goes, and the decisions behind it.

## What it is

A Claude Code plugin for one developer: three skills that plan, groom, and implement work. Tasks live in Kaneo. Specs and questions docs live in Outline. Each project's repo holds its code, tests, config, and guideline docs.

## Components

| Component | Role |
|-----------|------|
| Skills (`skills/<name>/SKILL.md`) | Judgment. `plan` turns an idea into tasks, `groom` reviews the backlog, and `work` implements a batch of tasks. Each states its goal, its hard rules, and when to stop. |
| Scripts (`lib/`) | Work that must be exact, or would load a large payload into context. Stdlib Python. |
| Notifiers (`lib/backends/`) | Discord and Telegram senders for `lib/notify.py`, behind the `Notifier` interface. |
| Kaneo client (`lib/backends/kaneo.py`, `lib/backends/rest.py`) | Kaneo's REST API, for scripts. Skills use the Kaneo MCP tools instead. |
| Hooks (`hooks/hooks.json`) | `hooks/session_start.py` runs on SessionStart, and puts the in-progress and in-review tasks in the session's context. `hooks/stop_notify.py` runs on Stop and StopFailure, and notifies with the session's state. |
| MCP config (`mcp.json`) | Declares the `kaneo` and `outline` MCP servers, with URLs from the plugin's `userConfig`. The manifest names it, because a root `.mcp.json` would also load as the repo's own project MCP config. |

### Scripts

| Script | What it does |
|--------|--------------|
| `lib/board.py` | Prints one line per open Kaneo task, so a skill reads the board without loading every description |
| `lib/notify.py` | Sends an ASK or STOP notification to Discord, with Telegram as the fallback |
| `lib/reference_check.py` | Fails, in CI, when a committed file cites a tracker item |
| `lib/transcript.py` | Reads a session transcript: its entries, usage-limit notes, and background subagents still running |
| `lib/validate_draft.py` | Checks task drafts against the task format |

## Per-repo files

A project using the plugin keeps everything unique to it in its own repo. The skills read only these:

* `.env`: the Kaneo API key, the notification tokens, and the Telegram chat id, which isn't a secret. Read only by scripts.
* `.sdlc/config.toml`: the Kaneo project, the Outline collection, and repo settings such as the check commands.
* `CLAUDE.md`: the project's rules and checks.
* `docs/guidelines/`: the project's guideline docs, with fixed file names.

## Where state lives

| State | Owner |
|-------|-------|
| Tasks, epics, deferred work, status, order, dependencies, task comments | Kaneo |
| Specs and questions docs | Outline |
| Code, tests, config, guideline docs | The repo |
| Drafts and other scratch state | `.sdlc/local/` (gitignored) |
| Secrets | `.env` (gitignored), read only by scripts |

Kaneo carries a batch's state between sessions: a new session resumes from the tasks' statuses. The only links between Kaneo and the repo are task keys in commit messages. Committed files never cite tracker items.

## Repo layout

```
.claude-plugin/        plugin and marketplace manifests
docs/guidelines/       guideline docs
hooks/                 plugin hooks
lib/                   scripts and shared code: config, .env loader
lib/backends/          notifiers and the Kaneo REST client
mcp.json               Kaneo and Outline MCP servers
skills/<name>/         SKILL.md
tests/                 script tests and fakes
```

Shared code lives only in `lib/`. A script finds `lib/` by a path relative to its own file.

## Script rules

* Python ≥ 3.11, standard library only.
* JSON in (a file path or a `--json` argument), JSON out on stdout. Exit 0 on success. On failure, exit non-zero with a specific message on stderr.
* Each script checks its own preconditions.
* Idempotent where it can be: running it twice leaves the same state.

## Key decisions

* **Built for one developer.** No backend abstraction and no install path for other people. Kaneo and Outline are the only backends, and skills call their MCP tools by name.
* **A real tracker, not files in the repo.** A markdown tracker needed a generator and hooks just to stay consistent, and its archives went stale.
* **Short skills, scripts for exact work.** A skill states the goal, the hard rules, and when to stop, and leaves the tool calls to Claude. A step becomes a script only when it must be exact or cheap.
* **A pull request per batch, merged by the developer.** `work` commits each task on one branch and opens one pull request. Skills never push to the default branch or merge.
* **A subagent per task,** so the main session holds only short summaries and stays cheap.
* **Guidelines in each repo,** so each project can differ, and reading one is a cheap local read.
