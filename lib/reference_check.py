"""Check committed files for tracker references: task keys and legacy ids.

Searches every file `git ls-files` lists for the project's task keys, built from
kaneo.project_slug in .sdlc/config.toml, and the legacy ids TASK-, EPIC-, and SPEC-
followed by digits. Matches listed in reference_check.allow are skipped. Prints each
hit as `path:line: match` and exits 1 when there's any. Prints nothing and exits 0
when there's none. A config problem is printed on stderr, with exit 2.
"""

import re
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.config import ConfigError, find_repo_root, load_config, lookup

LEGACY_PREFIXES = ("EPIC", "SPEC", "TASK")


def main():
    try:
        repo_root = find_repo_root()
        config = load_config(repo_root)
    except ConfigError as error:
        print(f"reference check: {error}", file=sys.stderr)
        return 2
    pattern = key_pattern(lookup(config, "kaneo.project_slug"))
    allowed = set(lookup(config, "reference_check.allow") or [])
    hits = [hit for hit in find_hits(repo_root, pattern) if hit[2] not in allowed]
    for path, line_number, match in hits:
        print(f"{path}:{line_number}: {match}")
    return 1 if hits else 0


def key_pattern(project_slug):
    prefixes = [*LEGACY_PREFIXES, *([project_slug] if project_slug else [])]
    return re.compile(rf"\b(?:{'|'.join(re.escape(prefix) for prefix in prefixes)})-\d+\b")


def find_hits(repo_root, pattern):
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=repo_root, capture_output=True, check=True)
    for name in listed.stdout.decode().split("\0"):
        if not name:
            continue
        for line_number, line in enumerate(text_lines(repo_root / name), start=1):
            for match in pattern.findall(line):
                yield name, line_number, match


def text_lines(path):
    """Return the file's lines, or none for a binary file or one deleted since it was committed."""
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if b"\0" in data:
        return []
    return data.decode(errors="replace").splitlines()


if __name__ == "__main__":
    sys.exit(main())
