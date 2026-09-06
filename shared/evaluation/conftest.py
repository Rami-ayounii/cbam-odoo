import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Same bare-import trick as machineB/tests/conftest.py: reach agent_loop.py
# and tools.py (M6) plus calc_engine.py (M2) without going through the cbam
# package (which imports odoo, not installed here).
UTILS_DIR = REPO_ROOT / "machineB" / "addons" / "cbam" / "utils"
ORCHESTRATOR_DIR = REPO_ROOT / "machineB" / "orchestrator"
# shared/data/ holds dev_fixtures.py (Task 4's build_emission_factor_session,
# used by run_real_evaluation.py) - it's a sibling directory to this one, not
# an ancestor, so pytest's own rootdir-based sys.path insertion never reaches
# it. shared/data/conftest.py adds UTILS_DIR for its own tests but has no
# reason to know about this directory, so it's added independently here
# (same pattern as machineB/tests/conftest.py and this file both adding
# UTILS_DIR/ORCHESTRATOR_DIR independently rather than relying on each other).
DATA_DIR = REPO_ROOT / "shared" / "data"

for path in (UTILS_DIR, ORCHESTRATOR_DIR, DATA_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
