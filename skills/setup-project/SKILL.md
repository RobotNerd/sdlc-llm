---
name: setup-project
description: Sets up a repo for sdlc-llm. Interviews the developer, then creates or connects the Kaneo project and Outline collection, writes .sdlc/config.toml, .env.example, the .gitignore entries, the CLAUDE.md sections, and .claude/settings.json, and checks every backend. Use once per repo before the first add-task, or again to repair a setup. Safe to rerun.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/setup-project/scripts/setup.py *), Bash(mkdir -p .sdlc/local)
---

# setup-project

Connects the current repo to Kaneo and Outline, and writes the files the other skills read. Every
step is idempotent: a rerun creates only what's missing and keeps every existing file, doc, and
setting.

Copy this checklist into your reply, and tick each step off as you finish it:

```
- [ ] 1. Check the repo
- [ ] 2. Interview
- [ ] 3. Secrets in .env
- [ ] 4. Save the values
- [ ] 5. Provision Kaneo and Outline
- [ ] 6. Write the repo files
- [ ] 7. Check the backends
- [ ] 8. Report
```

Notifications aren't configured until step 6. A STOP or ASK before then shows only in the
terminal. From step 7 on, also send each STOP and ASK with the notify script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py --skill setup-project --kind STOP --text "<what's needed>"
```

## 1. Check the repo

Freedom: low.

1. Run `git rev-parse --show-toplevel`. If it fails, **STOP**: setup needs a git repository.
2. Check that the plugin's MCP tools exist: `mcp__plugin_sdlc-llm_kaneo__list_workspaces` and
   `mcp__plugin_sdlc-llm_outline__list_collections`. Other servers' Kaneo or Outline tools don't
   count, because every skill calls the plugin's. If they're missing, **STOP**, and tell the
   developer to:
   1. open `/plugin`, choose sdlc-llm, then **Configure options**, and set the Kaneo URL and the
      Outline URL
   2. sign in to both servers with `/mcp`
   3. rerun this skill
3. If `.sdlc/config.toml` exists, the repo is already set up. **ASK** whether to rerun setup to
   repair it. A rerun keeps the existing config file unchanged. To change a value in it, the
   developer edits the file.

## 2. Interview

Freedom: high.

Ask with `AskUserQuestion`, a few questions at a time. Offer the default as the first option,
marked "(Recommended)". Collect:

| Value | Default |
|-------|---------|
| Kaneo URL | `${user_config.kaneo_url}` |
| Kaneo workspace | Call `mcp__plugin_sdlc-llm_kaneo__list_workspaces`. With one workspace, use it without asking. |
| Kaneo project name | The repo directory's name |
| Kaneo project slug | Up to five capital letters from the name. It's the task-key prefix, so it can't change later. |
| Outline URL | `${user_config.outline_url}` |
| Outline collection name | The repo directory's name |
| Test, lint, and format commands | Read the repo's build files (`pyproject.toml`, `package.json`, `Makefile`, and similar), and propose what they define. A command can be "none". |
| Healthy output for each command | What a passing run ends with, such as "ends with `passed`, and no `failed` lines" |
| Notifications on or off | On |
| Channels | Discord primary, Telegram failover. Telegram needs the chat id. |
| Stop hook | Off. It also notifies whenever a turn ends waiting for the developer, which can be noisy. |
| Thresholds | Show the defaults below, and change only the ones the developer asks to change. |

The defaults, each with its reason, are in `TOP_LEVEL_DEFAULTS`, `CRITIC_DEFAULTS`, and
`EVALS_DEFAULTS` in [scripts/repo_files.py](scripts/repo_files.py). Read that file only to list
them; don't run it.

If either MCP server fails to answer, **STOP**, and tell the developer to run `/mcp` to see why.

## 3. Secrets in .env

Freedom: low.

Never read `.env`, and never ask the developer to paste a secret into the conversation. Only the
scripts read it.

Tell the developer which names `.env` at the repo root needs, each on its own line as `NAME=value`:

- `KANEO_API_KEY`
- `OUTLINE_API_KEY`
- `DISCORD_WEBHOOK_URL`, when Discord is a channel
- `TELEGRAM_BOT_TOKEN`, when Telegram is a channel

**ASK** the developer to say when they've saved it. Step 5 reports a missing name.

## 4. Save the values

Freedom: medium.

Run `mkdir -p .sdlc/local`, then write `.sdlc/local/setup-values.json`. It holds no secrets.
Leave out any command that's "none", and any override the developer didn't change:

```json
{
  "commands": {
    "format": {"command": "<format command>", "healthy": "<healthy output>"},
    "lint": {"command": "<lint command>", "healthy": "<healthy output>"},
    "test": {"command": "<test command>", "healthy": "<healthy output>"}
  },
  "kaneo": {
    "project_name": "<name>",
    "project_slug": "<SLUG>",
    "url": "<Kaneo URL>",
    "workspace_id": "<workspace id>"
  },
  "notify": {
    "channels": [
      {"role": "primary", "type": "discord"},
      {"chat_id": "<chat id>", "role": "failover", "type": "telegram"}
    ],
    "enabled": true,
    "stop_hook": false
  },
  "outline": {
    "collection_name": "<collection name>",
    "url": "<Outline URL>"
  },
  "overrides": {"<key>": "<value>"}
}
```

An override key is a top-level config key, such as `quality_gate_attempts`, or `critic.<key>` or
`evals.<key>`.

## 5. Provision Kaneo and Outline

Freedom: low.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/setup-project/scripts/setup.py provision .sdlc/local/setup-values.json > .sdlc/local/setup-ids.json
```

It creates the Kaneo project, its columns and labels, and the Outline collection with its docs
and the default guideline docs, wherever they're missing. It prints the ids as JSON. On a
non-zero exit, **STOP** with its error. The error names the service and the step.

## 6. Write the repo files

Freedom: low.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/setup-project/scripts/setup.py write .sdlc/local/setup-values.json .sdlc/local/setup-ids.json
```

It writes `.sdlc/config.toml` (only when it doesn't exist), and merges `.env.example`,
`.gitignore`, `CLAUDE.md`, and `.claude/settings.json`, keeping what's already there. It prints
the files it changed and the ones it kept. On a non-zero exit, **STOP** with its error.

## 7. Check the backends

Freedom: low.

1. Run the script check. It checks the API keys, the Kaneo project, and the Outline collection,
   and sends a test notification to each channel:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/setup-project/scripts/setup.py check
   ```

2. Check the MCP connections the skills use:
   - `mcp__plugin_sdlc-llm_kaneo__get_project` with `id` set to `kaneo.project_id` from
     `.sdlc/config.toml`
   - `mcp__plugin_sdlc-llm_outline__list_collection_documents` with `collectionId` set to
     `outline.collection_id`

3. If anything fails, **STOP**, naming each failing check and its reason. After a fix, rerun
   from the step that failed.

4. **ASK** the developer to confirm a test notification arrived on each channel.

## 8. Report

Freedom: medium.

Tell the developer:

- what was created in Kaneo and Outline, from `created` in `.sdlc/local/setup-ids.json`
- the files changed and kept, from step 6
- any `extra_columns` on an existing Kaneo board, which the skills ignore
- any guideline left empty under `[guidelines]` in `.sdlc/config.toml`, which they fill in once the
  doc exists in Outline
- to review and commit the changed files, because `implement-task` needs a clean tree

Then **STOP**: the repo is ready for `add-task`.
