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


def _make_completion(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


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


def test_chat_does_not_retry_on_authentication_error():
    error = _make_error(AuthenticationError, 401)
    completions = FlakyCompletions(error, fail_times=99, completion=None)
    fake_client = FlakyOpenAIClient(completions)
    llm_client = LLMClient(model="test-model", client=fake_client)

    with pytest.raises(AuthenticationError):
        llm_client.chat(messages=[], tools=[])

    assert completions.call_count == 1
