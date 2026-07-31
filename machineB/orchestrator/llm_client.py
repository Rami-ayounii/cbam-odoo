"""Thin wrapper around the openai client pointed at Ollama's OpenAI-compatible
/v1 endpoint. Isolates agent_loop.py from the raw SDK response shape so the
loop can be tested with a trivial fake, and so a future swap of inference
backend touches only this file.

Per the project's explicit "no agent framework" decision: plain openai
client + a ~10-line parsing layer, not LangChain/AutoGen/CrewAI.
"""

import json
from dataclasses import dataclass
from typing import List, Optional

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Errors worth retrying: transient network/server issues and rate limits.
# Deliberately excludes things like AuthenticationError or BadRequestError,
# which won't fix themselves on retry and should fail the job immediately.
_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class LLMResponse:
    content: Optional[str]
    tool_calls: List[ToolCall]


class LLMClient:
    def __init__(self, model, base_url=None, api_key=None, client=None, max_retries=5):
        self._model = model
        # max_retries is passed straight to the openai SDK, which already
        # backs off exponentially and honors a Retry-After header on 429s -
        # the default of 2 is too low for a cloud endpoint under real load,
        # so this raises the floor rather than reimplementing that logic.
        self._client = client or OpenAI(base_url=base_url, api_key=api_key, max_retries=max_retries)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        reraise=True,
    )
    def chat(self, messages, tools) -> LLMResponse:
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
        )
        message = completion.choices[0].message
        tool_calls = [
            ToolCall(
                id=call.id,
                name=call.function.name,
                args=json.loads(call.function.arguments),
            )
            for call in (message.tool_calls or [])
        ]
        return LLMResponse(content=message.content, tool_calls=tool_calls)
