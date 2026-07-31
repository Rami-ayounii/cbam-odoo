import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Point straight at cbam/utils/, not machineB/addons/, so importing
# calc_engine never executes cbam/__init__.py (which imports models, which
# imports `odoo` - not installed outside a real Odoo environment). This
# keeps the calc engine unit-testable standalone, as designed in M2. The
# orchestrator (M6) needs this same trick for real: it runs in its own
# container with no Odoo installed, so it also imports calc_engine as a bare
# module with this directory on its PYTHONPATH, never through `cbam.utils`.
UTILS_DIR = BASE_DIR / "addons" / "cbam" / "utils"

# The orchestrator's own modules (agent_loop, tools, llm_client, odoo_client)
# are likewise plain, non-packaged modules so they can be imported directly.
ORCHESTRATOR_DIR = BASE_DIR / "orchestrator"

for path in (UTILS_DIR, ORCHESTRATOR_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
