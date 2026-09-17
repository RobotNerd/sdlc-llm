"""Load `.tasks/bin/sync` and `.tasks/bin/guardrails` as modules for the test suite.

`sync` has no `.py` extension and isn't part of an installable package (see
`pyproject.toml`), so it's imported by file path via `importlib`. `guardrails.py` does have
the extension but lives alongside `sync` outside any package too, and itself loads `sync` the
same way (reusing this same `sys.modules["sync"]` entry rather than re-executing the file) --
imported here second, after `sync` is already in `sys.modules`, so both stay the same instance
everywhere in the suite.
"""

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNC_PATH = REPO_ROOT / ".tasks" / "bin" / "sync"
GUARDRAILS_PATH = REPO_ROOT / ".tasks" / "bin" / "guardrails.py"

# `.tasks/bin/sync` has no .py suffix, so importlib can't infer a loader from
# the path alone — supply the SourceFileLoader explicitly.
_loader = SourceFileLoader("sync", str(SYNC_PATH))
_spec = importlib.util.spec_from_loader("sync", _loader)
sync = importlib.util.module_from_spec(_spec)
sys.modules["sync"] = sync
_loader.exec_module(sync)

_guardrails_loader = SourceFileLoader("guardrails", str(GUARDRAILS_PATH))
_guardrails_spec = importlib.util.spec_from_loader("guardrails", _guardrails_loader)
guardrails = importlib.util.module_from_spec(_guardrails_spec)
sys.modules["guardrails"] = guardrails
_guardrails_loader.exec_module(guardrails)
