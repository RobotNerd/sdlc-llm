"""Find the repo root and load its committed, secret-free .sdlc/config.toml."""

import tomllib
from pathlib import Path

CONFIG_PATH = ".sdlc/config.toml"
# Every skill needs to know which tracker and doc store to call. Each backend
# checks its own section's keys when it's created.
REQUIRED_KEYS = ("config_version", "docs.backend", "tracker.backend")
SUPPORTED_CONFIG_VERSION = 1
# Used when the project's config doesn't set the key.
DEFAULTS = {
    # One run, no baseline, pinned model, and a local-only report: the per-task gate.
    # {tag} is the skill whose cases run.
    "evals.command": (
        "claude plugin eval . --tag {tag} --runs 1 --ablation none --model claude-sonnet-5-5 --no-publish"
    ),
}


class ConfigError(Exception):
    pass


def find_repo_root(start=None):
    start = Path(start or Path.cwd()).resolve()
    for directory in (start, *start.parents):
        # .git is a directory in a clone, and a file in a worktree.
        if (directory / ".git").exists():
            return directory
    raise ConfigError(f"{start} is not inside a git repository, so {CONFIG_PATH} can't be found")


def load_config(start=None):
    path = find_repo_root(start) / CONFIG_PATH
    if not path.is_file():
        raise ConfigError(f"no config file at {path}; expected {CONFIG_PATH} at the repo root")
    try:
        with path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path} isn't valid TOML: {error}") from None

    missing = [key for key in REQUIRED_KEYS if lookup(config, key) is None]
    if missing:
        raise ConfigError(f"{path} is missing required keys: {', '.join(missing)}")

    version = config["config_version"]
    # bool is a subclass of int, so `true` would otherwise pass as 1.
    if type(version) is not int or version != SUPPORTED_CONFIG_VERSION:
        raise ConfigError(
            f"{path} has config_version {version!r}; "
            f"this version of sdlc-llm supports config_version {SUPPORTED_CONFIG_VERSION}"
        )
    return config


def lookup(config, dotted_key):
    value = config
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def setting(config, dotted_key):
    """Return the configured value, or the default when the config doesn't set it."""
    value = lookup(config, dotted_key)
    return DEFAULTS.get(dotted_key) if value is None else value
