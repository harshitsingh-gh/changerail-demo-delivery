"""Deployed candidate repository path shim (generated at install).

Pinned dependency installed from ./vendor (the CI workflow does
``python -m pip install vendor/``); locally, the package directory and the
vendored package are placed on ``sys.path`` directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _entry in (str(_ROOT / "delivery_app"), str(_ROOT / "vendor")):
    if _entry in sys.path:
        sys.path.remove(_entry)
    sys.path.insert(0, _entry)
