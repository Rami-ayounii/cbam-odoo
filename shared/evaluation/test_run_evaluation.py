from pathlib import Path

from run_evaluation import (
    build_report_markdown,
    load_synthetic_records,
    run_evaluation_on_record,
    EvaluationResult,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "synthetic_data" / "output"


class FakeToolCall:
    def __init__(self, id, name, args):
        self.id = id
        self.name = name
        self.args = args


class FakeLLMResponse:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class ScriptedLLMClient:
    def __init__(self, responses):
        self._responses = list(responses)

    def chat(self, messages, tools):
        return self._responses.pop(0)


def test_load_synthetic_records_reads_real_m1_output():
    records = load_synthetic_records(DATA_DIR, limit=3)

    assert len(records) == 3
    for record in records:
        assert "record_id" in record
        assert "document_text" in record
        assert "ground_truth" in record
        assert "quantity_tonnes" in record["ground_truth"]


def test_run_evaluation_on_record_scores_a_correct_completion():
    records = load_synthetic_records(DATA_DIR, limit=1)
    record = records[0]
    gt = record["ground_truth"]

    llm_client = ScriptedLLMClient(
        [
            FakeLLMResponse(
                tool_calls=[
                    FakeToolCall(
                        "c1",
                        "calculate_emissions",
                        {"quantity_tonnes": gt["quantity_tonnes"], "direct_ef": 1.9},
                    )
                ]
            ),
            FakeLLMResponse(
                tool_calls=[
                    FakeToolCall(
                        "c2",
                        "write_declaration_line",
                        {
                            "declaration_id": 1,
                            "good_id": 1,
                            "installation_id": 1,
                            "quantity_tonnes": gt["quantity_tonnes"],
                            "data_source": gt["data_source"],
                            "emission_factor_id": 1,
                            "carbon_price_paid_origin": gt["carbon_price_paid_origin"],
                            "precursor_emissions": gt["precursor_emissions"],
                        },
                    )
                ]
            ),
            FakeLLMResponse(content="done"),
        ]
    )

    from datetime import date

    result = run_evaluation_on_record(
        record,
        llm_client,
        tool_schemas=[],
        declaration_date=date(2026, 1, 1),
        max_iterations=9,
    )

    assert result.status == "completed"
    assert result.iterations == 3
    assert result.field_scores["quantity_tonnes"] is True
    assert result.field_scores["data_source"] is True


def test_run_evaluation_on_record_captures_errors_without_raising():
    records = load_synthetic_records(DATA_DIR, limit=1)
    record = records[0]

    class BrokenLLMClient:
        def chat(self, messages, tools):
            raise RuntimeError("connection refused")

    from datetime import date

    result = run_evaluation_on_record(
        record, BrokenLLMClient(), tool_schemas=[], declaration_date=date(2026, 1, 1)
    )

    assert result.status == "error"
    assert "connection refused" in result.error


def test_build_report_markdown_includes_status_and_field_accuracy():
    results = [
        EvaluationResult(
            record_id="A", status="completed", iterations=2,
            field_scores={"quantity_tonnes": True},
        ),
        EvaluationResult(
            record_id="B", status="escalated", iterations=5,
            field_scores={"quantity_tonnes": False},
        ),
    ]

    report = build_report_markdown(results)

    assert "completed: 1" in report
    assert "escalated: 1" in report
    assert "quantity_tonnes: 1/2" in report
