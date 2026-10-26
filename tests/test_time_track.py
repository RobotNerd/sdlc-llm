"""The time-tracking hook: Kimai entries started and stopped around each turn."""

import json
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks/time_track.py"
STATE = ".sdlc/local/time-entry.json"


class FakeKimai:
    def __init__(self, status=200):
        self.status = status
        self.requests = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def handle_any(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                fake.requests.append(
                    {"method": self.command, "path": self.path, "auth": self.headers["Authorization"], "json": body}
                )
                payload = json.dumps({"id": 7} if fake.status == 200 else {"message": "denied"}).encode()
                self.send_response(fake.status)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_POST = do_PATCH = handle_any

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def kimai():
    fake = FakeKimai()
    yield fake
    fake.close()


def make_repo(tmp_path, url=None):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".sdlc").mkdir()
    section = ""
    if url:
        section = f'\n[time_tracking]\nurl = "{url}"\nproject_id = 3\nactivity_id = 4\nagent_user = "agent"\n'
    (tmp_path / ".sdlc/config.toml").write_text("config_version = 1\n" + section)
    return tmp_path


def run_hook(repo, event, session_id="s1"):
    hook_input = {"cwd": str(repo), "hook_event_name": event, "session_id": session_id}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        capture_output=True,
        check=False,
        cwd=ROOT,
        env={"KIMAI_API_TOKEN": "fake-token", "PATH": "/usr/bin:/bin"},
        input=json.dumps(hook_input),
        text=True,
        timeout=60,
    )


def read_state(repo):
    return json.loads((repo / STATE).read_text())


def test_prompt_with_no_entry_starts_one(tmp_path, kimai):
    repo = make_repo(tmp_path, kimai.url)
    result = run_hook(repo, "UserPromptSubmit")
    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""
    [request] = kimai.requests
    assert (request["method"], request["path"]) == ("POST", "/api/timesheets")
    assert request["auth"] == "Bearer fake-token"
    assert request["json"]["project"] == 3 and request["json"]["activity"] == 4
    state = read_state(repo)
    assert state["entry_id"] == 7 and state["session_id"] == "s1"


def test_prompt_with_a_running_entry_starts_no_second(tmp_path, kimai):
    repo = make_repo(tmp_path, kimai.url)
    run_hook(repo, "UserPromptSubmit")
    run_hook(repo, "UserPromptSubmit")
    assert len(kimai.requests) == 1


@pytest.mark.parametrize("event", ["Stop", "StopFailure", "SessionEnd"])
def test_turn_end_stops_the_entry(tmp_path, kimai, event):
    repo = make_repo(tmp_path, kimai.url)
    run_hook(repo, "UserPromptSubmit")
    result = run_hook(repo, event)
    assert result.returncode == 0 and result.stderr == ""
    assert [(r["method"], r["path"]) for r in kimai.requests[1:]] == [("PATCH", "/api/timesheets/7/stop")]
    assert not (repo / STATE).exists()


def test_stop_with_no_entry_makes_no_request(tmp_path, kimai):
    run_hook(make_repo(tmp_path, kimai.url), "Stop")
    assert kimai.requests == []


@pytest.mark.parametrize("event", ["UserPromptSubmit", "Stop", "StopFailure", "SessionEnd"])
def test_no_section_does_nothing(tmp_path, kimai, event):
    repo = make_repo(tmp_path)
    result = run_hook(repo, event)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert kimai.requests == []
    assert not (repo / STATE).exists()


def test_refused_token_warns_and_exits_zero(tmp_path):
    fake = FakeKimai(status=401)
    try:
        result = run_hook(make_repo(tmp_path, fake.url), "UserPromptSubmit")
    finally:
        fake.close()
    assert result.returncode == 0 and result.stdout == ""
    assert "warning" in result.stderr and "HTTP 401" in result.stderr
    assert "fake-token" not in result.stderr


def test_unreachable_kimai_warns_and_exits_zero(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    result = run_hook(make_repo(tmp_path, f"http://127.0.0.1:{port}"), "UserPromptSubmit")
    assert result.returncode == 0
    assert "warning" in result.stderr and "can't connect" in result.stderr
