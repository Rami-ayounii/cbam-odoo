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
    # Ollama's OpenAI-compatible endpoint returns a "thinking" model's
    # (e.g. qwen3:8b) chain-of-thought here, separate from content - not
    # part of the official OpenAI schema, so the openai SDK only exposes it
    # via getattr/model_extra, never a typed attribute every model has.
    reasoning: Optional[str] = None


class LLMClient:
    def __init__(
        self,
        model,
        base_url=None,
        api_key=None,
        client=None,
        max_retries=5,
        temperature=0.1,
    ):
        self._model = model
        # Low, not zero: a real live trace (docs/PROGRESS.md's "Real
        # production-path verification" follow-up) showed llama3.1:8b
        # repeatedly narrating a tool call as plain-text JSON inside
        # `content` instead of using the actual function-calling protocol -
        # Ollama's own request log for those runs showed temp=1.000 (the
        # default when nothing is set), which is known to hurt
        # structured-output/function-calling adherence in small models.
        # 0.1 favors the model actually following the tool schema over
        # creative phrasing, without being fully deterministic (0.0 can
        # make some models loop on a single bad completion instead of
        # varying their next attempt after a tool error).
        self._temperature = temperature
        # max_retries is passed straight to the openai SDK, which already
        # backs off exponentially and honors a Retry-After header on 429s -
        # the default of 2 is too low for a cloud endpoint under real load,
        # so this raises the floor rather than reimplementing that logic.
        #
        # default_headers sets X-Api-Key explicitly: the openai SDK's own
        # `api_key` param only ever produces an `Authorization: Bearer`
        # header, but the nginx gate in front of Ollama (hardworker/
        # nginx.conf.template, reused byte-for-byte - see
        # docker-compose.local-dev.yml's nginx service comment) checks
        # $http_x_api_key, not Authorization. Without this, every real
        # request through the gate 401s - this was never exercised until
        # M6's first live run (Task 6) because every earlier test used a
        # fake LLMClient/OpenAI client and never talked to the real gate.
        self._client = client or OpenAI(
            base_url=base_url,
            api_key=api_key,
            max_retries=max_retries,
            default_headers={"X-Api-Key": api_key} if api_key else None,
        )

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
            temperature=self._temperature,
        )
        message = completion.choices[0].message
        tool_calls = [
            ToolCall(
                id=call.id,
                name=call.function.name,
                args=_parse_tool_call_arguments(call.function.arguments),
            )
            for call in (message.tool_calls or [])
        ]
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            reasoning=getattr(message, "reasoning", None),
        )


def _parse_tool_call_arguments(raw_arguments) -> dict:
    """Small local models occasionally return malformed JSON (or no JSON at
    all) for a tool call's arguments - this is a real, expected failure mode
    (see agent_loop.py's docstring / projecthandoff.md section 7 on 7-8B
    models not always converging cleanly). A json.JSONDecodeError here used
    to propagate straight out of chat(), uncaught by the tenacity retry
    (which only retries transient network/server errors, not parsing
    errors) and uncaught by agent_loop.py's loop body, crashing the whole
    job instead of giving the model a chance to correct itself.

    Instead, fall back to a placeholder dict that deliberately lacks every
    tool's required fields. tools.py's Pydantic validation
    (tool_args.TOOL_ARG_MODELS) then rejects it the same way it already
    rejects any other malformed/missing tool arguments - a ValueError fed
    back into the conversation as a tool error, not a crash.
    """
    try:
        parsed = json.loads(raw_arguments)
    except (TypeError, json.JSONDecodeError) as exc:
        return {
            "_tool_call_arguments_parse_error": (
                f"model returned unparseable tool-call arguments: {exc}"
            ),
            "_raw_arguments": raw_arguments,
        }
    if not isinstance(parsed, dict):
        return {
            "_tool_call_arguments_parse_error": (
                "model returned tool-call arguments that are valid JSON but "
                f"not a JSON object (got {type(parsed).__name__})"
            ),
            "_raw_arguments": raw_arguments,
        }
    return parsed
