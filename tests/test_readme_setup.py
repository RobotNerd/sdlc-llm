"""The README's Setup example config is accepted by the plugin."""

import re
from pathlib import Path

from lib.config import SUPPORTED_CONFIG_VERSION, load_config

README = Path(__file__).resolve().parent.parent / "README.md"
# Every key the plugin reads, per table. A key outside this set is one the plugin ignores.
KNOWN_KEYS = {
    "": {
        "config_version",
        "branch_prefix",
        "remote",
        "test_command",
        "lint_command",
        "format_command",
        "throwaway_test_dir",
        "quality_gate_attempts",
        "kaneo",
        "outline",
        "notify",
        "reference_check",
    },
    "kaneo": {"project_id", "project_slug", "url"},
    "outline": {"collection_id", "url"},
}


def first_toml_block_under_setup():
    text = README.read_text()
    setup = text.split("\n## Setup", 1)[1].split("\n## ", 1)[0]
    return re.search(r"```toml\n(.*?)```", setup, re.DOTALL).group(1)


def test_example_config_loads_when_copied_from_readme_setup(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".sdlc").mkdir()
    (tmp_path / ".sdlc/config.toml").write_text(first_toml_block_under_setup())

    config = load_config(tmp_path)

    assert config["config_version"] == SUPPORTED_CONFIG_VERSION
    for table, keys in KNOWN_KEYS.items():
        section = config if table == "" else config.get(table, {})
        assert set(section) <= keys, f"unknown keys in [{table}]: {set(section) - keys}"
