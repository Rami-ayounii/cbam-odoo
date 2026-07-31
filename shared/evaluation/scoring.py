"""Scoring logic for M9 evaluation: compares a written declaration line
against the synthetic dataset's ground truth. Kept separate from the
harness that actually drives the agent loop so this can be tested (and
trusted) without needing a live LLM or Odoo instance.
"""

from typing import Dict, List

SCORED_FIELDS = [
    "quantity_tonnes",
    "data_source",
    "direct_emissions_actual",
    "indirect_emissions_actual",
    "carbon_price_paid_origin",
    "precursor_emissions",
]

_FLOAT_TOLERANCE = 1e-6


def _values_match(ground_truth_value, written_value) -> bool:
    if isinstance(ground_truth_value, float) or isinstance(written_value, float):
        if ground_truth_value is None or written_value is None:
            return False
        # written_value normally reaches here already coerced to float by
        # tool_args.py's Pydantic validation (the real agent-loop path), but
        # score_record is a standalone, independently-tested function (see
        # module docstring) that may be called directly with raw dict data -
        # e.g. a numeric string. float(...) makes that coercion explicit
        # instead of crashing with a bare TypeError on `float - str`, and a
        # genuinely non-numeric value (a coercion failure) is correctly
        # scored as a mismatch rather than propagating an exception.
        try:
            return abs(float(ground_truth_value) - float(written_value)) < _FLOAT_TOLERANCE
        except (TypeError, ValueError):
            return False
    return ground_truth_value == written_value


def score_record(ground_truth: dict, written: dict) -> Dict[str, bool]:
    """One bool per field that has a non-null ground-truth value. Fields
    that are null in ground truth (e.g. direct_emissions_actual for a
    'default'-sourced record) are skipped, not scored - there is nothing to
    verify extraction against."""
    scores = {}
    for field_name in SCORED_FIELDS:
        if field_name not in ground_truth or ground_truth[field_name] is None:
            continue
        scores[field_name] = _values_match(
            ground_truth[field_name], written.get(field_name)
        )
    return scores


def aggregate_field_scores(per_record_scores: List[Dict[str, bool]]) -> Dict[str, dict]:
    totals: Dict[str, dict] = {}
    for record_scores in per_record_scores:
        for field_name, is_correct in record_scores.items():
            bucket = totals.setdefault(field_name, {"correct": 0, "total": 0})
            bucket["total"] += 1
            if is_correct:
                bucket["correct"] += 1

    for bucket in totals.values():
        bucket["accuracy"] = bucket["correct"] / bucket["total"]

    return totals
