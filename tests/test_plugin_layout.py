"""The repo is a valid Claude Code plugin, and is its own marketplace."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
USER_CONFIG_REF = re.compile(r"\$\{user_config\.([A-Za-z_][A-Za-z0-9_]*)\}")


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text())


def test_manifest_names_the_plugin_and_asks_for_the_server_urls():
    manifest = load_json(".claude-plugin/plugin.json")

    assert manifest["name"] == "sdlc-llm"
    assert set(manifest["userConfig"]) == {"kaneo_url", "kimai_mcp_url", "outline_url"}
    for option in manifest["userConfig"].values():
        assert {"type", "title", "description"} <= set(option)
        assert option["required"] is True
        assert re.search(r"https?://\S+[^/\s,.]", option["description"])


def test_every_component_path_in_the_manifest_exists_inside_the_plugin():
    manifest = load_json(".claude-plugin/plugin.json")

    for key in ("mcpServers", "hooks", "skills", "commands", "agents"):
        paths = manifest.get(key, [])
        for path in [paths] if isinstance(paths, str) else paths:
            assert path.startswith("./"), f"{key} path {path!r} must start with ./"
            resolved = (ROOT / path).resolve()
            assert resolved.is_relative_to(ROOT), f"{key} path {path!r} escapes the plugin"
            assert resolved.exists(), f"{key} path {path!r} doesn't exist"


def test_mcp_servers_use_only_declared_user_config_values():
    declared = set(load_json(".claude-plugin/plugin.json")["userConfig"])
    servers = load_json("mcp.json")["mcpServers"]

    assert servers["kimai"]["url"] == "${user_config.kimai_mcp_url}"
    assert set(servers) == {"kaneo", "kimai", "outline"}
    for name, server in servers.items():
        assert server["type"] == "http"
        referenced = set(USER_CONFIG_REF.findall(server["url"]))
        assert referenced, f"{name} URL doesn't come from userConfig"
        assert referenced <= declared, f"{name} URL references undeclared {referenced - declared}"


def test_marketplace_lists_the_plugin_at_the_repo_root():
    marketplace = load_json(".claude-plugin/marketplace.json")

    entries = {entry["name"]: entry for entry in marketplace["plugins"]}
    assert entries["sdlc-llm"]["source"] == "./"
    assert (ROOT / ".claude-plugin/plugin.json").exists()


def test_plugin_manifest_points_at_the_github_repo_the_install_steps_use():
    repository = load_json(".claude-plugin/plugin.json")["repository"]
    assert repository == "https://github.com/RobotNerd/sdlc-llm"


def test_no_version_pins_the_installed_plugin():
    # A version in either place keeps an install on its cached copy until the string
    # changes. Without one, Claude Code versions the install by commit SHA, so every
    # merge to main reaches it.
    assert "version" not in load_json(".claude-plugin/plugin.json")
    for entry in load_json(".claude-plugin/marketplace.json")["plugins"]:
        assert "version" not in entry


def test_standard_directories_and_hooks_file_exist():
    for directory in ("skills", "lib/backends", "tests"):
        assert (ROOT / directory).is_dir(), f"{directory}/ is missing"
    assert "hooks" in load_json("hooks/hooks.json")


def test_no_project_mcp_file_at_the_root():
    # A root .mcp.json would also load as this repo's own project MCP config, where
    # ${user_config.*} never resolves. The plugin's servers live in mcp.json instead.
    assert not (ROOT / ".mcp.json").exists()


def test_skills_use_only_declared_user_config_values():
    declared = set(load_json(".claude-plugin/plugin.json")["userConfig"])

    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        referenced = set(USER_CONFIG_REF.findall(skill.read_text()))
        assert referenced <= declared, f"{skill.parent.name} references undeclared {referenced - declared}"


@pytest.mark.parametrize("name", ("draw", "groom", "plan", "work"))
def test_skill_is_short_with_valid_frontmatter(name):
    text = (ROOT / f"skills/{name}/SKILL.md").read_text()
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md has no frontmatter"
    fields = dict(line.split(": ", 1) for line in match.group(1).splitlines())

    assert fields["name"] == name
    assert 0 < len(fields["description"]) <= 1024
    assert len(text.splitlines()) < 60


def test_only_the_v3_skills_exist():
    assert sorted(path.name for path in (ROOT / "skills").iterdir()) == ["draw", "groom", "plan", "work"]
