# CBAM Agent Loop Evaluation - qwen2.5:7b-instruct vs. llama3.1:8b

Model: qwen2.5:7b-instruct, real live Ollama via the nginx gate, real
`FixtureOdooClient` harness (the standard M9 harness), all of this
session's fixes in effect (known_context injection, lookup-result
carryover, temperature=0.1, the write_declaration_line prompt fix,
remembered-write-fields carryover) - the identical harness and fix set
used for `docs/evaluation-full20-2026-09-09.md`'s `llama3.1:8b` run, run
immediately after it for a same-day, same-conditions comparison.

**Why this model:** M4's original raw tool-calling benchmark
(`docs/model-benchmark.md`) scored `qwen2.5:7b-instruct` at 40% valid-call
rate, second only to `llama3.1:8b`'s 50% (the two other candidates,
`qwen3:8b` and `qwen2.5:14b-instruct`, both scored 0% in that benchmark).
Worth checking against the real, now-fixed harness rather than trusting
the raw-validity number alone.

Records evaluated: 10 (SYNTH-0000 through SYNTH-0009, first 10 in numeric
order - not hand-picked, same records `llama3.1:8b`'s full-20 run covers).

## Status breakdown
- exhausted: 10 (100%)

## Per-field accuracy
- All scored fields: 0/10 (0%), 0/6 where applicable (0%)

## Result

**10 of 10 records exhausted the full 9-iteration cap without ever
calling `write_declaration_line` or `flag_for_human_review`** - a
different and worse failure mode than `llama3.1:8b`'s mix of
completed/escalated/exhausted on the same harness. `llama3.1:8b`'s full
20-record run (same day, same fixes) reached 5/20 completed and 15-20%
field accuracy on the plumbing-reachable fields; `qwen2.5:7b-instruct`
never reached a terminal action at all in this sample.

## Conclusion

M4's raw tool-calling benchmark ranking (llama3.1:8b > qwen2.5:7b-instruct)
holds up on the real, fixed harness, and by a wider margin than the raw
40%-vs-50% numbers alone suggested - `llama3.1:8b` remains the
best-of-tested model for this project's tool schemas. `qwen3:8b` and
`qwen2.5:14b-instruct` were not re-tested against this harness (both
scored 0% in M4's raw benchmark for a reason - emitting multiple tool
calls per turn - that `agent_loop.py` may handle correctly even though
M4's narrower benchmark methodology didn't; this remains an open,
unexplored possibility, not ruled out, just not pursued further this
session per the human partner's choice to conclude the comparison here).
