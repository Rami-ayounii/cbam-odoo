import json

from benchmark_models import (
    AttemptResult,
    BenchmarkResult,
    attempt_tool_call,
    build_report_markdown,
)


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, name, arguments):
        self.function = _FakeFunction(name, arguments)


class _FakeMessage:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


class _FakeChoice:
    def __init__(self, message):
        self.message = message


class _FakeCompletion:
    def __init__(self, tool_calls):
        self.choices = [_FakeChoice(_FakeMessage(tool_calls))]


class _FakeCompletions:
    def __init__(self, tool_calls=None, raise_exc=None):
        self._tool_calls = tool_calls
        self._raise_exc = raise_exc

    def create(self, model, messages, tools):
        if self._raise_exc:
            raise self._raise_exc
        return _FakeCompletion(self._tool_calls)


class _FakeChatNamespace:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, tool_calls=None, raise_exc=None):
        self.chat = _FakeChatNamespace(_FakeCompletions(tool_calls, raise_exc))


def test_attempt_tool_call_valid_when_args_pass_validation():
    tool_calls = [_FakeToolCall("flag_for_human_review", json.dumps({"reason": "test"}))]
    client = _FakeClient(tool_calls=tool_calls)

    result = attempt_tool_call(client, "test-model", messages=[], tool_schemas=[])

    assert result.valid is True
    assert result.tool_name == "flag_for_human_review"


def test_attempt_tool_call_invalid_on_unknown_tool_name():
    tool_calls = [_FakeToolCall("not_a_real_tool", json.dumps({}))]
    client = _FakeClient(tool_calls=tool_calls)

    result = attempt_tool_call(client, "test-model", messages=[], tool_schemas=[])

    assert result.valid is False
    assert "unknown tool" in result.error.lower()


def test_attempt_tool_call_invalid_on_bad_arguments():
    tool_calls = [_FakeToolCall("flag_for_human_review", json.dumps({}))]  # missing "reason"
    client = _FakeClient(tool_calls=tool_calls)

    result = attempt_tool_call(client, "test-model", messages=[], tool_schemas=[])

    assert result.valid is False


def test_attempt_tool_call_invalid_on_malformed_json():
    tool_calls = [_FakeToolCall("flag_for_human_review", "{not json")]
    client = _FakeClient(tool_calls=tool_calls)

    result = attempt_tool_call(client, "test-model", messages=[], tool_schemas=[])

    assert result.valid is False


def test_attempt_tool_call_invalid_when_no_tool_call_made():
    client = _FakeClient(tool_calls=[])

    result = attempt_tool_call(client, "test-model", messages=[], tool_schemas=[])

    assert result.valid is False
    assert "expected exactly 1" in result.error.lower()


def test_attempt_tool_call_invalid_on_api_error():
    client = _FakeClient(raise_exc=RuntimeError("connection refused"))

    result = attempt_tool_call(client, "test-model", messages=[], tool_schemas=[])

    assert result.valid is False
    assert "connection refused" in result.error


def test_build_report_markdown_names_the_highest_valid_rate_as_winner():
    results = [
        BenchmarkResult(model="model-a", attempts=10, valid_count=3, errors=["x"], latencies_s=[1.0]),
        BenchmarkResult(model="model-b", attempts=10, valid_count=9, errors=[], latencies_s=[2.0]),
    ]

    report = build_report_markdown(results)

    assert "model-b" in report
    assert "Winner: model-b" in report
