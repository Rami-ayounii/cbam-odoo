from agent_loop import run_agent_loop


class FakeToolCall:
    def __init__(self, id, name, args):
        self.id = id
        self.name = name
        self.args = args


class FakeLLMResponse:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeLLMClient:
    """Returns pre-programmed responses in order - the model's ordering
    decisions are baked into the fixture, never decided by the loop."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def chat(self, messages, tools):
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._responses.pop(0)


def _recording_execute_tool(log, results=None):
    results = results or {}

    def execute_tool(name, args):
        log.append((name, args))
        if name in results and isinstance(results[name], Exception):
            raise results[name]
        return results.get(name, {"ok": True})

    return execute_tool


def test_loop_stops_when_model_returns_no_tool_calls():
    llm_client = FakeLLMClient([FakeLLMResponse(content="all done")])
    log = []

    result = run_agent_loop(
        messages=[{"role": "system", "content": "go"}],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool(log),
        max_iterations=10,
    )

    assert result.status == "completed"
    assert result.final_message == "all done"
    assert result.iterations == 1
    assert log == []


def test_loop_executes_a_tool_call_then_stops_once_model_is_done():
    llm_client = FakeLLMClient(
        [
            FakeLLMResponse(
                tool_calls=[FakeToolCall("call-1", "lookup_default_value", {"sector": "steel"})]
            ),
            FakeLLMResponse(content="final answer"),
        ]
    )
    log = []

    result = run_agent_loop(
        messages=[{"role": "system", "content": "go"}],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool(log),
        max_iterations=10,
    )

    assert result.status == "completed"
    assert result.iterations == 2
    assert log == [("lookup_default_value", {"sector": "steel"})]


def test_loop_runs_tools_in_whatever_order_the_model_chose_this_turn():
    # The model decided to call calculate_emissions BEFORE extract_field on
    # its first turn - an order nobody would hardcode. The loop must not
    # reorder or second-guess this.
    llm_client = FakeLLMClient(
        [
            FakeLLMResponse(
                tool_calls=[
                    FakeToolCall("c1", "calculate_emissions", {"x": 1}),
                    FakeToolCall("c2", "extract_field", {"y": 2}),
                ]
            ),
            FakeLLMResponse(content="done"),
        ]
    )
    log = []

    run_agent_loop(
        messages=[],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool(log),
        max_iterations=10,
    )

    assert log == [("calculate_emissions", {"x": 1}), ("extract_field", {"y": 2})]


def test_loop_escalates_immediately_on_flag_for_human_review_without_running_later_calls():
    llm_client = FakeLLMClient(
        [
            FakeLLMResponse(
                tool_calls=[
                    FakeToolCall("c1", "flag_for_human_review", {"reason": "conflicting data"}),
                    FakeToolCall("c2", "write_declaration_line", {"should": "never run"}),
                ]
            )
        ]
    )
    log = []

    result = run_agent_loop(
        messages=[],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool(
            log, results={"flag_for_human_review": {"acknowledged": True, "reason": "conflicting data"}}
        ),
        max_iterations=10,
    )

    assert result.status == "escalated"
    assert result.final_message == "conflicting data"
    assert log == [("flag_for_human_review", {"reason": "conflicting data"})]


def test_loop_falls_back_to_human_review_when_iteration_cap_reached():
    # The model never converges - every turn it calls the same tool again.
    responses = [
        FakeLLMResponse(tool_calls=[FakeToolCall(f"c{i}", "extract_field", {"i": i})])
        for i in range(3)
    ]
    llm_client = FakeLLMClient(responses)
    log = []

    result = run_agent_loop(
        messages=[],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool(
            log,
            results={
                "flag_for_human_review": {
                    "acknowledged": True,
                    "reason": "iteration cap (3) reached without convergence",
                }
            },
        ),
        max_iterations=3,
    )

    assert result.status == "exhausted"
    assert "iteration cap" in result.final_message
    # 3 extract_field calls (one per turn) plus the automatic escalation call
    assert log[-1][0] == "flag_for_human_review"
    assert len([c for c in log if c[0] == "extract_field"]) == 3


def test_loop_feeds_tool_errors_back_to_the_model_without_crashing():
    llm_client = FakeLLMClient(
        [
            FakeLLMResponse(
                tool_calls=[FakeToolCall("c1", "lookup_default_value", {"sector": "steel"})]
            ),
            FakeLLMResponse(content="recovered"),
        ]
    )
    log = []

    result = run_agent_loop(
        messages=[],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool(
            log, results={"lookup_default_value": ValueError("no factor on file")}
        ),
        max_iterations=10,
    )

    assert result.status == "completed"
    assert result.iterations == 2
    # the error must have been fed back into the conversation, not swallowed
    tool_messages = [m for m in result.messages if m.get("role") == "tool"]
    assert any("no factor on file" in m["content"] for m in tool_messages)


def test_result_counts_tool_call_turns_and_which_ones_stated_reasoning_first():
    # Observability only: the prompt asks the model to state its reasoning
    # (a ReAct-style Thought) in its own message content before calling a
    # tool, but nothing in the loop enforces or parses that - this counts
    # how often it actually happened, without rejecting the turns that
    # skipped it. Turn 1 reasons before acting, turn 2 doesn't, turn 3 has
    # no tool calls at all (the model is done).
    llm_client = FakeLLMClient(
        [
            FakeLLMResponse(
                content="Quantity is missing, I should extract it first.",
                tool_calls=[FakeToolCall("c1", "extract_field", {"field_name": "quantity_tonnes"})],
            ),
            FakeLLMResponse(
                content=None,
                tool_calls=[FakeToolCall("c2", "lookup_default_value", {"sector": "steel"})],
            ),
            FakeLLMResponse(content="done"),
        ]
    )

    result = run_agent_loop(
        messages=[],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool([]),
        max_iterations=10,
    )

    assert result.status == "completed"
    assert result.iterations == 3
    assert result.tool_call_turns == 2
    assert result.reasoning_turns == 1


def test_reasoning_turns_counted_on_the_escalated_path_too():
    llm_client = FakeLLMClient(
        [
            FakeLLMResponse(
                content="Data is inconsistent, escalating.",
                tool_calls=[FakeToolCall("c1", "flag_for_human_review", {"reason": "bad data"})],
            )
        ]
    )

    result = run_agent_loop(
        messages=[],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool(
            [], results={"flag_for_human_review": {"acknowledged": True, "reason": "bad data"}}
        ),
        max_iterations=10,
    )

    assert result.status == "escalated"
    assert result.tool_call_turns == 1
    assert result.reasoning_turns == 1


def test_the_automatic_iteration_cap_escalation_is_not_counted_as_a_reasoning_turn():
    # The fallback flag_for_human_review call the loop injects when the cap
    # is reached never went through the model - it must not be counted as
    # a (reasoning-less) model turn, which would understate the model's
    # own real reasoning rate.
    responses = [
        FakeLLMResponse(
            content=None,
            tool_calls=[FakeToolCall(f"c{i}", "extract_field", {"i": i})],
        )
        for i in range(3)
    ]
    llm_client = FakeLLMClient(responses)

    result = run_agent_loop(
        messages=[],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool(
            [],
            results={
                "flag_for_human_review": {
                    "acknowledged": True,
                    "reason": "iteration cap (3) reached without convergence",
                }
            },
        ),
        max_iterations=3,
    )

    assert result.status == "exhausted"
    assert result.tool_call_turns == 3
    assert result.reasoning_turns == 0


def test_assistant_tool_call_message_is_reconstructed_for_the_next_turn():
    llm_client = FakeLLMClient(
        [
            FakeLLMResponse(
                tool_calls=[FakeToolCall("call-abc", "extract_field", {"field_name": "cn_code"})]
            ),
            FakeLLMResponse(content="done"),
        ]
    )

    result = run_agent_loop(
        messages=[{"role": "system", "content": "go"}],
        llm_client=llm_client,
        tool_schemas=[],
        execute_tool=_recording_execute_tool([]),
        max_iterations=10,
    )

    assistant_messages = [m for m in result.messages if m.get("role") == "assistant"]
    assert len(assistant_messages) == 1
    assert assistant_messages[0]["tool_calls"][0]["id"] == "call-abc"
    assert assistant_messages[0]["tool_calls"][0]["function"]["name"] == "extract_field"

    tool_messages = [m for m in result.messages if m.get("role") == "tool"]
    assert tool_messages[0]["tool_call_id"] == "call-abc"
