"""The notify script: one message to the primary channel, or to the failover when it fails."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NOTIFY = ROOT / "lib/notify.py"
FAKE_TOKEN = "fake-bot-token-123"
LINK = "https://kaneo.example.com/task?id=12&view=full"
MARKER = ".sdlc/local/notify-sent"
SECRET_NAMES = ("DISCORD_WEBHOOK_URL", "TELEGRAM_BOT_TOKEN")


class FakeServer:
    """An HTTP server that records each request and answers from a list of responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                fake.requests.append({"path": self.path, "headers": dict(self.headers), "json": json.loads(body)})
                status, payload = fake.responses.pop(0) if len(fake.responses) > 1 else fake.responses[0]
                encoded = json.dumps(payload).encode() if payload is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def servers():
    created = []

    def make(responses):
        server = FakeServer(responses)
        created.append(server)
        return server

    yield make
    for server in created:
        server.close()


def make_repo(tmp_path, telegram_url, enabled=True):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".sdlc").mkdir()
    (tmp_path / ".sdlc/config.toml").write_text(
        f"""\
config_version = 1

[docs]
backend = "outline"

[notify]
enabled = {"true" if enabled else "false"}
stop_hook = false

[[notify.channels]]
role = "primary"
type = "discord"

[[notify.channels]]
api_url = "{telegram_url}"
chat_id = "4242"
role = "failover"
type = "telegram"

[tracker]
backend = "kaneo"
"""
    )
    return tmp_path


def run_notify(repo, discord, *arguments):
    environment = {name: value for name, value in os.environ.items() if name not in SECRET_NAMES}
    environment["DISCORD_WEBHOOK_URL"] = f"{discord.url}/api/webhooks/1/fake"
    environment["TELEGRAM_BOT_TOKEN"] = FAKE_TOKEN
    command = [sys.executable, str(NOTIFY), "--project", "sdlc-llm", "--skill", "implement-task", "--kind", "STOP"]
    return subprocess.run(
        [*command, *arguments],
        capture_output=True,
        cwd=repo,
        env=environment,
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


def test_warning_and_exit_0_when_the_config_is_missing(tmp_path, servers):
    discord = servers([(204, None)])
    (tmp_path / ".git").mkdir()

    result = run_notify(tmp_path, discord, "--text", "batch finished")

    assert result.returncode == 0
    assert ".sdlc/config.toml" in result.stderr
    assert discord.requests == []
