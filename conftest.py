"""Controller-installed pytest baseline for the P2 delivery repositories.

Deployed candidate repositories receive their pytest configuration from the
controller (build-plan Task 5; D-018/D-025 policy gates); the protected
verifier hash-compares these exact bytes against the checkout's
conftest.py/pytest.ini (candidate_pytest_tamper). Pinned dependency
installed from ./vendor; locally the repository root and the vendored
package are placed on ``sys.path`` directly (P2 layout: ./delivery_app/).
No network, no side effects.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _entry in (str(_ROOT), str(_ROOT / "vendor")):
    if _entry in sys.path:
        sys.path.remove(_entry)
    sys.path.insert(0, _entry)
