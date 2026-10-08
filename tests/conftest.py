import sys
from pathlib import Path

# Scripts import shared code as the `lib` package from the plugin root, so tests do too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
