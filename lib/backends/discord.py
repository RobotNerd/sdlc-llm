"""Send a notification through a Discord incoming webhook."""

from lib.backends.http_post import post_json
from lib.backends.interfaces import Notifier

# Discord's SUPPRESS_EMBEDS message flag, which turns off link previews.
SUPPRESS_EMBEDS = 1 << 2


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url, user_agent):
        self.webhook_url = webhook_url
        self.user_agent = user_agent

    def send(self, level, text, link_text=None, link=None):
        content = text if not link else f"{text}\n[{link_text}]({link})"
        payload = {
            "allowed_mentions": {"parse": []},
            "content": content,
            "flags": SUPPRESS_EMBEDS,
        }
        post_json(self.webhook_url, payload, self.user_agent)
