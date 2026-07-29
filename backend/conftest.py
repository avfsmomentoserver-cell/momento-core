"""Pytest bootstrap for the backend package.

Placing this at the backend root means pytest adds this directory to
`sys.path` automatically, so tests import `momento`, `features` and `research`
without the hardcoded absolute paths the older standalone scripts relied on.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
