"""Pick the backend that .sdlc/config.toml names for each interface."""

import importlib

from lib.config import lookup

# The notifier isn't here: the notify script builds one per configured channel.
CONFIG_KEYS = {
    "critic": "critic.provider",
    "docstore": "docs.backend",
    "tracker": "tracker.backend",
}
# Imported only when chosen, so one backend's module never loads another's.
BUILT_IN = {
    "critic": {},
    "docstore": {"outline": ("lib.backends.outline", "OutlineDocStore")},
    "tracker": {"kaneo": ("lib.backends.kaneo", "KaneoTracker")},
}
registered = {kind: {} for kind in CONFIG_KEYS}


class BackendError(Exception):
    pass


def register(kind, name, factory):
    """Make a backend choosable by name. factory(config) returns the backend."""
    known_kind(kind)
    registered[kind][name] = factory


def get_backend(kind, config):
    known_kind(kind)
    key = CONFIG_KEYS[kind]
    name = lookup(config, key)
    known = sorted({*BUILT_IN[kind], *registered[kind]})
    if name in registered[kind]:
        return registered[kind][name](config)
    if name not in BUILT_IN[kind]:
        raise BackendError(f"unknown {kind} backend {name!r} in {key}; known backends: {', '.join(known) or 'none'}")

    module_name, class_name = BUILT_IN[kind][name]
    try:
        backend_class = getattr(importlib.import_module(module_name), class_name, None)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        backend_class = None
    if backend_class is None:
        raise BackendError(
            f"the {name} {kind} backend has no script implementation yet; "
            f"prose skills use lib/references/backends/{name}.md"
        )
    return backend_class(config)


def known_kind(kind):
    if kind not in CONFIG_KEYS:
        raise BackendError(f"unknown backend kind {kind!r}; known kinds: {', '.join(sorted(CONFIG_KEYS))}")
