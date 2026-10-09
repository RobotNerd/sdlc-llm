"""The Stop hook: a generic notification when a turn ends, unless a skill already sent one."""

import json
import subprocess
import sys
from pathlib import Path

from notify_fakes import MARKER, fake_environment, make_repo

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks/stop_notify.py"


def run_hook(repo, discord, stop_hook_active=False):
    stop_input = {
        "cwd": str(repo),
        "hook_event_name": "Stop",
        "session_id": "test-session",
        "stop_hook_active": stop_hook_active,
        "transcript_path": str(repo / "transcript.jsonl"),
    }
    return subprocess.run(
        [sys.executable, str(HOOK)],
        capture_output=True,
        check=False,
        cwd=ROOT,
        env=fake_environment(discord),
        input=json.dumps(stop_input),
        text=True,
        timeout=60,
    )


def write_marker(repo):
    (repo / MARKER).parent.mkdir(parents=True, exist_ok=True)
    (repo / MARKER).write_text("{}")


def test_nothing_is_sent_when_the_stop_hook_flag_is_off(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=False)

    result = run_hook(repo, discord)

    assert result.returncode == 0
    assert result.stdout == ""
    assert discord.requests == []
    assert telegram.requests == []


def test_one_generic_message_is_sent_when_the_flag_is_on_and_there_is_no_marker(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    result = run_hook(repo, discord)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert len(discord.requests) == 1
    assert telegram.requests == []
    assert not (repo / MARKER).exists()


def test_nothing_is_sent_and_the_marker_is_cleared_when_a_skill_already_notified(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)
    write_marker(repo)

    result = run_hook(repo, discord)

    assert result.returncode == 0
    assert discord.requests == []
    assert not (repo / MARKER).exists()


def test_the_next_stop_notifies_again_when_the_hook_sent_the_last_message(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    run_hook(repo, discord)
    run_hook(repo, discord)

    assert len(discord.requests) == 2


def test_the_stop_is_not_blocked_when_both_channels_fail(tmp_path, servers):
    discord, telegram = servers([(503, None)]), servers([(503, None)])
    repo = make_repo(tmp_path, telegram.url, stop_hook=True)

    result = run_hook(repo, discord)

    assert result.returncode == 0
    assert "block" not in result.stdout


def test_nothing_happens_when_the_project_has_no_config(tmp_path, servers):
    discord = servers([(204, None)])
    (tmp_path / ".git").mkdir()

    result = run_hook(tmp_path, discord)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert discord.requests == []


def test_hooks_file_runs_the_stop_hook_from_the_plugin_root():
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text())["hooks"]

    commands = [hook["command"] for entry in hooks["Stop"] for hook in entry["hooks"]]

    assert commands == ['python3 "${CLAUDE_PLUGIN_ROOT}/hooks/stop_notify.py"']
