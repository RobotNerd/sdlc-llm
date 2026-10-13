"""The prose backend maps the planning skills follow for tracker and docs calls."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MAPS = {
    "kaneo": ROOT / "lib/references/backends/kaneo.md",
    "outline": ROOT / "lib/references/backends/outline.md",
}
MAP_ROW = re.compile(r"^\|\s*`([a-z_]+)`\s*\|([^|]*)\|", re.MULTILINE)
QUOTED = re.compile(r"`([^`]+)`")


def map_rows(path):
    return {operation: QUOTED.findall(tools) for operation, tools in MAP_ROW.findall(path.read_text())}


@pytest.mark.parametrize("server", sorted(MAPS))
def test_every_map_entry_names_a_fully_qualified_tool(server):
    qualified = re.compile(rf"mcp__plugin_sdlc-llm_{server}__[a-z_]+")

    rows = map_rows(MAPS[server])

    assert rows, f"the {server} map has no operations"
    for operation, tools in rows.items():
        assert tools, f"{operation} names no tool"
        for tool in tools:
            assert qualified.fullmatch(tool), f"{operation}: {tool!r} isn't fully qualified"


def test_kaneo_map_never_mentions_whoami():
    assert "whoami" not in MAPS["kaneo"].read_text()
