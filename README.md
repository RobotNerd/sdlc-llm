# sdlc-llm

A Claude Code plugin for a solo developer who builds software with an LLM. Its skills plan
work, groom the backlog, and implement batches of tasks, from branch to pull request.

Tasks live in [Kaneo](https://kaneo.app), a self-hosted tracker. Specs and questions docs
live in [Outline](https://www.getoutline.com), a self-hosted wiki. Notifications for anything
that needs the developer go to Discord, with Telegram as the fallback. The developer reviews
and merges every pull request; the skills never push to `main` or merge.

## Install

Install the plugin once per machine, at user scope, from the marketplace on GitHub:

```bash
claude plugin marketplace add RobotNerd/sdlc-llm
```

```bash
claude plugin install sdlc-llm@sdlc-llm --scope user
```

The plugin has three options:

* `kaneo_url`: the Kaneo URL
* `kimai_mcp_url`: the full URL of the Kimai MCP server, including its path, for example
  `https://kimai-mcp.example.com/mcp`
* `outline_url`: the Outline URL

Claude Code asks for them when it installs the plugin. To list the options and see which are
set, run:

```bash
claude plugin configure sdlc-llm@sdlc-llm
```

Each option shows `(required, set)` or `(required, not set)`. Inside a session,
`/plugin configure sdlc-llm@sdlc-llm` does the same.

The plugin brings its own Kaneo, Kimai, and Outline MCP servers. The Kimai server signs in
with OAuth. After setting `kimai_mcp_url`, run `/mcp` in a session and sign in to `kimai`. A repo
needs no `mcp.json` or `.mcp.json` for them.

Diagrams need Node 20 or later, because the `draw` skill runs `npx`. To check the version, run:

```bash
node --version
```

An Excalidraw canvas is optional. It is only for editing a diagram by hand, as the
[Edit a diagram by hand](#edit-a-diagram-by-hand) section describes.

### Upgrade

Auto-update brings each merge to `main` to the install in the background. Without running
anything, the install catches up on its own.

To bring the install to the latest `main` right away, run these two commands:

```bash
claude plugin marketplace update sdlc-llm
```

```bash
claude plugin update sdlc-llm@sdlc-llm --scope user
```

Then start a new session. A running session keeps the version it started with.

An update can add an option. Claude Code asks for options only at install, so the new option
stays unset, and its MCP server fails to connect. After an update, list the options:

```bash
claude plugin configure sdlc-llm@sdlc-llm
```

Set each one marked `(required, not set)`. This command reads a JSON object of single-line
strings from stdin and saves it. Options left out keep their values. Replace the URL with
your own:

```bash
echo '{"kimai_mcp_url": "https://kimai-mcp.example.com/mcp"}' | claude plugin configure sdlc-llm@sdlc-llm --values-stdin
```

## Setup

Make a repo ready for `plan`, `groom`, and `work`. Do these steps once per repo, in order.
The steps are manual.

1. Create a project in Kaneo. Note its slug, and find its id and your workspace's id in the
   project's URL.
2. Give the project these columns, in this order. Mark `done` as the final column. `planned`
   and `archived` are built-in Kaneo statuses and need no column.

   * `to-do`
   * `in-progress`
   * `in-review`
   * `done`

3. Create these labels in the workspace:

   * `bug`
   * `chore`
   * `deferred`
   * `docs`
   * `epic`
   * `feature`
   * `follow-up`
   * `manual`
   * `needs-refinement`
   * `refactor`
   * `validation`
   * `wont-do`

4. Create an Outline collection for the repo's specs and questions docs. Note its id.
5. Create a Kaneo API key and an Outline API key. In the repo, copy `.env.example` to
   `.env`, then fill in the keys:

   ```bash
   cp .env.example .env
   ```

   Copy `.env.example` from this plugin's repo if the repo has none. It holds these keys:

   * `DISCORD_WEBHOOK_URL`
   * `KANEO_API_KEY`
   * `KIMAI_API_TOKEN`
   * `OUTLINE_API_KEY`
   * `TELEGRAM_BOT_TOKEN`
   * `TELEGRAM_CHAT_ID`

   Leave the notification keys empty if notifications are off.

6. Add these lines to `.gitignore`:

   * `.env`
   * `.sdlc/local/`

7. Create `.sdlc/config.toml` in an editor, with this content. Replace the ids, the slug,
   and the URLs. Set the three commands to the repo's own test, lint, and format checks, or
   to `""` if it has none:

   ```toml
   config_version = 1
   branch_prefix = "app-"
   remote = "origin"
   test_command = "pytest"
   lint_command = "ruff check ."
   format_command = "ruff format --check ."
   throwaway_test_dir = ".sdlc/local/throwaway-tests"

   [kaneo]
   project_id = "<project id>"
   project_slug = "APP"
   url = "https://kaneo.example.com"

   [outline]
   collection_id = "<collection id>"
   url = "https://outline.example.com"
   ```

   To turn on notifications, add this to the file. A second channel with `type = "telegram"`,
   `role = "failover"` is the fallback; its chat id is `TELEGRAM_CHAT_ID` in `.env`:

   ```toml
   [notify]
   enabled = true
   stop_hook = true
   # Starts every message, so projects sharing a channel are told apart. "" turns it off.
   emoji = "⚙️"

   [[notify.channels]]
   role = "primary"
   type = "discord"
   ```

8. Create `CLAUDE.md` in the repo root, with the project's rules and its test, lint, and
   format commands.
9. Create `docs/guidelines/` and add the guideline files the repo needs, named as in
   `Per-repo files`.
10. Check the setup. Start a session in the repo:

    ```bash
    claude
    ```

    A good result: the SessionStart hook prints either the in-progress and in-review
    tasks, or `No Kaneo tasks are in progress or needing review.`, and no error. Then send:

    ```text
    /sdlc-llm:groom
    ```

    A good result: the skill reads the board and proposes fixes, or says the backlog is
    clean.

## Per-repo files

Everything unique to a project lives in its own repo. The skills read only these:

* `.env`: the Kaneo API key, the Kimai API token, and the notification tokens. Gitignored, and read only by
  scripts. `.env.example` lists the keys.
* `.sdlc/config.toml`: the Kaneo project, the Outline collection, and repo settings such as
  the branch prefix and the test, lint, and format commands.
* `CLAUDE.md`: the project's rules and checks.
* `docs/guidelines/`: the project's guideline docs. A skill reads only the one a step needs.

The guideline docs have fixed file names, so the skills can find them. A repo may leave any of
them out:

* `architecture.md`
* `code-style.md`
* `commit-conventions.md`
* `documentation-style.md`
* `review-policy.md`
* `skill-authoring.md`
* `task-style.md`
* `testing.md`

## Skills

| Skill | What it does |
|-------|--------------|
| `draw` | Draws or edits a diagram as an Excalidraw source and a dark and light mode SVG, rendered on this machine, and places both in an Outline doc or the repo. |
| `groom` | Reviews the backlog: blocked chains, tasks ranked above their blocker, stale and under-specified tasks, Planned tasks ready for To Do, deferred tasks, and finished epics. It proposes every fix in one numbered list, and makes only the ones you confirm. |
| `plan` | Turns an idea into tasks. It interviews you in an Outline questions doc, writes a spec when the work is bigger than one task, and creates the epic and its tasks in Kaneo. |
| `work` | Implements a batch of To Do tasks on one branch, one subagent per task, and opens one pull request. It stops only on a real blocker. |

`work` runs on Sonnet; `plan`, `groom`, and `draw` run on Opus.

### Edit a diagram by hand

The `draw` skill needs no canvas. To change a diagram by hand, load its `.excalidraw` source
onto an Excalidraw canvas, edit it in a browser, and save it back. Both commands need Node 20
or later. Replace `https://excalidraw.example.com` with your canvas URL, with no trailing
slash, and `<name>` with the diagram's name. With a trailing slash, the commands can't reach
the canvas. `EXCALIDRAW_NO_AUTOSTART=1` stops the commands from starting a local canvas
when yours is unreachable.

Load the source onto the canvas, replacing what is there:

```bash
EXPRESS_SERVER_URL=https://excalidraw.example.com EXCALIDRAW_NO_AUTOSTART=1 npx -y mcp-excalidraw-server@2.1.2 import docs/diagrams/excalidraw/<name>.excalidraw --replace
```

Edit the diagram in the browser, then save the canvas back to the same file:

```bash
EXPRESS_SERVER_URL=https://excalidraw.example.com EXCALIDRAW_NO_AUTOSTART=1 npx -y mcp-excalidraw-server@2.1.2 export --out docs/diagrams/excalidraw/<name>.excalidraw
```

Then ask the `draw` skill to re-render the diagram from its source.

## Scripts and hooks

| Name | Kind | What it does |
|------|------|--------------|
| `hooks/session_start.py` | SessionStart hook | Prints the in-progress and in-review tasks, so a new session knows where things stand |
| `hooks/time_track.py` | UserPromptSubmit, Stop, StopFailure, and SessionEnd hook | Records each turn's wall-clock time as a Kimai entry, when the repo has `[time_tracking]` |
| `hooks/stop_notify.py` | Stop and StopFailure hook | Notifies with the session's state, including a usage limit and when it resets |
| `lib/board.py` | script | Prints one line per open task: key, status, title, labels, open blockers, and id |
| `lib/notify.py` | script | Sends a notification to Discord, with Telegram as the fallback |
| `lib/reference_check.py` | script, CI | Fails when a committed file cites a tracker item |
| `lib/svg_theme.py` | script | Makes an exported diagram SVG follow the viewer's light or dark mode |
| `lib/validate_draft.py` | script | Checks task drafts against the task format |

The hooks do nothing in a repo without `.sdlc/config.toml`.

## Time tracking

The `hooks/time_track.py` hook records how long the agent works as Kimai time entries. A prompt
starts an entry, and the end of the turn stops it. A repo opts in with a `[time_tracking]`
section, so the hook does nothing, and prints nothing, without one.

### Set up Kimai

1. Run [Kimai](https://www.kimai.org) on a server, following its Docker docs, and serve it only
   on your private network.
2. Create two users: yourself, and `agent`.
3. Create a team led by `agent`, with you as a member.
4. Create a customer, a project for the repo, and an activity such as `Development`. Give the
   team access to the project. Note the project's id and the activity's id.
5. In the system settings, allow more than one active timesheet entry per user.
6. Turn off rounding. Without this step, Kimai rounds entries to whole minutes, which overcounts
   short agent turns. In the Kimai container, put this in `config/packages/local.yaml`, merged
   with any existing `kimai:` key:

   ```yaml
   kimai:
       timesheet:
           rounding:
               default:
                   weekdays: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                   begin: 0
                   end: 0
                   duration: 0
                   mode: default
   ```

   Then reload the cache, in the Kimai container:

   ```bash
   bin/console kimai:reload --env=prod
   ```

7. Log in as `agent`, create an API token, and add it to the repo's `.env`:

   ```text
   KIMAI_API_TOKEN=<the token>
   ```

### The `[time_tracking]` section

Add this to `.sdlc/config.toml`. All four keys are required. Replace the values:

```toml
[time_tracking]
url = "https://kimai.example.com"
project_id = 1
activity_id = 1
agent_user = "agent"
```

* `url`: the Kimai URL, with no trailing slash
* `project_id`: the id of the repo's Kimai project
* `activity_id`: the id of the activity entries are recorded on
* `agent_user`: the Kimai user the token belongs to

The running entry is kept in `.sdlc/local/time-entry.json`. When Kimai is unreachable or
refuses the token, the hook prints a warning on stderr and the session goes on.

### Record your own time from an iPhone

Install an iPhone app such as Kimai Mobile or Timai from the App Store. Log in with the Kimai
URL and your own API token, not the agent's. Entries you start there show beside the agent's,
under your user.

## Workflows

### Plan and build a feature

1. Start planning:

   ```text
   /sdlc-llm:plan Let a batch skip tasks that are already merged
   ```

2. Answer each question in the Outline questions doc the skill links to, replacing its
   `> Answer: TODO` line. Then type:

   ```text
   continue
   ```

3. Read the spec. Edit it if you like, then type:

   ```text
   approved
   ```

4. Review the tasks it created in Planned, then type `approved` again to release them to To
   Do.
5. Implement them, using the keys it listed:

   ```text
   /sdlc-llm:work KEY-12 KEY-13 KEY-14
   ```

6. Review and merge the pull request on GitHub, then type:

   ```text
   merged
   ```

   The skill updates `main`, deletes the branch, and moves the tasks to done.

### Groom the backlog

1. Start a review:

   ```text
   /sdlc-llm:groom
   ```

2. Answer with the numbers of the proposals to apply, and a choice where one is offered:

   ```text
   1, 3, 4 keep, 6 archive
   ```

3. Start a batch with the tasks now at the top of To Do:

   ```text
   /sdlc-llm:work KEY-15 KEY-16
   ```

### Pick up after a break or a usage limit

1. Start a new session in the repo:

   ```bash
   claude
   ```

2. Read the in-progress and in-review tasks the SessionStart hook prints at the top.
3. If the pull request is still open, or the batch stopped partway, run the same `work`
   command again. It resumes from the tasks' Kaneo status:

   ```text
   /sdlc-llm:work KEY-12 KEY-13 KEY-14
   ```

4. If you merged the pull request while away, type:

   ```text
   merged
   ```

## Without a skill

Some work is a plain request. The repo's guidelines and `CLAUDE.md` carry the rules. Earlier
versions had skills for some of these; they were dropped as not worth a skill.

Add a single task (was `add-task`):

```text
Add a task to Kaneo: <what and why>. Follow docs/guidelines/task-style.md, and check it with validate_draft.py.
```

Defer an idea:

```text
File a deferred task for <idea>: why it's deferred, and what would bring it back.
```

Review docs (was `review-docs`):

```text
Review README.md and CLAUDE.md for paths that don't exist, stale skill names, and tracker references. List the problems; fix only what I confirm.
```

Set up a new repo (was `setup-project`): follow `Setup`.

Ask what blocks a task:

```text
What blocks KEY-14, and what's left on each blocker?
```

Refine one task:

```text
Rewrite the acceptance criteria of KEY-14 by docs/guidelines/task-style.md, and show me the change before you save it.
```

Archive a task:

```text
Archive KEY-14 as wont-do: <reason>.
```

## Development

Python 3.11 or later, standard library only. `pytest` and `ruff` are the dev dependencies:

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -e '.[dev]'
```

```bash
.venv/bin/python -m pytest
```

```bash
.venv/bin/ruff check .
```

```bash
.venv/bin/ruff format --check .
```

`CLAUDE.md` says how to test a branch in the sandbox before merging it.
