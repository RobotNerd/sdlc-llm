"""Send a notification through a Telegram bot, to the developer's chat with it."""

import html

from lib.backends.http_post import post_json
from lib.backends.interfaces import Notifier, NotifierError

DEFAULT_API_URL = "https://api.telegram.org"


class TelegramNotifier(Notifier):
    def __init__(self, bot_token, chat_id, user_agent, api_url=DEFAULT_API_URL):
        self.url = f"{api_url.rstrip('/')}/bot{bot_token}/sendMessage"
        self.chat_id = chat_id
        self.user_agent = user_agent

    def send(self, level, text, link_text=None, link=None):
        message = html.escape(text, quote=False)
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
