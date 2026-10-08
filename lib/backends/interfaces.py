"""The four interfaces skills call instead of a specific tool.

Each backend implements one interface, and only the backend knows the tool's endpoints
and field names. Prose skills perform the same operations through the backend maps in
lib/references/backends/.
"""

from abc import ABC, abstractmethod


class Tracker(ABC):
    """Tasks, their order within a column, labels, relations, and comments."""

    @abstractmethod
    def add_comment(self, task_id, text):
        """Append a markdown comment to the task's worklog."""

    @abstractmethod
    def add_label(self, task_id, label_name):
        """Add a label by name. Adding one the task already has changes nothing."""

    @abstractmethod
    def add_relation(self, source_task_id, target_task_id, relation_type):
        """relation_type is "blocks" (the source is the blocker) or "subtask" (the source is the epic)."""

    @abstractmethod
    def archive_task(self, task_id):
        """Hide a task from every column. Its labels and comments survive."""

    @abstractmethod
    def create_task(self, title, description, status):
        """Return the new task's id."""

    @abstractmethod
    def get_task(self, task_id):
        """Return the task, or None when no task has that id."""

    @abstractmethod
    def list_column(self, status):
        """Return every task in the column, in priority order."""

    @abstractmethod
    def list_relations(self, task_id):
        """Return every relation the task is the source or the target of."""

    @abstractmethod
    def place_task(self, task_id, where, anchor_task_id=None):
        """Move a task within its column. where is "top", "end", or "after" (anchor_task_id)."""

    @abstractmethod
    def remove_label(self, task_id, label_name):
        """Remove a label by name. Removing one the task doesn't have changes nothing."""

    @abstractmethod
    def remove_relation(self, source_task_id, target_task_id, relation_type):
        """Remove the relation. Removing one that doesn't exist changes nothing."""

    @abstractmethod
    def search_tasks(self, query):
        """Return the project's tasks whose text matches the query."""

    @abstractmethod
    def set_status(self, task_id, status):
        """Move the task to the column named by status."""

    @abstractmethod
    def update_description(self, task_id, description):
        """Replace the description, and leave every other field as it was."""


class DocStore(ABC):
    """Docs nested in the project's collection."""

    @abstractmethod
    def archive_doc(self, doc_id):
        """Hide the doc from the collection. It stays restorable."""

    @abstractmethod
    def create_doc(self, title, text, parent_doc_id=None):
        """Create a doc under parent_doc_id, or at the top of the collection. Return its id."""

    @abstractmethod
    def find_doc(self, path):
        """Return the doc at a title path such as "docs/guidelines/Code style", or None."""

    @abstractmethod
    def get_doc(self, doc_id):
        """Return the doc's title and markdown, or None when no doc has that id."""

    @abstractmethod
    def list_children(self, doc_id):
        """Return the docs nested directly under the doc."""

    @abstractmethod
    def search_docs(self, query):
        """Return the collection's docs whose text matches the query."""

    @abstractmethod
    def update_doc(self, doc_id, find_text, replacement):
        """Replace the first match of find_text, and leave the rest of the doc intact."""


class NotifierError(Exception):
    """A message wasn't delivered. The text says why, and never holds a secret."""


class Notifier(ABC):
    """A one-way message to the developer's phone."""

    @abstractmethod
    def send(self, level, text, link_text=None, link=None):
        """Send one message, or raise NotifierError when it isn't delivered."""


class Critic(ABC):
    """An independent review of a task's change."""

    @abstractmethod
    def review(self, task, plan, diff, gate_results, review_policy, guidelines):
        """Return the verdict as a dict, in the shape the review policy defines."""
