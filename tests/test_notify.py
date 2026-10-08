"""The notify script: one message to the primary channel, or to the failover when it fails."""

import subprocess
import sys
from pathlib import Path

from notify_fakes import FAKE_TOKEN, MARKER, fake_environment, make_repo

ROOT = Path(__file__).resolve().parent.parent
NOTIFY = ROOT / "lib/notify.py"
LINK = "https://kaneo.example.com/task?id=12&view=full"


def run_notify(repo, discord, *arguments):
    command = [sys.executable, str(NOTIFY), "--project", "sdlc-llm", "--skill", "implement-task", "--kind", "STOP"]
    return subprocess.run(
        [*command, *arguments],
        capture_output=True,
        cwd=repo,
        env=fake_environment(discord),
        text=True,
        timeout=30,
    )


def test_nothing_is_sent_when_notifications_are_off(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url, enabled=False)

    result = run_notify(repo, discord, "--text", "critic rejected 3×, decision needed")

    assert result.returncode == 0
    assert discord.requests == []
    assert telegram.requests == []
    assert not (repo / MARKER).exists()


def test_one_discord_message_is_sent_when_discord_is_up(tmp_path, servers):
    discord, telegram = servers([(204, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url)

    result = run_notify(
        repo, discord, "--task", "SDLC-12", "--text", "critic rejected 3×, decision needed", "--link", LINK
    )

    assert result.returncode == 0, result.stderr
    assert len(discord.requests) == 1
    request = discord.requests[0]
    assert request["path"] == "/api/webhooks/1/fake"
    assert request["json"]["content"] == (
        "sdlc-llm · implement-task · STOP · SDLC-12: critic rejected 3×, decision needed\n"
        f"[Open SDLC-12]({LINK})"
    )
    assert request["headers"]["User-Agent"].startswith("sdlc-llm-notify/")
    assert telegram.requests == []
    assert (repo / MARKER).is_file()


def test_telegram_gets_the_message_when_discord_fails(tmp_path, servers):
    discord, telegram = servers([(503, None)]), servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url)

    result = run_notify(repo, discord, "--task", "SDLC-12", "--text", "tests <failed> & stopped", "--link", LINK)

    assert result.returncode == 0, result.stderr
    assert len(telegram.requests) == 1
    request = telegram.requests[0]
    assert request["path"] == f"/bot{FAKE_TOKEN}/sendMessage"
    assert request["headers"]["User-Agent"].startswith("sdlc-llm-notify/")
    assert request["json"]["chat_id"] == "4242"
    assert request["json"]["parse_mode"] == "HTML"
    assert request["json"]["link_preview_options"] == {"is_disabled": True}
    assert request["json"]["text"] == (
        "sdlc-llm · implement-task · STOP · SDLC-12: tests &lt;failed&gt; &amp; stopped\n"
        '<a href="https://kaneo.example.com/task?id=12&amp;view=full">Open SDLC-12</a>'
    )
    assert discord.requests[0]["headers"]["User-Agent"].startswith("sdlc-llm-notify/")
    assert (repo / MARKER).is_file()
    assert "sent to telegram" in result.stderr
    assert "not sent" not in result.stderr


def test_discord_is_retried_once_when_it_answers_429(tmp_path, servers):
    discord = servers([(429, {"retry_after": 0.01}), (204, None)])
    telegram = servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url)

    result = run_notify(repo, discord, "--text", "batch finished")

    assert result.returncode == 0, result.stderr
    assert len(discord.requests) == 2
    assert telegram.requests == []


def test_telegram_gets_the_message_when_discord_still_answers_429_after_a_retry(tmp_path, servers):
    discord = servers([(429, {"retry_after": 0.01})])
    telegram = servers([(200, {"ok": True})])
    repo = make_repo(tmp_path, telegram.url)

    result = run_notify(repo, discord, "--text", "batch finished")

    assert result.returncode == 0, result.stderr
    assert len(discord.requests) == 2
    assert len(telegram.requests) == 1


def test_warning_and_exit_0_when_both_channels_fail(tmp_path, servers):
    discord, telegram = servers([(503, None)]), servers([(503, None)])
    repo = make_repo(tmp_path, telegram.url)

    result = run_notify(repo, discord, "--text", "batch finished")

    assert result.returncode == 0
    assert "warning" in result.stderr.lower()
    assert FAKE_TOKEN not in result.stderr
    assert "/api/webhooks/" not in result.stderr
    assert not (repo / MARKER).exists()


def test_warning_gives_the_services_reason_when_a_channel_refuses_the_message(tmp_path, servers):
    discord = servers([(404, {"message": "Unknown Webhook", "code": 10015})])
    telegram = servers([(400, {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"})])
    repo = make_repo(tmp_path, telegram.url)

    result = run_notify(repo, discord, "--text", "batch finished")

    assert result.returncode == 0
    assert "Unknown Webhook" in result.stderr
    assert "Bad Request: chat not found" in result.stderr
    assert FAKE_TOKEN not in result.stderr


def test_warning_and_exit_0_when_the_config_is_missing(tmp_path, servers):
    discord = servers([(204, None)])
    (tmp_path / ".git").mkdir()

    result = run_notify(tmp_path, discord, "--text", "batch finished")

    assert result.returncode == 0
    assert ".sdlc/config.toml" in result.stderr
    assert discord.requests == []
