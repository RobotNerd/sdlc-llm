"""setup.py write and check: the repo's files merged from the values, and each backend checked."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from backend_fakes import FakeKaneo, FakeOutline

from lib.config import load_config

ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "skills/setup-project/scripts/setup.py"
SECRET_NAMES = ("DISCORD_WEBHOOK_URL", "KANEO_API_KEY", "OUTLINE_API_KEY", "TELEGRAM_BOT_TOKEN")
WORKSPACE = "workspace1"


@pytest.fixture
def backends():
    kaneo, outline = FakeKaneo(), FakeOutline()
    yield kaneo, outline
    kaneo.close()
    outline.close()


def git(repo, *arguments):
    return subprocess.run(["git", *arguments], capture_output=True, check=True, cwd=repo, text=True).stdout


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    return repo


def make_values(kaneo_url, outline_url, telegram_url=None):
    channels = [{"role": "primary", "type": "discord"}]
    if telegram_url:
        channels.append({"api_url": telegram_url, "chat_id": "4242", "role": "failover", "type": "telegram"})
    return {
        "commands": {
            "format": None,
            "lint": {"command": "ruff check .", "healthy": "`All checks passed!`"},
            "test": {"command": "python3 -m pytest", "healthy": "ends with `passed`, and no `failed` lines."},
        },
        "kaneo": {"project_name": "Example", "project_slug": "EX", "url": kaneo_url, "workspace_id": WORKSPACE},
        "notify": {"channels": channels, "enabled": True, "stop_hook": False},
        "outline": {"collection_name": "example", "url": outline_url},
        "overrides": {"quality_gate_attempts": 5},
    }


def run_setup(repo, *arguments, environment=None):
    base = {name: value for name, value in os.environ.items() if name not in SECRET_NAMES}
    base.update(environment or {"KANEO_API_KEY": "fake-kaneo-key", "OUTLINE_API_KEY": "fake-outline-key"})
    return subprocess.run(
        [sys.executable, str(SETUP), *map(str, arguments)],
        capture_output=True,
        check=False,
        cwd=repo,
        env=base,
        text=True,
        timeout=60,
    )


def check_environment(discord):
    return {
        "DISCORD_WEBHOOK_URL": f"{discord.url}/api/webhooks/1/fake",
        "KANEO_API_KEY": "fake-kaneo-key",
        "OUTLINE_API_KEY": "fake-outline-key",
        "TELEGRAM_BOT_TOKEN": "fake-bot-token",
    }


def provision_and_write(repo, values):
    values_path = repo.parent / "values.json"
    values_path.write_text(json.dumps(values))
    provisioned = run_setup(repo, "provision", values_path)
    assert provisioned.returncode == 0, provisioned.stderr
    ids_path = repo.parent / "ids.json"
    ids_path.write_text(provisioned.stdout)
    written = run_setup(repo, "write", values_path, ids_path)
    assert written.returncode == 0, written.stderr
    return json.loads(provisioned.stdout), json.loads(written.stdout)


def test_every_file_is_written_and_settings_deny_reading_env_when_the_repo_is_fresh(tmp_path, backends):
    kaneo, outline = backends
    repo = make_repo(tmp_path)

    ids, written = provision_and_write(repo, make_values(kaneo.url, outline.url))

    files = [".sdlc/config.toml", ".env.example", ".gitignore", "CLAUDE.md", ".claude/settings.json"]
    assert sorted(written["changed"]) == sorted(files)
    config = load_config(repo)
    assert config["kaneo"]["project_id"] == ids["kaneo"]["project_id"]
    assert config["kaneo"]["columns"] == ids["kaneo"]["columns"]
    assert config["outline"]["collection_id"] == ids["outline"]["collection_id"]
    assert config["guidelines"]["testing"] == ids["outline"]["guidelines"]["Testing strategy"]
    assert config["guidelines"]["architecture"] == ""
    assert config["test_command"] == "python3 -m pytest"
    assert config["format_command"] == ""
    assert config["quality_gate_attempts"] == 5
    config_lines = (repo / ".sdlc/config.toml").read_text().splitlines()
    assert config_lines[config_lines.index("quality_gate_attempts = 5") - 1] == "# Chosen during setup-project."
    assert [channel["type"] for channel in config["notify"]["channels"]] == ["discord"]
    assert (repo / ".env.example").read_text().splitlines()[1:] == [
        "DISCORD_WEBHOOK_URL=",
        "KANEO_API_KEY=",
        "OUTLINE_API_KEY=",
    ]
    assert {".env", ".sdlc/local/"} <= set((repo / ".gitignore").read_text().splitlines())
    claude_md = (repo / "CLAUDE.md").read_text()
    for heading in ("## Verifying your work", "## Guidelines", "## Things Claude gets wrong"):
        assert heading in claude_md
    assert "`python3 -m pytest`" in claude_md
    assert "- **Format:** not configured yet." in claude_md
    permissions = json.loads((repo / ".claude/settings.json").read_text())["permissions"]
    assert "Read(.env)" in permissions["deny"]
    assert {"Bash(git *)", "Bash(python3 -m pytest *)", "Bash(ruff check . *)"} <= set(permissions["allow"])
    assert "mcp__plugin_sdlc-llm_kaneo__create_task" in permissions["allow"]
    assert "mcp__plugin_sdlc-llm_outline__fetch" in permissions["allow"]


def test_nothing_changes_when_write_runs_again(tmp_path, backends):
    kaneo, outline = backends
    repo = make_repo(tmp_path)
    provision_and_write(repo, make_values(kaneo.url, outline.url))
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "--message", "setup")

    written = run_setup(repo, "write", repo.parent / "values.json", repo.parent / "ids.json")

    assert written.returncode == 0, written.stderr
    assert json.loads(written.stdout)["changed"] == []
    assert git(repo, "status", "--porcelain") == ""


def test_existing_claude_md_and_settings_are_kept_and_extended(tmp_path, backends):
    kaneo, outline = backends
    repo = make_repo(tmp_path)
    (repo / "CLAUDE.md").write_text(
        "# CLAUDE.md\n\n## House rules\n\nAlways say please.\n\n## Guidelines\n\nOur own list.\n"
    )
    (repo / ".claude").mkdir()
    (repo / ".claude/settings.json").write_text(
        json.dumps({"model": "opus", "permissions": {"allow": ["Bash(make *)"]}})
    )
    (repo / ".gitignore").write_text("node_modules/\n.env")

    provision_and_write(repo, make_values(kaneo.url, outline.url))

    claude_md = (repo / "CLAUDE.md").read_text()
    assert "## House rules\n\nAlways say please." in claude_md
    assert claude_md.count("## Guidelines") == 1
    assert "Our own list." in claude_md
    assert "## Verifying your work" in claude_md
    assert "## Things Claude gets wrong" in claude_md
    settings = json.loads((repo / ".claude/settings.json").read_text())
    assert settings["model"] == "opus"
    assert settings["permissions"]["allow"][0] == "Bash(make *)"
    assert "Bash(git *)" in settings["permissions"]["allow"]
    assert settings["permissions"]["deny"] == ["Read(.env)"]
    assert (repo / ".gitignore").read_text().splitlines() == [
        "node_modules/",
        ".env",
        "# sdlc-llm: secrets and local state",
        ".sdlc/local/",
    ]


def test_an_existing_config_is_kept(tmp_path, backends):
    kaneo, outline = backends
    repo = make_repo(tmp_path)
    (repo / ".sdlc").mkdir()
    (repo / ".sdlc/config.toml").write_text("config_version = 1\n# hand-tuned\n")

    _, written = provision_and_write(repo, make_values(kaneo.url, outline.url))

    assert ".sdlc/config.toml" in written["kept"]
    assert (repo / ".sdlc/config.toml").read_text() == "config_version = 1\n# hand-tuned\n"


def test_unknown_override_fails_naming_it(tmp_path, backends):
    kaneo, outline = backends
    repo = make_repo(tmp_path)
    values = make_values(kaneo.url, outline.url)
    values["overrides"] = {"quality_gate_attempt": 5}
    values_path, ids_path = tmp_path / "values.json", tmp_path / "ids.json"
    values_path.write_text(json.dumps(values))
    ids_path.write_text(run_setup(repo, "provision", values_path).stdout)

    result = run_setup(repo, "write", values_path, ids_path)

    assert result.returncode != 0
    assert "quality_gate_attempt" in result.stderr
    assert not (repo / ".sdlc/config.toml").exists()


def test_every_check_passes_and_each_channel_gets_a_test_message_when_backends_are_up(tmp_path, backends, servers):
    kaneo, outline = backends
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path)
    provision_and_write(repo, make_values(kaneo.url, outline.url, telegram.url))

    result = run_setup(repo, "check", environment=check_environment(discord))

    assert result.returncode == 0, result.stderr
    checks = {entry["name"]: entry for entry in json.loads(result.stdout)["checks"]}
    assert {name: entry["ok"] for name, entry in checks.items()} == {
        "discord": True,
        "kaneo": True,
        "outline": True,
        "telegram": True,
    }
    assert checks["kaneo"]["detail"] == "project EX"
    assert "setup-project · TEST" in discord.requests[0]["json"]["content"]
    assert len(telegram.requests) == 1


def test_check_fails_naming_kaneo_and_the_rest_pass_when_kaneo_is_down(tmp_path, backends, servers):
    kaneo, outline = backends
    discord = servers([(204, None)])
    repo = make_repo(tmp_path)
    provision_and_write(repo, make_values(kaneo.url, outline.url))
    kaneo.fail_with = 500

    result = run_setup(repo, "check", environment=check_environment(discord))

    assert result.returncode != 0
    checks = {entry["name"]: entry for entry in json.loads(result.stdout)["checks"]}
    assert {name: entry["ok"] for name, entry in checks.items()} == {"discord": True, "kaneo": False, "outline": True}
    assert "Kaneo: list projects: HTTP 500" in checks["kaneo"]["detail"]
    assert "kaneo" in result.stderr
    assert "fake-kaneo-key" not in result.stdout + result.stderr


def test_config_is_valid_toml_with_a_reason_above_each_default(tmp_path, backends):
    kaneo, outline = backends
    repo = make_repo(tmp_path)

    provision_and_write(repo, make_values(kaneo.url, outline.url))

    text = (repo / ".sdlc/config.toml").read_text()
    tomllib.loads(text)
    lines = text.splitlines()
    for key in ("autonomous_new_task_limit", "context_usage_halt_pct", "stale_active_days", "token_budget_per_batch"):
        index = next(number for number, line in enumerate(lines) if line.startswith(f"{key} ="))
        assert lines[index - 1].startswith("# ")
