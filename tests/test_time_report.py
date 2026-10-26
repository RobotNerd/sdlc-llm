"""The time-report script, against fake Kimai and Kaneo servers."""

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "lib/time_report.py"


class FakeServer:
    """Answers each GET path from a dict of payloads, or with `status` when it isn't 200."""

    def __init__(self, routes, status=200):
        self.routes = routes
        self.status = status
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = urlparse(self.path).path
                payload = json.dumps(fake.routes.get(path) if fake.status == 200 else {"message": "boom"}).encode()
                self.send_response(fake.status)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def entry(user, begin, seconds):
    return {"begin": begin, "duration": seconds, "end": begin, "user": {"username": user}}


ENTRIES = [
    entry("agent", "2026-10-05T09:00:00+0000", 3 * 3600),
    entry("marshall", "2026-10-01T09:00:00+0000", 5400),
]


def epic(task_id, number, status):
    return {"id": task_id, "number": number, "status": status, "title": f"Epic {number}", "labels": [{"name": "epic"}]}


def board(tasks):
    columns = [{"slug": "to-do", "isFinal": False, "tasks": []}, {"slug": "done", "isFinal": True, "tasks": tasks}]
    return {
        "data": {"columns": columns, "plannedTasks": [], "archivedTasks": []},
        "pagination": {"totalPages": 1, "relatedTotalPages": 1},
    }


def moved_to_done(day):
    return [{"type": "status_changed", "createdAt": f"{day}T10:00:00.000Z", "eventData": {"newStatus": "done"}}]


KANEO_ROUTES = {
    "/api/task/tasks/p1": board([epic("e1", 1, "done"), epic("e2", 2, "to-do")]),
    "/api/activity/e1": moved_to_done("2026-10-15"),
}


@pytest.fixture
def fakes():
    created = []

    def make(kimai_routes=None, kimai_status=200, kaneo_routes=None, kaneo_status=200):
        kimai = FakeServer({"/api/timesheets": ENTRIES} | (kimai_routes or {}), kimai_status)
        kaneo = FakeServer(KANEO_ROUTES if kaneo_routes is None else kaneo_routes, kaneo_status)
        created.extend([kimai, kaneo])
        return kimai, kaneo

    yield make
    for server in created:
        server.close()


def make_repo(tmp_path, kimai_url=None, kaneo_url="http://127.0.0.1:9"):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".sdlc").mkdir()
    config = f'config_version = 1\n\n[kaneo]\nproject_id = "p1"\nurl = "{kaneo_url}"\n'
    if kimai_url:
        config += f'\n[time_tracking]\nurl = "{kimai_url}"\nproject_id = 3\nactivity_id = 4\nagent_user = "agent"\n'
    (tmp_path / ".sdlc/config.toml").write_text(config)
    return tmp_path


def run(repo, *flags):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *flags],
        capture_output=True,
        check=False,
        cwd=repo,
        env={"KIMAI_API_TOKEN": "k", "KANEO_API_KEY": "n", "PATH": "/usr/bin:/bin"},
        text=True,
        timeout=60,
    )


def report_for(tmp_path, fakes):
    kimai, kaneo = fakes()
    result = run(make_repo(tmp_path, kimai.url, kaneo.url))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_hours_split_by_user(tmp_path, fakes):
    assert report_for(tmp_path, fakes)["hours"] == {"total": 4.5, "agent": 3.0, "human": 1.5}


def test_user_id_resolves_through_the_users_list(tmp_path, fakes):
    entries = [{**ENTRIES[0], "user": 1}, {**ENTRIES[1], "user": 2}]
    users = [{"id": 1, "username": "agent"}, {"id": 2, "username": "marshall"}]
    kimai, kaneo = fakes({"/api/timesheets": entries, "/api/users": users})
    result = run(make_repo(tmp_path, kimai.url, kaneo.url))
    assert json.loads(result.stdout)["hours"]["agent"] == 3.0


def test_start_is_the_earliest_begin(tmp_path, fakes):
    assert report_for(tmp_path, fakes)["start"] == "2026-10-01T09:00:00+0000"


def test_done_epic_is_a_milestone(tmp_path, fakes):
    assert report_for(tmp_path, fakes)["milestones"] == [
        {"title": "Epic 1", "number": 1, "done": "2026-10-15", "days": 14}
    ]


def test_markdown_prints_both_tables(tmp_path, fakes):
    kimai, kaneo = fakes()
    result = run(make_repo(tmp_path, kimai.url, kaneo.url), "--markdown")
    assert result.returncode == 0, result.stderr
    assert "| Total | 4.50 |" in result.stdout
    assert "| Agent | 3.00 |" in result.stdout
    assert "| Human | 1.50 |" in result.stdout
    assert "| Epic 1 | 2026-10-15 | 14 |" in result.stdout


def test_missing_time_tracking_fails(tmp_path):
    result = run(make_repo(tmp_path))
    assert result.returncode != 0
    assert "[time_tracking]" in result.stderr


def test_kimai_failure_fails(tmp_path, fakes):
    kimai, kaneo = fakes(kimai_status=500)
    result = run(make_repo(tmp_path, kimai.url, kaneo.url))
    assert result.returncode != 0
    assert "Kimai" in result.stderr


def test_kaneo_failure_fails(tmp_path, fakes):
    kimai, kaneo = fakes(kaneo_status=500)
    result = run(make_repo(tmp_path, kimai.url, kaneo.url))
    assert result.returncode != 0
    assert "Kaneo" in result.stderr
