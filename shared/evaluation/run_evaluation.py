"""M9 evaluation harness: runs the real agent loop (M6) against the
synthetic dataset (M1) and scores the result against ground truth.

STATUS: the harness itself is complete and drives the real agent_loop.py /
tools.py code (not a reimplementation), but it has only ever been exercised
with a scripted fake LLM client (see test_run_evaluation.py) - M4 being
blocked means no real Ollama model has driven this yet. Do not treat
anything this produces as a real evaluation - see docs/PROGRESS.md's M9
section for exactly what's needed to run it for real.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from agent_loop import run_agent_loop
from tools import ToolDispatcher

from scoring import aggregate_field_scores, score_record

from main import SYSTEM_PROMPT


def load_synthetic_records(data_dir, limit: Optional[int] = 20) -> List[dict]:
    data_dir = Path(data_dir)
    with (data_dir / "index.json").open(encoding="utf-8") as f:
        index = json.load(f)
    if limit is not None:
        index = index[:limit]

    records = []
    for entry in index:
        with (data_dir / f"{entry['record_id']}.json").open(encoding="utf-8") as f:
            records.append(json.load(f))
    return records


class FixtureOdooClient:
    """Serves one synthetic record's document text; the final write is
    recorded in-memory for scoring. Never talks to a real Odoo instance -
    that's the whole point of using synthetic ground-truth data here."""

    def __init__(self, document_text, emission_factor_session=None):
        self._document_text = document_text
        self._emission_factor_session = emission_factor_session
        self.written = None

    def get_source_document_text(self, document_id, expected_declaration_line_id):
        # No real declaration/ownership concept in this fixture - it always
        # serves the one synthetic record's document text (see class
        # docstring); expected_declaration_line_id exists only so this
        # matches ToolDispatcher's real call signature.
        return self._document_text

    def get_emission_factor_session(self):
        return self._emission_factor_session

    def write_declaration_line(self, **data):
        self.written = data
        return 1


@dataclass
class EvaluationResult:
    record_id: str
    status: str
    iterations: int
    field_scores: dict = field(default_factory=dict)
    error: Optional[str] = None


def run_evaluation_on_record(
    record,
    llm_client,
    tool_schemas,
    declaration_date,
    emission_factor_session=None,
    max_iterations=9,
    declaration_id=1,
    declaration_line_id=1,
) -> EvaluationResult:
    # declaration_id/declaration_line_id are fixture placeholders, not real
    # Odoo IDs - this harness never talks to a real Odoo instance (see
    # FixtureOdooClient). They exist only so write_declaration_line's
    # ownership check (tools.py) has something to compare the LLM's
    # tool-call declaration_id against.
    odoo_client = FixtureOdooClient(
        document_text=record["document_text"],
        emission_factor_session=emission_factor_session,
    )
    dispatcher = ToolDispatcher(
        odoo_client,
        declaration_date=declaration_date,
        declaration_id=declaration_id,
        declaration_line_id=declaration_line_id,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Process document {record['record_id']}:\n\n{record['document_text']}",
        },
    ]

    try:
        result = run_agent_loop(
            messages=messages,
            llm_client=llm_client,
            tool_schemas=tool_schemas,
            execute_tool=dispatcher.execute,
            max_iterations=max_iterations,
        )
    except Exception as exc:
        return EvaluationResult(
            record_id=record["record_id"], status="error", iterations=0, error=str(exc)
        )

    field_scores = score_record(record["ground_truth"], odoo_client.written or {})
    return EvaluationResult(
        record_id=record["record_id"],
        status=result.status,
        iterations=result.iterations,
        field_scores=field_scores,
    )


def run_evaluation(
    records,
    llm_client_factory: Callable[[dict], object],
    tool_schemas,
    declaration_date,
    emission_factor_session=None,
    max_iterations=9,
) -> List[EvaluationResult]:
    return [
        run_evaluation_on_record(
            record,
            llm_client_factory(record),
            tool_schemas,
            declaration_date,
            emission_factor_session,
            max_iterations,
        )
        for record in records
    ]


def build_report_markdown(results: List[EvaluationResult]) -> str:
    status_counts: dict = {}
    iteration_counts: dict = {}
    all_field_scores = []
    errors = []

    for r in results:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        iteration_counts[r.iterations] = iteration_counts.get(r.iterations, 0) + 1
        if r.field_scores:
            all_field_scores.append(r.field_scores)
        if r.error:
            errors.append((r.record_id, r.error))

    aggregated = aggregate_field_scores(all_field_scores)

    lines = ["# CBAM Agent Loop Evaluation", "", f"Records evaluated: {len(results)}", ""]
    lines.append("## Status breakdown")
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    lines.append("")
    lines.append("## Iteration distribution")
    for iterations, count in sorted(iteration_counts.items()):
        lines.append(f"- {iterations} iteration(s): {count} record(s)")
    lines.append("")
    lines.append("## Per-field accuracy")
    for field_name, stats in sorted(aggregated.items()):
        lines.append(
            f"- {field_name}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.0%})"
        )
    if errors:
        lines.append("")
        lines.append("## Errors")
        for record_id, error in errors:
            lines.append(f"- {record_id}: {error}")

    return "\n".join(lines)
