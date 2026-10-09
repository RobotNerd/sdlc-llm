"""Load secrets from a .env file. A real environment variable overrides the file.

Error messages name the file, the line number, and the key, but never a value: any
line of a .env file may hold a secret.
"""

import os
import re
from pathlib import Path

KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
DOUBLE_QUOTE_ESCAPES = {'"': '"', "\\": "\\", "n": "\n"}


class EnvError(Exception):
    pass


def load_env(path, environ=None):
    """Return the file's values overlaid with the environment's.

    A missing file isn't an error: in CI every secret comes from the environment.
    """
    path = Path(path)
    environ = os.environ if environ is None else environ
    values = parse_env_file(path) if path.is_file() else {}
    values.update(environ)
    return values


def require_secret(values, name, path):
    value = values.get(name)
    if not value:
        raise EnvError(f"{name} is not set; add it to {path} or set it in the environment")
    return value


def parse_env_file(path):
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        raise EnvError(f"{path} isn't valid UTF-8") from None

    values = {}
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or not KEY_PATTERN.fullmatch(key):
            raise EnvError(f"{path}:{line_number}: expected KEY=VALUE")
        values[key] = parse_value(raw_value.strip(), f"{path}:{line_number}: {key}")
    return values


def parse_value(raw_value, location):
    if not raw_value or raw_value[0] not in "\"'":
        # An unquoted value ends at a comment that follows whitespace.
        return re.split(r"\s+#", raw_value, maxsplit=1)[0]

    quote = raw_value[0]
    characters = []
    index = 1
    while index < len(raw_value):
        character = raw_value[index]
        if character == quote:
            rest = raw_value[index + 1 :].strip()
            if rest and not rest.startswith("#"):
                raise EnvError(f"{location}: unexpected text after the closing quote")
            return "".join(characters)
        if quote == '"' and character == "\\" and index + 1 < len(raw_value):
            escaped = raw_value[index + 1]
            characters.append(DOUBLE_QUOTE_ESCAPES.get(escaped, "\\" + escaped))
            index += 2
            continue
        characters.append(character)
        index += 1
    raise EnvError(f"{location}: missing the closing {quote}")
