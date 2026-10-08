"""Choosing a backend from config, and the prose backend maps that cover each interface."""

import re
from pathlib import Path

import pytest

from lib.backends import BackendError, get_backend, register
from lib.backends.interfaces import DocStore, Tracker

ROOT = Path(__file__).resolve().parent.parent
MAPS = {
    "kaneo": (Tracker, ROOT / "lib/references/backends/kaneo.md"),
    "outline": (DocStore, ROOT / "lib/references/backends/outline.md"),
}
MAP_ROW = re.compile(r"^\|\s*`([a-z_]+)`\s*\|([^|]*)\|", re.MULTILINE)
QUOTED = re.compile(r"`([^`]+)`")


class FakeTracker:
    def __init__(self, config):
        self.config = config


def operations(interface):
    return set(interface.__abstractmethods__)


def map_rows(path):
    return {operation: QUOTED.findall(tools) for operation, tools in MAP_ROW.findall(path.read_text())}


def test_configured_backend_is_returned_when_its_name_is_registered():
    register("tracker", "fake", FakeTracker)
    config = {"tracker": {"backend": "fake"}}

    backend = get_backend("tracker", config)

    assert isinstance(backend, FakeTracker)
    assert backend.config is config


def test_error_lists_the_known_backends_when_the_name_is_unknown():
    with pytest.raises(BackendError) as error:
        get_backend("tracker", {"tracker": {"backend": "jira"}})

    message = str(error.value)
    assert "jira" in message
    assert "kaneo" in message


def test_error_lists_the_known_kinds_when_the_kind_is_unknown():
    with pytest.raises(BackendError) as error:
        get_backend("calendar", {})

    assert "tracker" in str(error.value)


@pytest.mark.parametrize("server", sorted(MAPS))
def test_every_operation_is_mapped_when_the_map_is_read(server):
    interface, path = MAPS[server]

    rows = map_rows(path)

    assert set(rows) == operations(interface)


@pytest.mark.parametrize("server", sorted(MAPS))
def test_every_map_entry_names_a_fully_qualified_tool(server):
    _, path = MAPS[server]
    qualified = re.compile(rf"mcp__plugin_sdlc-llm_{server}__[a-z_]+")

    for operation, tools in map_rows(path).items():
        assert tools, f"{operation} names no tool"
        for tool in tools:
            assert qualified.fullmatch(tool), f"{operation}: {tool!r} isn't fully qualified"


def test_kaneo_map_never_mentions_whoami():
    _, path = MAPS["kaneo"]

    assert "whoami" not in path.read_text()
