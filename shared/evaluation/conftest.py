import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Same bare-import trick as machineB/tests/conftest.py: reach agent_loop.py
# and tools.py (M6) plus calc_engine.py (M2) without going through the cbam
# package (which imports odoo, not installed here).
UTILS_DIR = REPO_ROOT / "machineB" / "addons" / "cbam" / "utils"
ORCHESTRATOR_DIR = REPO_ROOT / "machineB" / "orchestrator"

for path in (UTILS_DIR, ORCHESTRATOR_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
