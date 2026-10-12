"""Count each task's active days: days with commits to the default branch since it was created.

Pass each task's creation time, in ISO 8601, as an argument. Prints one JSON object mapping
each time to its count, such as {"2026-09-01T10:00:00Z": 23}. The branch is
<remote>/<default_branch> from .sdlc/config.toml, or the local default branch when the remote
one isn't fetched, or HEAD when neither exists. A config problem is printed on stderr, with exit 2.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.config import ConfigError, find_repo_root, load_config, lookup


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("created_at", nargs="+", help="a task's creation time, in ISO 8601")
    arguments = parser.parse_args(argv)
    try:
        repo_root = find_repo_root()
        config = load_config(repo_root)
    except ConfigError as error:
        print(f"active days: {error}", file=sys.stderr)
        return 2
    ref = default_branch_ref(repo_root, config)
    print(json.dumps({created_at: active_days(repo_root, ref, created_at) for created_at in arguments.created_at}))
    return 0


def default_branch_ref(repo_root, config):
    branch = lookup(config, "default_branch") or "main"
    remote = lookup(config, "remote") or "origin"
    for ref in (f"{remote}/{branch}", branch):
        found = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref], cwd=repo_root, capture_output=True, check=False
        )
        if found.returncode == 0:
            return ref
    return "HEAD"


def active_days(repo_root, ref, created_at):
    log = subprocess.run(
        ["git", "log", ref, f"--since={created_at}", "--format=%cs"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    return len(set(log.stdout.split()))


if __name__ == "__main__":
    sys.exit(main())
