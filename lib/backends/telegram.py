"""Send a notification through a Telegram bot, to the developer's chat with it."""

import html
import re

from lib.backends.http_post import post_json
from lib.backends.interfaces import Notifier, NotifierError

DEFAULT_API_URL = "https://api.telegram.org"
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


class TelegramNotifier(Notifier):
    def __init__(self, bot_token, chat_id, user_agent, api_url=DEFAULT_API_URL):
        self.url = f"{api_url.rstrip('/')}/bot{bot_token}/sendMessage"
        self.chat_id = chat_id
        self.user_agent = user_agent

    def send(self, level, text, link_text=None, link=None):
        message = html_with_links(text)
        if link:
            message += f'\n<a href="{html.escape(link)}">{html.escape(link_text, quote=False)}</a>'
        payload = {
            "chat_id": self.chat_id,
            "link_preview_options": {"is_disabled": True},
            "parse_mode": "HTML",
            "text": message,
        }
        body = post_json(self.url, payload, self.user_agent)
        if isinstance(body, dict) and body.get("ok") is False:
            raise NotifierError(f"Telegram refused the message: {body.get('description', 'no reason given')}")


def html_with_links(text):
    """Escape text for Telegram's HTML mode, turning each Markdown link into an anchor."""
    parts, start = [], 0
    for match in MARKDOWN_LINK.finditer(text):
        parts.append(html.escape(text[start : match.start()], quote=False))
        parts.append(f'<a href="{html.escape(match.group(2))}">{html.escape(match.group(1), quote=False)}</a>')
        start = match.end()
    parts.append(html.escape(text[start:], quote=False))
    return "".join(parts)
