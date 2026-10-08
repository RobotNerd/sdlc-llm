"""The repo is a valid Claude Code plugin, and is its own marketplace."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER_CONFIG_REF = re.compile(r"\$\{user_config\.([A-Za-z_][A-Za-z0-9_]*)\}")


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text())


def test_manifest_names_the_plugin_and_asks_for_both_urls():
    manifest = load_json(".claude-plugin/plugin.json")

    assert manifest["name"] == "sdlc-llm"
    assert {"kaneo_url", "outline_url"} <= set(manifest["userConfig"])
    for option in manifest["userConfig"].values():
        assert {"type", "title", "description"} <= set(option)


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

    assert set(servers) == {"kaneo", "outline"}
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


def test_standard_directories_and_hooks_file_exist():
    for directory in ("skills", "lib/backends", "lib/references/backends", "evals", "tests"):
        assert (ROOT / directory).is_dir(), f"{directory}/ is missing"
    assert "hooks" in load_json("hooks/hooks.json")


def test_no_project_mcp_file_at_the_root():
    # A root .mcp.json would also load as this repo's own project MCP config, where
    # ${user_config.*} never resolves. The plugin's servers live in mcp.json instead.
    assert not (ROOT / ".mcp.json").exists()
