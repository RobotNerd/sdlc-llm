"""The interface every notification channel implements."""

from abc import ABC, abstractmethod


class NotifierError(Exception):
    """A message wasn't delivered. The text says why, and never holds a secret."""


class Notifier(ABC):
    """A one-way message to the developer's phone."""

    @abstractmethod
    def send(self, level, text, link_text=None, link=None):
        """Send one message, or raise NotifierError when it isn't delivered."""
