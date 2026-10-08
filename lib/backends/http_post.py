"""POST JSON to a notification service, retrying once when it's rate limited.

Request URLs can hold a secret (a webhook URL or a bot token), so no error here
includes the URL.
"""

import json
import time
import urllib.error
import urllib.request

from lib.backends.interfaces import NotifierError

# Both services answered in about a second in testing. A hung send must not stall a skill.
TIMEOUT_SECONDS = 10
# A notification isn't worth a longer wait. A 429 asking for more counts as a failure.
MAX_RETRY_WAIT_SECONDS = 5
# Used when a 429 doesn't say how long to wait.
DEFAULT_RETRY_WAIT_SECONDS = 1
TOO_MANY_REQUESTS = 429


def post_json(url, payload, user_agent):
    """Return the response's parsed JSON body, or None when it has none."""
    status, headers, body = send_once(url, payload, user_agent)
    if status == TOO_MANY_REQUESTS:
        wait = retry_wait(headers, body)
        if wait > MAX_RETRY_WAIT_SECONDS:
            raise NotifierError(f"rate limited for {wait:g}s")
        time.sleep(wait)
        status, headers, body = send_once(url, payload, user_agent)
    if not 200 <= status < 300:
        raise NotifierError(f"HTTP {status}")
    return body


def send_once(url, payload, user_agent):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": user_agent},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.headers, parse_body(response.read())
    except urllib.error.HTTPError as error:
        return error.code, error.headers, parse_body(error.read())
    except (urllib.error.URLError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise NotifierError(f"network error: {type(reason).__name__}") from None


def parse_body(raw):
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None


def retry_wait(headers, body):
    body = body if isinstance(body, dict) else {}
    # Discord puts retry_after at the top of the body, and Telegram under parameters.
    candidates = (
        headers.get("Retry-After"),
        body.get("retry_after"),
        (body.get("parameters") or {}).get("retry_after"),
    )
    for candidate in candidates:
        try:
            return max(float(candidate), 0)
        except (TypeError, ValueError):
            continue
    return DEFAULT_RETRY_WAIT_SECONDS
