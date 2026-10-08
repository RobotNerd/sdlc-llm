"""Fake Discord and Telegram servers, and a temp repo whose config points at them."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAKE_TOKEN = "fake-bot-token-123"
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


def make_repo(tmp_path, telegram_url, enabled=True, stop_hook=False):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".sdlc").mkdir()
    (tmp_path / ".sdlc/config.toml").write_text(
        f"""\
config_version = 1

[docs]
backend = "outline"

[notify]
enabled = {"true" if enabled else "false"}
stop_hook = {"true" if stop_hook else "false"}

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


def fake_environment(discord):
    environment = {name: value for name, value in os.environ.items() if name not in SECRET_NAMES}
    environment["DISCORD_WEBHOOK_URL"] = f"{discord.url}/api/webhooks/1/fake"
    environment["TELEGRAM_BOT_TOKEN"] = FAKE_TOKEN
    return environment
