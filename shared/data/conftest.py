import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
UTILS_DIR = REPO_ROOT / "softworker" / "addons" / "cbam" / "utils"

if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))
