"""JSON over HTTP for the backend modules, with errors that name the service and the step."""

import json
import urllib.error
import urllib.parse
import urllib.request

# A setup step makes one small request. A backend that takes longer is treated as down.
TIMEOUT_SECONDS = 20
# Enough of an error body to show the service's reason without flooding the terminal.
MAX_ERROR_TEXT = 300
USER_AGENT = "sdlc-llm"


class RestError(Exception):
    """A request failed. The text names the service and the step, and never holds the API key."""


class RestClient:
    def __init__(self, service, base_url, api_key):
        self.service = service
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def request(self, step, method, path, body=None, query=None):
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(
            url,
            data=None if body is None else json.dumps(body).encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            reason = error.read().decode(errors="replace").strip()[:MAX_ERROR_TEXT]
            raise RestError(f"{self.service}: {step}: HTTP {error.code}{': ' + reason if reason else ''}") from None
        except (urllib.error.URLError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise RestError(f"{self.service}: {step}: can't connect ({reason})") from None
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            raise RestError(f"{self.service}: {step}: the response isn't JSON") from None
