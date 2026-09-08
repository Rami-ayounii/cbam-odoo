from types import SimpleNamespace

import httpx
import pytest
from openai import AuthenticationError, RateLimitError

from llm_client import LLMClient


def _make_error(error_cls, status_code):
    request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return error_cls("boom", response=response, body=None)


class FakeCompletions:
    def __init__(self, completion):
        self._completion = completion
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        return self._completion


class FakeChat:
    def __init__(self, completion):
        self.completions = FakeCompletions(completion)


class FakeOpenAIClient:
    def __init__(self, completion):
        self.chat = FakeChat(completion)


class _CapturingOpenAIConstructor:
    """Stands in for openai.OpenAI itself (not a client instance) so the
    constructor kwargs LLMClient passes can be inspected - every other
    fake in this file replaces the client *after* construction via
    `client=`, which never exercises this code path at all."""

    last_kwargs = None

    def __init__(self, **kwargs):
        _CapturingOpenAIConstructor.last_kwargs = kwargs


def _make_completion(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_constructs_openai_client_with_explicit_x_api_key_header(monkeypatch):
    monkeypatch.setattr("llm_client.OpenAI", _CapturingOpenAIConstructor)

    LLMClient(model="llama3.1:8b", base_url="http://ollama:8443/v1", api_key="secret-key")

    kwargs = _CapturingOpenAIConstructor.last_kwargs
    assert kwargs["api_key"] == "secret-key"
    assert kwargs["default_headers"] == {"X-Api-Key": "secret-key"}


def test_omits_default_headers_when_no_api_key_given(monkeypatch):
    monkeypatch.setattr("llm_client.OpenAI", _CapturingOpenAIConstructor)

    LLMClient(model="llama3.1:8b", base_url="http://ollama:8443/v1", api_key=None)

    kwargs = _CapturingOpenAIConstructor.last_kwargs
    assert kwargs["default_headers"] is None


def test_chat_returns_content_when_no_tool_calls():
    completion = _make_completion(content="hello")
    fake_client = FakeOpenAIClient(completion)
    llm_client = LLMClient(model="test-model", client=fake_client)

    response = llm_client.chat(messages=[{"role": "user", "content": "hi"}], tools=[])

    assert response.content == "hello"
    assert response.tool_calls == []


def test_chat_parses_tool_calls():
    raw_tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="lookup_default_value", arguments='{"sector": "steel"}'),
    )
    completion = _make_completion(content=None, tool_calls=[raw_tool_call])
    fake_client = FakeOpenAIClient(completion)
    llm_client = LLMClient(model="test-model", client=fake_client)

    response = llm_client.chat(messages=[], tools=[])

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].id == "call-1"
    assert response.tool_calls[0].name == "lookup_default_value"
    assert response.tool_calls[0].args == {"sector": "steel"}


def test_chat_passes_model_messages_and_tools_through():
    completion = _make_completion(content="ok")
    fake_client = FakeOpenAIClient(completion)
    llm_client = LLMClient(model="qwen2.5:7b-instruct", client=fake_client)

    messages = [{"role": "system", "content": "go"}]
    tools = [{"type": "function", "function": {"name": "x"}}]
    llm_client.chat(messages=messages, tools=tools)

    call_kwargs = fake_client.chat.completions.last_call_kwargs
    assert call_kwargs["model"] == "qwen2.5:7b-instruct"
    assert call_kwargs["messages"] == messages
    assert call_kwargs["tools"] == tools


def test_chat_passes_a_low_default_temperature():
    # Regression test for a real live-traced bug (docs/PROGRESS.md's "Real
    # production-path verification" follow-up): Ollama's own request log
    # showed temp=1.000 (the default when nothing is set) for real jobs
    # that repeatedly narrated a tool call as text instead of using the
    # actual function-calling protocol. A low, non-zero temperature is a
    # known lever for small-model function-calling adherence.
    completion = _make_completion(content="ok")
    fake_client = FakeOpenAIClient(completion)
    llm_client = LLMClient(model="test-model", client=fake_client)

    llm_client.chat(messages=[], tools=[])

    call_kwargs = fake_client.chat.completions.last_call_kwargs
    assert 0 < call_kwargs["temperature"] <= 0.3


def test_chat_temperature_is_configurable():
    completion = _make_completion(content="ok")
    fake_client = FakeOpenAIClient(completion)
    llm_client = LLMClient(model="test-model", client=fake_client, temperature=0.0)

    llm_client.chat(messages=[], tools=[])

    assert fake_client.chat.completions.last_call_kwargs["temperature"] == 0.0


class FlakyCompletions:
    """Raises `error` on the first `fail_times` calls, then succeeds."""

    def __init__(self, error, fail_times, completion):
        self._error = error
        self._fail_times = fail_times
        self._completion = completion
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1
        if self.call_count <= self._fail_times:
            raise self._error
        return self._completion


class FlakyOpenAIClient:
    def __init__(self, completions):
        self.chat = SimpleNamespace(completions=completions)


def test_chat_retries_on_rate_limit_then_succeeds():
    completion = _make_completion(content="ok")
    error = _make_error(RateLimitError, 429)
    completions = FlakyCompletions(error, fail_times=2, completion=completion)
    fake_client = FlakyOpenAIClient(completions)
    llm_client = LLMClient(model="test-model", client=fake_client)

    response = llm_client.chat(messages=[], tools=[])

    assert response.content == "ok"
    assert completions.call_count == 3


def test_chat_does_not_crash_on_malformed_tool_call_arguments():
    # A real, expected failure mode for small local models: returning
    # non-JSON (or truncated JSON) tool-call arguments. This used to raise
    # json.JSONDecodeError straight out of chat(), uncaught by the tenacity
    # retry (not a retryable error type) and uncaught by agent_loop.py,
    # crashing the whole job. It must instead come back as a normal
    # LLMResponse the loop can hand to the dispatcher, which then rejects
    # the malformed args as a tool error fed back to the model.
    raw_tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="lookup_default_value", arguments="{not valid json"),
    )
    completion = _make_completion(content=None, tool_calls=[raw_tool_call])
    fake_client = FakeOpenAIClient(completion)
    llm_client = LLMClient(model="test-model", client=fake_client)

    response = llm_client.chat(messages=[], tools=[])

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "lookup_default_value"
    assert isinstance(response.tool_calls[0].args, dict)
    assert "_tool_call_arguments_parse_error" in response.tool_calls[0].args


def test_chat_does_not_retry_on_authentication_error():
    error = _make_error(AuthenticationError, 401)
    completions = FlakyCompletions(error, fail_times=99, completion=None)
    fake_client = FlakyOpenAIClient(completions)
    llm_client = LLMClient(model="test-model", client=fake_client)

    with pytest.raises(AuthenticationError):
        llm_client.chat(messages=[], tools=[])

    assert completions.call_count == 1
