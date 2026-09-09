# M4 Model Tool-Calling Benchmark

Method: N attempts per model, each given one real synthetic CBAM document (shared/synthetic_data/output/) and asked to make progress on processing it. A tool call is 'valid' only if it names a real tool and its arguments pass that tool's exact production Pydantic validation (softworker/orchestrator/tool_args.py).

Notes:
- `llama3.1:8b-instruct` (named in projecthandoff.md section 10) is not a
  published Ollama library tag — only `llama3.1:8b` exists, and it is
  already the instruction-tuned chat variant (Meta did not publish a
  separate base-model tag under that name on the Ollama registry). This
  benchmark ran `llama3.1:8b` in its place; use that exact name downstream.
- `qwen2.5:14b-instruct` (9.5 GB) was NOT dropped: `ollama ps` showed it
  running 100% on GPU (RTX 5070, 12 GB VRAM) with a ~0.4s warm single-turn
  latency, well under the "impractically slow" bar, so it was benchmarked
  along with the other three as planned.
- All four models were run for real against a live local `ollama serve` at
  http://localhost:11434/v1 (OpenAI-compatible endpoint), 10 attempts each,
  same document and prompt. qwen3:8b and qwen2.5:14b-instruct scored 0% here
  specifically because they emitted 2-5 tool calls per turn instead of the
  1 this benchmark requires per attempt (see their sample errors below) -
  a real, reproducible tool-discipline difference between models, not a
  benchmark bug.
- Methodology note, corrected: this benchmark scores a tool call valid only
  when the model emits exactly one well-formed call per turn. The real
  orchestrator (`softworker/orchestrator/agent_loop.py`) actually executes
  every tool call a model emits in a turn (`for call in
  response.tool_calls: ...`) with no single-call restriction - it is more
  permissive than this benchmark on that specific point, not equivalent to
  it. So a model scored 0% here for emitting multiple calls per turn (e.g.
  qwen3:8b, qwen2.5:14b-instruct above) may still perform differently
  against the real agent loop. What this benchmark actually measures is
  single-call discipline plus argument correctness (the latter via the
  exact same production Pydantic validation, `tool_args.py`) - not raw
  production tolerance for how many calls a turn may contain.

## llama3.1:8b
- Valid tool calls: 5/10 (50%)
- Avg latency: 1.7s
- Sample errors: invalid arguments: 1 validation error for ExtractFieldArgs
field_name
  Input should be 'cn_code', 'quantity_tonnes', 'installation_name', 'installation_country', 'production_route', 'direct_emissions_actual', 'indirect_emissions_actual' or 'carbon_price_paid_origin' [type=literal_error, input_value='sector', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error; invalid arguments: 1 validation error for ExtractFieldArgs
field_name
  Input should be 'cn_code', 'quantity_tonnes', 'installation_name', 'installation_country', 'production_route', 'direct_emissions_actual', 'indirect_emissions_actual' or 'carbon_price_paid_origin' [type=literal_error, input_value='sector', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error; invalid arguments: 1 validation error for ExtractFieldArgs
field_name
  Input should be 'cn_code', 'quantity_tonnes', 'installation_name', 'installation_country', 'production_route', 'direct_emissions_actual', 'indirect_emissions_actual' or 'carbon_price_paid_origin' [type=literal_error, input_value='sector', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error (+2 more)

## qwen2.5:7b-instruct
- Valid tool calls: 4/10 (40%)
- Avg latency: 2.2s
- Sample errors: invalid arguments: 1 validation error for ExtractFieldArgs
document_id
  Input should be a valid string [type=string_type, input_value=1, input_type=int]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type; invalid arguments: 1 validation error for ExtractFieldArgs
document_id
  Input should be a valid string [type=string_type, input_value=1, input_type=int]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type; invalid arguments: 1 validation error for ExtractFieldArgs
document_id
  Input should be a valid string [type=string_type, input_value=1, input_type=int]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type (+3 more)

## qwen3:8b
- Valid tool calls: 0/10 (0%)
- Avg latency: 14.1s
- Sample errors: expected exactly 1 tool call, got 5; expected exactly 1 tool call, got 3; expected exactly 1 tool call, got 5 (+7 more)

## qwen2.5:14b-instruct
- Valid tool calls: 0/10 (0%)
- Avg latency: 5.5s
- Sample errors: expected exactly 1 tool call, got 2; expected exactly 1 tool call, got 4; expected exactly 1 tool call, got 2 (+7 more)

## Winner: llama3.1:8b
Highest valid tool-call rate (50%); ties broken by lower latency.