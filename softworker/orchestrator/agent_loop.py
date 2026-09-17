"""The agentic tool-use loop.

The model decides which tool to call, in what order, every turn - including
calling the same tool twice, calling tools in an order nobody anticipated,
or deciding it's done. This file contains no ordering logic: it never
branches on a tool's name to decide what should happen next. The only
name-based branch here is detecting flag_for_human_review, which is a loop
*termination* signal the model itself raised, not a workflow step.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class AgentLoopResult:
    status: str  # "completed" | "escalated" | "exhausted"
    final_message: Optional[str]
    messages: List[dict] = field(default_factory=list)
    iterations: int = 0
    # Observability only, per the project's ReAct-style prompting (main.py's
    # SYSTEM_PROMPT asks the model to state its reasoning in its own message
    # content before calling a tool) - nothing here enforces or parses that
    # reasoning, it is only counted, so a turn that skips it is never
    # rejected or altered. tool_call_turns counts genuine model turns that
    # made at least one tool call; reasoning_turns is the subset of those
    # where the model's own content was non-empty. The iteration-cap
    # fallback call never went through the model, so it is excluded from
    # both counts.
    tool_call_turns: int = 0
    reasoning_turns: int = 0


@dataclass
class _ToolCall:
    id: str
    name: str
    args: dict


def _tool_call_message(tool_calls):
    return [
        {
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": json.dumps(call.args)},
        }
        for call in tool_calls
    ]


def _execute_and_record(execute_tool, call, messages):
    try:
        result = execute_tool(call.name, call.args)
    except Exception as exc:  # fed back to the model, never swallowed silently
        result = {"error": str(exc)}

    messages.append(
        {
            "role": "tool",
            "tool_call_id": call.id,
            "name": call.name,
            "content": json.dumps(result),
        }
    )
    return result


def run_agent_loop(
    messages: List[dict],
    llm_client: Any,
    tool_schemas: List[dict],
    execute_tool: Callable[[str, dict], dict],
    max_iterations: int = 10,
) -> AgentLoopResult:
    messages = list(messages)
    tool_call_turns = 0
    reasoning_turns = 0

    for i in range(max_iterations):
        response = llm_client.chat(messages=messages, tools=tool_schemas)

        if not response.tool_calls:
            return AgentLoopResult(
                status="completed",
                final_message=response.content,
                messages=messages,
                iterations=i + 1,
                tool_call_turns=tool_call_turns,
                reasoning_turns=reasoning_turns,
            )

        tool_call_turns += 1
        # A "thinking" model (e.g. qwen3:8b) may put its reasoning in a
        # separate response.reasoning field rather than response.content -
        # see llm_client.py's LLMResponse.reasoning. Either counts.
        stated_reasoning = (response.content and response.content.strip()) or (
            getattr(response, "reasoning", None) and response.reasoning.strip()
        )
        if stated_reasoning:
            reasoning_turns += 1

        messages.append(
            {
                "role": "assistant",
                "content": response.content,
                "tool_calls": _tool_call_message(response.tool_calls),
            }
        )

        for call in response.tool_calls:
            result = _execute_and_record(execute_tool, call, messages)

            if call.name == "flag_for_human_review":
                return AgentLoopResult(
                    status="escalated",
                    final_message=result.get("reason"),
                    messages=messages,
                    iterations=i + 1,
                    tool_call_turns=tool_call_turns,
                    reasoning_turns=reasoning_turns,
                )

    # Iteration cap reached without the model converging - hard fallback to
    # human review, per the non-negotiable design constraint (small local
    # models don't always converge cleanly on tool-calling).
    fallback_call = _ToolCall(
        id="fallback",
        name="flag_for_human_review",
        args={"reason": f"iteration cap ({max_iterations}) reached without convergence"},
    )
    fallback_result = _execute_and_record(execute_tool, fallback_call, messages)
    return AgentLoopResult(
        status="exhausted",
        final_message=fallback_result.get("reason"),
        messages=messages,
        iterations=max_iterations,
        tool_call_turns=tool_call_turns,
        reasoning_turns=reasoning_turns,
    )
