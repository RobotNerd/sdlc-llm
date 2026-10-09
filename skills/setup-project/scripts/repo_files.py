"""The repo files setup-project writes: config, .env.example, .gitignore, CLAUDE.md, and Claude Code settings.

Each one is merged, never replaced: existing text, entries, and rules are kept.
"""

import json
import re
from pathlib import Path

from lib.config import DEFAULTS

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
BACKEND_MAPS = PLUGIN_ROOT / "lib/references/backends"
CLAUDE_MD = "CLAUDE.md"
CONFIG = ".sdlc/config.toml"
ENV_EXAMPLE = ".env.example"
GITIGNORE = ".gitignore"
GITIGNORE_ENTRIES = (".env", ".sdlc/local/")
SETTINGS = ".claude/settings.json"
# The deny rule keeps secrets out of the transcript. A bare file name matches .env at any depth.
DENY_RULES = ("Read(.env)",)
# The plugin's install path holds its version, so the rules match the script path at any root.
PLUGIN_SCRIPT_RULES = (
    "Bash(python3 */lib/notify.py *)",
    "Bash(python3 */lib/render_diagram.py *)",
    "Bash(python3 */skills/*/scripts/*.py *)",
)
MCP_TOOL_PATTERN = re.compile(r"mcp__plugin_sdlc-llm_[a-z]+__[a-z_]+")

# Guideline doc titles in Outline, mapped to their guidelines.* config key, in CLAUDE.md order.
GUIDELINE_ROLES = (
    ("Architecture", "architecture", "before deciding where new code goes."),
    ("Code style", "code_style", "before writing or reviewing code."),
    ("Documentation style", "doc_style", "before writing any doc, task text, or comment."),
    ("Task style guide", "task_style", "before writing or refining a task."),
    ("Testing strategy", "testing", "before writing tests or a task's testing strategy."),
    ("Commit conventions", "commits", "before committing."),
    ("Review policy", "review_policy", "when reviewing a change."),
    ("Skill authoring", "skill_authoring", "before changing a skill."),
)
COMMAND_LABELS = (("test", "Tests"), ("lint", "Lint"), ("format", "Format"))

# (key, default, why). Values the developer gives override the default.
TOP_LEVEL_DEFAULTS = (
    (
        "autonomous_new_task_limit",
        3,
        "Past this many follow-ups, a batch recommends instead of filing, so the backlog doesn't grow unattended.",
    ),
    ("context_usage_halt_pct", 85, "Pause with room left in the context window to write the pause report."),
    ("critic_rejection_attempts", 3, "Three rejections on one task means the human should decide, not the loop."),
    ("default_branch", "main", "The branch batches merge into."),
    ("docs_ignore_paths", [], "Paths review-docs skips."),
    ("docs_review_paths", ["CLAUDE.md", "README.md"], "The repo docs review-docs checks."),
    ("docs_update_paths", ["README.md"], "The repo docs a task updates when its change affects them."),
    ("guardrail_denial_attempts", 2, "A denial repeated twice is a rule the task can't work around, so ask the human."),
    ("ignored_paths", [], "Paths the clean-tree check ignores, such as scratch files."),
    ("quality_gate_attempts", 3, "Three failed gate runs on one task means the fix needs the human."),
    ("remote", "origin", "The remote batches pull from and push to."),
    (
        "stale_active_days",
        20,
        "About a month of working days with commits, after which refine-backlog asks about a task.",
    ),
    (
        "throwaway_test_dir",
        ".sdlc/local/throwaway-tests",
        "Under .sdlc/local/, which is gitignored, so throwaway tests are never committed.",
    ),
    ("token_budget_per_batch", 5000000, "Stops a runaway batch before it costs too much. Tune it after a few batches."),
)
CRITIC_DEFAULTS = (
    ("external_opt_in", False, "Nothing goes to a third-party critic until you opt in."),
    ("max_diff_bytes", 200000, "A larger diff halts instead of being truncated. 200 KB covers a normal task."),
    ("min_balance", 1.0, "Stop before the provider balance runs out mid-review."),
    ("model", "haiku", "The read-only reviewer subagent's model."),
    ("provider", "subagent", "A Claude Code subagent. An external provider is opt-in."),
)
EVALS_DEFAULTS = (
    (
        "command",
        DEFAULTS["evals.command"],
        "One run, no baseline, a pinned model, and a local-only report: the per-task gate. "
        "{tag} is the skill whose cases run.",
    ),
    ("gate", "task", 'Run the changed skills\' evals after each task. "batch" runs them once at the end.'),
)


class RepoFilesError(Exception):
    pass


def write_all(repo_root, values, ids, is_plugin):
    """Write or merge each file. Returns the paths changed and the paths kept as they were."""
    changed, kept = [], []
    files = (
        (CONFIG, lambda current: current if current is not None else render_config(values, ids, is_plugin)),
        (ENV_EXAMPLE, lambda current: merge_env_example(current, secret_names(values))),
        (GITIGNORE, merge_gitignore),
        (CLAUDE_MD, lambda current: merge_claude_md(current, values, is_plugin)),
        (SETTINGS, lambda current: merge_settings(current, values, is_plugin)),
    )
    for relative_path, update in files:
        path = repo_root / relative_path
        current = path.read_text() if path.is_file() else None
        text = update(current)
        if text == current:
            kept.append(relative_path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        changed.append(relative_path)
    return changed, kept


def render_config(values, ids, is_plugin):
    overrides = values.get("overrides", {})
    known = (
        {"branch_prefix"}
        | {key for key, _, _ in TOP_LEVEL_DEFAULTS}
        | {f"critic.{key}" for key, _, _ in CRITIC_DEFAULTS}
    )
    known |= {f"evals.{key}" for key, _, _ in EVALS_DEFAULTS} if is_plugin else set()
    unknown = sorted(set(overrides) - known)
    if unknown:
        raise RepoFilesError(f"unknown overrides: {', '.join(unknown)}")
    commands = values.get("commands", {})
    kaneo, outline = ids["kaneo"], ids["outline"]
    slug = kaneo["project_slug"]

    top_level = [
        (
            "branch_prefix",
            overrides.get("branch_prefix", f"{slug.lower()}-"),
            "Task branches are <prefix><number>-<slug>. The project slug makes them easy to spot.",
        )
    ]
    for name, _ in COMMAND_LABELS:
        command = (commands.get(name) or {}).get("command", "")
        top_level.append((f"{name}_command", command, "Run by the quality gate. Empty means not configured."))
    top_level += [with_override(entry, entry[0], overrides) for entry in TOP_LEVEL_DEFAULTS]
    top_level = [("config_version", 1, "The config format this file follows."), *sorted(top_level)]

    tables = [
        ("critic", [with_override(entry, f"critic.{entry[0]}", overrides) for entry in CRITIC_DEFAULTS]),
        ("docs", [("backend", "outline", None)]),
    ]
    if is_plugin:
        tables.append(("evals", [with_override(entry, f"evals.{entry[0]}", overrides) for entry in EVALS_DEFAULTS]))
    found = ids["outline"]["guidelines"]
    tables.append(
        (
            "guidelines",
            [
                (
                    role,
                    found.get(title, ""),
                    None if title in found else f"Set to the id of the {title} doc once it exists.",
                )
                for title, role, _ in sorted(GUIDELINE_ROLES, key=lambda entry: entry[1])
                if role != "skill_authoring" or is_plugin
            ],
        )
    )
    tables.append(
        (
            "kaneo",
            [
                ("columns", kaneo["columns"], None),
                ("project_id", kaneo["project_id"], None),
                ("project_slug", slug, None),
                ("url", values["kaneo"]["url"], None),
                ("workspace_id", kaneo["workspace_id"], None),
            ],
        )
    )
    notify = values.get("notify", {})
    tables.append(
        (
            "notify",
            [
                ("enabled", notify.get("enabled", False), "Send STOP and ASK messages to the channels below."),
                (
                    "stop_hook",
                    notify.get("stop_hook", False),
                    "Also notify whenever a turn ends waiting for you. Off by default, because it can be noisy.",
                ),
            ],
        )
    )
    tables.append(
        ("outline", [("collection_id", outline["collection_id"], None), ("url", values["outline"]["url"], None)])
    )
    tables.append(("reference_check", [("allow", ["KEY-NNN"], "Placeholder keys that docs may use in examples.")]))
    tables.append(("tracker", [("backend", "kaneo", None)]))

    lines = render_entries(top_level)
    for name, entries in tables:
        lines += ["", f"[{name}]", *render_entries(entries)]
        if name == "notify":
            for channel in notify.get("channels", []):
                lines += [
                    "",
                    "[[notify.channels]]",
                    *render_entries([(key, channel[key], None) for key in sorted(channel)]),
                ]
    return "\n".join(lines) + "\n"


def with_override(entry, dotted_key, overrides):
    key = entry[0]
    # The default's reason doesn't explain a value the developer chose.
    return (key, overrides[dotted_key], "Chosen during setup-project.") if dotted_key in overrides else entry


def render_entries(entries):
    lines = []
    for key, value, why in entries:
        if why:
            lines.append(f"# {why}")
        lines.append(f"{toml_key(key)} = {toml_value(value)}")
    return lines


def toml_key(key):
    return key if re.fullmatch(r"[A-Za-z0-9_]+", key) else json.dumps(key)


def toml_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        # A JSON string is a valid TOML basic string.
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{toml_key(key)} = {toml_value(value[key])}" for key in sorted(value)) + " }"
    raise RepoFilesError(f"can't write {value!r} to TOML")


def secret_names(values):
    names = ["KANEO_API_KEY", "OUTLINE_API_KEY"]
    channel_secrets = {"discord": "DISCORD_WEBHOOK_URL", "telegram": "TELEGRAM_BOT_TOKEN"}
    names += [
        channel_secrets[channel["type"]]
        for channel in values.get("notify", {}).get("channels", [])
        if channel.get("type") in channel_secrets
    ]
    return sorted(set(names))


def merge_env_example(current, names):
    present = set(re.findall(r"^([A-Z0-9_]+)=", current or "", flags=re.MULTILINE))
    missing = [name for name in names if name not in present]
    if current is None:
        return "# Copy to .env and fill in. .env is gitignored, and only scripts read it.\n" + "".join(
            f"{name}=\n" for name in missing
        )
    return append_lines(current, [f"{name}=" for name in missing])


def merge_gitignore(current):
    present = {line.strip() for line in (current or "").splitlines()}
    missing = [entry for entry in GITIGNORE_ENTRIES if entry not in present and entry.rstrip("/") not in present]
    if not missing:
        return current
    return append_lines(current or "", ["# sdlc-llm: secrets and local state", *missing])


def append_lines(text, lines):
    if not lines:
        return text
    separator = "" if not text or text.endswith("\n") else "\n"
    return text + separator + "".join(f"{line}\n" for line in lines)


def merge_claude_md(current, values, is_plugin):
    sections = [
        ("Verifying your work", verifying_section(values)),
        ("Guidelines", guidelines_section(is_plugin)),
        ("Things Claude gets wrong", "None yet."),
    ]
    text = current if current is not None else "# CLAUDE.md\n"
    present = set(re.findall(r"^## (.+?)\s*$", text, flags=re.MULTILINE))
    for heading, body in sections:
        if heading not in present:
            text = text.rstrip("\n") + f"\n\n## {heading}\n\n{body}\n"
    return text


def verifying_section(values):
    commands = values.get("commands", {})
    lines = []
    for name, label in COMMAND_LABELS:
        command = commands.get(name) or {}
        if command.get("command"):
            healthy = command.get("healthy", "").strip()
            lines.append(f"- **{label}:** `{command['command']}`." + (f" Healthy output: {healthy}" if healthy else ""))
        else:
            lines.append(f"- **{label}:** not configured yet.")
    return "\n".join(lines)


def guidelines_section(is_plugin):
    lines = [
        "The guideline docs live in Outline under `docs/guidelines`. Their ids are under `[guidelines]` in",
        "`.sdlc/config.toml`. Read the one a step needs, when it needs it:",
        "",
    ]
    lines += [
        f"- **{title}:** {when}" for title, role, when in GUIDELINE_ROLES if role != "skill_authoring" or is_plugin
    ]
    return "\n".join(lines)


def merge_settings(current, values, is_plugin):
    try:
        settings = json.loads(current) if current else {}
    except ValueError as error:
        raise RepoFilesError(f"{SETTINGS} isn't valid JSON: {error}") from None
    if not isinstance(settings, dict):
        raise RepoFilesError(f"{SETTINGS} must hold a JSON object")
    permissions = settings.setdefault("permissions", {})
    for key, rules in (("allow", allow_rules(values, is_plugin)), ("deny", DENY_RULES)):
        existing = permissions.setdefault(key, [])
        existing += [rule for rule in rules if rule not in existing]
    text = json.dumps(settings, indent=2) + "\n"
    if current is not None and json.loads(current) == settings:
        return current
    return text


def allow_rules(values, is_plugin):
    rules = ["Bash(git *)"]
    for name, _ in COMMAND_LABELS:
        command = (values.get("commands", {}).get(name) or {}).get("command")
        if command:
            rules += [f"Bash({command})", f"Bash({command} *)"]
    if is_plugin:
        rules.append("Bash(claude plugin eval *)")
    rules += PLUGIN_SCRIPT_RULES
    rules += mcp_tools()
    return rules


def mcp_tools():
    """The MCP tools the backend maps name: the ones the skills call."""
    tools = set()
    for path in BACKEND_MAPS.glob("*.md"):
        tools.update(MCP_TOOL_PATTERN.findall(path.read_text()))
    return sorted(tools)
