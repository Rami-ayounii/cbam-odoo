# CBAM Agent Loop Evaluation — qwen3:8b (new default), full 20 records, source_quote gate + observability live for the first time

Model: `qwen3:8b` (the current default per "Default model switched to qwen3:8b"),
real live Ollama via the nginx gate (local-dev stack), real
`FixtureOdooClient` harness. This is the run the punch list's "Add #4"
item asked for: `qwen3:8b` + the `source_quote` anti-hallucination gate +
the `tool_call_turns`/`reasoning_turns` observability counters, all
exercised together against a live model for the first time.

## Result: full 20-record status/field accuracy

| | completed | escalated | exhausted |
|---|---|---|---|
| 20 records | 16 | 0 | 4 |

| field | accuracy |
|---|---|
| quantity_tonnes | 7/20 (35%) |
| data_source | 7/20 (35%) |
| carbon_price_paid_origin | 5/20 (25%) |
| precursor_emissions | 7/20 (35%) |
| direct_emissions_actual | 1/14 (7%) |
| indirect_emissions_actual | 1/14 (7%) |

**On the first 10 records** (the same `SYNTH-0000`-`SYNTH-0009` subset as
`docs/evaluation-qwen3-8b-2026-09-09.md`), this is statistically consistent
with that earlier measurement (30%/30%/30%/20%/12%/12%), not a regression -
7/10 completed here vs. 8/10 there, 3/10 correct on `quantity_tonnes`/
`data_source` both times. An initial read of this run looked like a sharp
regression; tracing individual records (below) showed the real story is
more specific than "worse," and the completion-rate difference is smaller
than it first appears.

**Comparison against `qwen2.5:14b-instruct`'s full-20 run from earlier this
session (`docs/evaluation-qwen25-14b-full20-2026-09-17.md`):**

| field | qwen3:8b (full 20) | qwen2.5:14b-instruct (full 20) |
|---|---|---|
| quantity_tonnes | 35% | **70%** |
| data_source | 35% | **70%** |
| carbon_price_paid_origin | 25% | **60%** |
| precursor_emissions | 35% | **70%** |
| direct_emissions_actual | 7% | **57%** |
| indirect_emissions_actual | 7% | **57%** |

`qwen2.5:14b-instruct` remains, by a wide margin, the strongest model this
project has measured against this harness.

## A real, verified bug found and fixed: reasoning_turns was silently broken for thinking models

The very first pass through this run reported **`reasoning_turns: 0` across
all 74 tool-call turns** - i.e. the ReAct-style "state your reasoning before
acting" prompt (from the "Anti-hallucination gate" section) appeared to be
completely ignored by `qwen3:8b`. That would have been a real, concerning
finding, so it was checked rather than reported at face value.

**Root cause, confirmed with a raw API call:** `qwen3:8b` is a hybrid
"thinking" model. Ollama's OpenAI-compatible endpoint returns its
chain-of-thought in a **separate `message.reasoning` field**, not
`message.content` - confirmed with a direct `curl` to
`/v1/chat/completions` and independently confirmed that the `openai` Python
SDK exposes it (`getattr(message, "reasoning", None)` / `message.model_extra`).
`llm_client.py`'s `chat()` only ever read `message.content`, so
`agent_loop.py`'s `reasoning_turns` counter - which checks
`response.content` - undercounted to zero for `qwen3:8b` even though the
model was reasoning on effectively every turn.

**Fix (`softworker/orchestrator/llm_client.py`,
`softworker/orchestrator/agent_loop.py`):** `LLMResponse` gained a
`reasoning` field, populated from `getattr(message, "reasoning", None)`;
`agent_loop.py`'s reasoning-turn check now counts a turn as reasoning if
either `content` or `reasoning` is non-empty. 3 new regression tests
(2 in `test_llm_client.py`, 1 in `test_agent_loop.py`, plus 2 more added
earlier this session in `shared/evaluation/test_run_evaluation.py` for the
counters' report-wiring - see "Session synthesis" punch list Add #2). Full
suite: 154 passed (149 base + 5 new across both fixes; no existing test's
expectations changed).

**Live-verified after the fix:** re-traced 4 records
(`SYNTH-0001`/`0003`/`0008`/`0012`) - `reasoning_turns` now equals
`tool_call_turns` exactly in all 4 (9/9, 1/1, 6/6, 3/3). The model reasons
on essentially every turn; the prompt instruction was working the whole
time, the harness just couldn't see it. This means the "reasoning turns:
0/74" figure the raw run produced is known-wrong and superseded by this
finding - a corrected full-run count was not re-collected (would cost
another ~20-record live run for a metric that doesn't affect field
accuracy or status), but the direction and near-100% rate is established
by the 4-record spot-check above.

## Live-traced failure modes (why so many "completed" records score 0/6)

Traced several "completed, 0/6" records message-by-message rather than
trusting the aggregate:

- **The pre-existing "silent stop after successful extraction" pattern
  persists.** `SYNTH-0003`: the model calls `extract_field` twice
  (both succeed, real document text returned), then its very next turn has
  no tool calls and empty content/reasoning - the loop ends `completed`
  with nothing written. This is the same failure category M6/M9 sessions
  targeted with the "not finished until write_declaration_line" prompt
  strengthening; it still happens some of the time with `qwen3:8b`.
- **A new confusion, possibly prompt-induced:** one trace
  (`SYNTH-0008`, first pass before the reasoning-field fix) showed the
  model attempting `extract_field(field_name="source_quote")` - an invalid
  enum value (`source_quote` is a `write_declaration_line` argument, not
  an extractable field) - getting a validation error, then repeatedly
  re-calling `extract_field` for fields it had *already* successfully
  extracted several turns earlier, wasting 5+ iterations before finally
  calling `write_declaration_line` correctly (with a valid, grounded
  `source_quote`) right at the iteration cap. The write succeeded (4/6
  fields correct) but the record scored `exhausted`, not `completed`,
  because the model kept going past the cap. This looks like the
  `source_quote` gate's prompt wording may be inviting the model to treat
  `source_quote` as something to *fetch* rather than something to
  *construct* from what it already extracted - a `SYSTEM_PROMPT` wording
  issue worth a future look, not confirmed as the sole cause from one
  trace.

Neither of these is a regression introduced by today's changes specifically
- both are consistent with this project's long-documented small-model
tool-calling ceiling (M4: 50% valid-call rate, the best of 4 models tested
before `qwen2.5:14b-instruct`). The `source_quote`-as-extractable-field
confusion is the one genuinely new observation from this run.

## Conclusion

**The punch list's "Add #4" is now done:** `qwen3:8b` + the `source_quote`
gate + the observability counters have all been exercised together against
a live model, for the first time, at full 20-record scale. Two real
findings came out of it: a genuine bug (reasoning silently uncounted for
thinking models, now fixed and verified) and a real, if inconclusive,
observation (`source_quote` sometimes gets mistaken for something
`extract_field` should supply). Field accuracy itself did not move in a
statistically meaningful way from the last `qwen3:8b` measurement.

**This further sharpens the case for `qwen2.5:14b-instruct` over
`qwen3:8b` as this project's default model** - same harness, same day,
same fixes, and `qwen2.5:14b-instruct` leads on every field by a wide
margin (57-70% vs. 7-35%). This is a decision for the human partner
(VRAM-cost tradeoff already noted in the earlier section), not changed
unilaterally here.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 154
passed (149 base + 5 new regression tests across this session's two fixes;
no existing test's expectations changed).
