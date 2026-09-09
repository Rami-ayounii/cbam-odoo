"""Runs the real M9 evaluation harness (run_evaluation.py) against a real
Ollama model - the actual measurement docs/PROGRESS.md's M9 section says
was blocked pending M4. Uses the real LLMClient (retry + malformed-JSON
handling included), not the raw openai client benchmark_models.py uses for
tool-call-reliability testing - this measures extraction accuracy, not
tool-calling validity.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

# Standalone-runnable bootstrap: softworker/orchestrator, softworker/addons/cbam/
# utils, and shared/data only land on sys.path automatically when pytest
# loads shared/evaluation/conftest.py. Task 7's Step 5 runs this file
# directly with plain `python run_real_evaluation.py ...` (no pytest
# involved), so the same paths need to be inserted here too - mirroring
# conftest.py's REPO_ROOT computation and benchmark_models.py's own
# standalone bootstrap - or the imports below fail with
# ModuleNotFoundError (dev_fixtures, and transitively calc_engine).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_UTILS_DIR = _REPO_ROOT / "softworker" / "addons" / "cbam" / "utils"
_ORCHESTRATOR_DIR = _REPO_ROOT / "softworker" / "orchestrator"
_SHARED_DATA_DIR = _REPO_ROOT / "shared" / "data"
for _path in (_UTILS_DIR, _ORCHESTRATOR_DIR, _SHARED_DATA_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dev_fixtures import build_emission_factor_session  # noqa: E402 - needs the sys.path bootstrap above
from llm_client import LLMClient  # noqa: E402
from run_evaluation import build_report_markdown, load_synthetic_records, run_evaluation  # noqa: E402

from benchmark_models import load_tool_schemas  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "synthetic_data" / "output"


def build_llm_client_factory(model, base_url, api_key):
    def factory(record):
        return LLMClient(model=model, base_url=base_url, api_key=api_key)

    return factory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://localhost:11434/v1")
    parser.add_argument("--api-key", default="ollama")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-iterations", type=int, default=9)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent.parent.parent / "docs" / "evaluation.md"))
    args = parser.parse_args()

    records = load_synthetic_records(DATA_DIR, limit=args.limit)
    results = run_evaluation(
        records,
        llm_client_factory=build_llm_client_factory(args.model, args.base_url, args.api_key),
        tool_schemas=load_tool_schemas(),
        declaration_date=date(2026, 1, 1),
        emission_factor_session=build_emission_factor_session(),
        max_iterations=args.max_iterations,
    )

    report = build_report_markdown(results)
    Path(args.out).write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
