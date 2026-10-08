"""Send one STOP or ASK notification to the primary channel, or to the failover when it fails.

A failed notification never blocks a skill: every failure is a warning on stderr,
and the exit code is 0. Prints the result as JSON on stdout.
"""

import argparse
import json
import sys
import time
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.backends.discord import DiscordNotifier
from lib.backends.interfaces import NotifierError
from lib.backends.telegram import DEFAULT_API_URL, TelegramNotifier
from lib.config import ConfigError, find_repo_root, load_config
from lib.env import EnvError, load_env, require_secret

KINDS = ("ASK", "STOP")
# The Stop hook skips its own message while this exists.
MARKER_PATH = ".sdlc/local/notify-sent"
ROLES = ("primary", "failover")


class NotifyError(Exception):
    pass


def main(argv=None):
    arguments = parse_arguments(argv)
    try:
        result = notify(arguments)
    except (ConfigError, EnvError, NotifyError) as error:
        result = {"sent_to": None, "warning": f"notification not sent: {error}"}
    except Exception as error:
        # Anything unexpected is still only a warning, so the skill carries on.
        result = {"sent_to": None, "warning": f"notification not sent: unexpected {type(error).__name__}"}
    if "warning" in result:
        print(f"warning: {result['warning']}", file=sys.stderr)
    print(json.dumps(result))
    return 0


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kind", choices=KINDS, required=True)
    parser.add_argument("--link", help="a URL, shown as link text")
    parser.add_argument("--link-text", help='defaults to "Open <task>", or "Open" with no task')
    parser.add_argument("--project", help="defaults to the repo's directory name")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--task", help="the task key, such as KEY-12")
    parser.add_argument("--text", required=True, help="what's needed, in a few words")
    return parser.parse_args(argv)


def notify(arguments, start=None):
    repo_root = find_repo_root(start)
    config = load_config(repo_root)
    settings = config.get("notify", {})
    if not settings.get("enabled", False):
        return {"sent_to": None, "reason": "notifications are off"}

    text, link_text = message(arguments, repo_root)
    failures = []
    for channel in channels_in_order(settings):
        name = channel.get("type", "unknown")
        try:
            build_notifier(channel, repo_root).send(arguments.kind, text, link_text, arguments.link)
        except (EnvError, NotifierError, NotifyError) as error:
            failures.append(f"{name}: {error}")
            continue
        write_marker(repo_root)
        result = {"sent_to": name}
        if failures:
            result["warning"] = f"sent to {name}, the failover, after {'; '.join(failures)}"
        return result
    raise NotifyError("; ".join(failures) or "no channels in notify.channels")


def message(arguments, repo_root):
    project = arguments.project or repo_root.name
    prefix = " · ".join([project, arguments.skill, arguments.kind, *([arguments.task] if arguments.task else [])])
    link_text = arguments.link_text or " ".join(["Open", *([arguments.task] if arguments.task else [])])
    return f"{prefix}: {arguments.text}", link_text


def channels_in_order(settings):
    channels = settings.get("channels", [])
    for channel in channels:
        if channel.get("role") not in ROLES:
            raise NotifyError(f"notify.channels role {channel.get('role')!r} must be one of: {', '.join(ROLES)}")
    return sorted(channels, key=lambda channel: ROLES.index(channel["role"]))


def build_notifier(channel, repo_root):
    env_path = repo_root / ".env"
    secrets = load_env(env_path)
    user_agent = f"sdlc-llm-notify/{plugin_version()}"
    channel_type = channel.get("type")
    if channel_type == "discord":
        return DiscordNotifier(require_secret(secrets, "DISCORD_WEBHOOK_URL", env_path), user_agent)
    if channel_type == "telegram":
        if "chat_id" not in channel:
            raise NotifyError("notify.channels for telegram needs chat_id")
        return TelegramNotifier(
            require_secret(secrets, "TELEGRAM_BOT_TOKEN", env_path),
            channel["chat_id"],
            user_agent,
            channel.get("api_url", DEFAULT_API_URL),
        )
    raise NotifyError(f"unknown notify.channels type {channel_type!r}; known types: discord, telegram")


def plugin_version():
    try:
        return json.loads((PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text())["version"]
    except (OSError, KeyError, ValueError):
        return "unknown"


def write_marker(repo_root):
    marker = repo_root / MARKER_PATH
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"sent_at": time.time()}))


if __name__ == "__main__":
    sys.exit(main())
