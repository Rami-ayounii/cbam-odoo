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


def test_run_evaluation_on_record_gives_the_model_a_document_id_to_extract_with():
    # Regression test for a real bug (docs/PROGRESS.md's audit follow-up
    # section): this harness used to dump the raw document text directly
    # into the user message instead of requiring extract_field, even though
    # SYSTEM_PROMPT instructs the model to use extract_field - and never
    # supplied any document_id anywhere, so a real model could never
    # construct a valid extract_field call. Now the harness must mirror
    # main.py's real "known context" shape and give the model a document_id
    # to use, and must NOT leak the raw document text directly into the
    # prompt (that would let a model "cheat" by reading it in-context
    # instead of genuinely exercising extract_field, unlike real production).
    records = load_synthetic_records(DATA_DIR, limit=1)
    record = records[0]

    captured = {}

    class CapturingLLMClient:
        def chat(self, messages, tools):
            captured["messages"] = messages
            return FakeLLMResponse(content="done")

    from datetime import date

    run_evaluation_on_record(
        record, CapturingLLMClient(), tool_schemas=[], declaration_date=date(2026, 1, 1)
    )

    user_message = captured["messages"][1]["content"]
    assert "document_id" in user_message
    assert "source_document_ids" in user_message
    assert record["document_text"] not in user_message


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


def test_run_evaluation_on_record_captures_observability_counters():
    # Regression test for the punch list's "Add #2" item (docs/PROGRESS.md,
    # "Session synthesis + next-session punch list"): agent_loop.py has
    # tracked tool_call_turns/reasoning_turns since the "Observability"
    # section, but this harness discarded them - so the eval report could
    # never show whether the ReAct-style reasoning prompt (the
    # "Anti-hallucination gate" section) actually gets used by a real model.
    records = load_synthetic_records(DATA_DIR, limit=1)
    record = records[0]
    gt = record["ground_truth"]

    llm_client = ScriptedLLMClient(
        [
            FakeLLMResponse(
                content="Checking the document first.",
                tool_calls=[
                    FakeToolCall(
                        "c1",
                        "calculate_emissions",
                        {"quantity_tonnes": gt["quantity_tonnes"], "direct_ef": 1.9},
                    )
                ],
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

    assert result.tool_call_turns == 1
    assert result.reasoning_turns == 1


def test_build_report_markdown_includes_observability_summary():
    results = [
        EvaluationResult(
            record_id="A", status="completed", iterations=2,
            field_scores={"quantity_tonnes": True},
            tool_call_turns=2, reasoning_turns=2,
        ),
        EvaluationResult(
            record_id="B", status="escalated", iterations=5,
            field_scores={"quantity_tonnes": False},
            tool_call_turns=4, reasoning_turns=0,
        ),
    ]

    report = build_report_markdown(results)

    assert "## Observability" in report
    assert "reasoning turns: 2/6" in report
