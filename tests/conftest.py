"""Load `.tasks/bin/sync` as a module for the test suite.

It has no `.py` extension and isn't part of an installable package (see
`pyproject.toml`), so it's imported by file path via `importlib`.
"""

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNC_PATH = REPO_ROOT / ".tasks" / "bin" / "sync"

# `.tasks/bin/sync` has no .py suffix, so importlib can't infer a loader from
# the path alone — supply the SourceFileLoader explicitly.
_loader = SourceFileLoader("sync", str(SYNC_PATH))
_spec = importlib.util.spec_from_loader("sync", _loader)
sync = importlib.util.module_from_spec(_spec)
sys.modules["sync"] = sync
_loader.exec_module(sync)
