import sys
from pathlib import Path

import pytest

from notify_fakes import FakeServer

# Scripts import shared code as the `lib` package from the plugin root, so tests do too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def servers():
    created = []

    def make(responses):
        server = FakeServer(responses)
        created.append(server)
        return server

    yield make
    for server in created:
        server.close()
