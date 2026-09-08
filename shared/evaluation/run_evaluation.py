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

    # Mirrors main.py's real production prompt shape exactly (declaration_id/
    # declaration_line_id + a "known context" JSON block + document_id under
    # source_document_ids), instead of the raw document text dumped directly
    # into the user message this harness used to build. That divergence was
    # a real bug: SYSTEM_PROMPT explicitly instructs the model to retrieve
    # document content via extract_field, but extract_field requires a
    # document_id and this harness never supplied one anywhere - so real
    # runs against this harness were never actually exercising extract_field
    # successfully (a live production trace showed the same failure mode:
    # see docs/PROGRESS.md's audit follow-up section). good_id/
    # installation_id are arbitrary placeholders (not real Odoo ids, not
    # ground truth) - FixtureOdooClient doesn't validate them and
    # scoring.py doesn't score them.
    #
    # good_sector/installation_country/production_route/quantity_tonnes/
    # data_source are all genuinely pre-known in real production (fixed
    # properties of the good/installation records, or set on the line at
    # creation time, per get_declaration_line_context - never extracted
    # from a document there either) and this dict is passed as
    # ToolDispatcher's known_context, which now injects them directly into
    # lookup_default_value/write_declaration_line calls rather than relying
    # on the model to correctly re-supply them (see tools.py's
    # _KNOWN_CONTEXT_INJECTIONS and shared/tool_schemas/*.json, which no
    # longer even expose these as model-fillable arguments - a live trace,
    # docs/PROGRESS.md's field-accuracy investigation, showed llama3.1:8b
    # reliably dropping at least one of several required fields on almost
    # every multi-argument tool call). Consequence worth being explicit
    # about: quantity_tonnes/data_source are now always correctly injected
    # from ground truth here, same as real production would inject them
    # from the already-set line record - so their SCORED_FIELDS accuracy is
    # now a trivial pass-through, not a real extraction test, matching the
    # fact that production doesn't ask the model to extract them either.
    # The genuinely-tested fields are direct_emissions_actual/
    # indirect_emissions_actual/carbon_price_paid_origin/
    # precursor_emissions/emission_factor_id.
    line_context = {
        "declaration_id": declaration_id,
        "good_id": 1,
        "installation_id": 1,
        "good_sector": record["ground_truth"].get("sector"),
        "installation_country": record["ground_truth"].get("installation_country"),
        "production_route": record["ground_truth"].get("production_route"),
        "quantity_tonnes": record["ground_truth"].get("quantity_tonnes"),
        "data_source": record["ground_truth"].get("data_source"),
        "source_document_ids": [
            {"document_id": "1", "filename": f"{record['record_id']}.txt"}
        ],
    }
    dispatcher = ToolDispatcher(
        odoo_client,
        declaration_date=declaration_date,
        declaration_id=declaration_id,
        declaration_line_id=declaration_line_id,
        known_context=line_context,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Process declaration_id={declaration_id} "
                f"declaration_line_id={declaration_line_id}.\n"
                "Known context already set on this declaration line "
                "(read-only, you did not extract this yourself): "
                f"{json.dumps(line_context)}"
            ),
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
