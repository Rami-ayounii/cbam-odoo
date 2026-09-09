# CBAM Agent Loop Evaluation - qwen3:8b vs. llama3.1:8b, same records

Model: qwen3:8b, real live Ollama via the nginx gate, real
`FixtureOdooClient` harness, all of this session's fixes in effect
(known_context injection, lookup-result carryover, temperature=0.1, the
write_declaration_line prompt fix, remembered-write-fields carryover) -
identical harness and fix set to the `llama3.1:8b` and
`qwen2.5:7b-instruct` runs, same day, same 10 records (SYNTH-0000 through
SYNTH-0009).

**Why this model, again:** M4's original raw tool-calling benchmark
(`docs/model-benchmark.md`) scored `qwen3:8b` at **0%** valid-call rate -
"both zero-scores from emitting multiple tool calls per turn rather than
the one this benchmark scores." `agent_loop.py` explicitly preserves the
model's own multi-tool-call ordering within a turn rather than rejecting
it (a real architectural property, not an assumption - see its own test
coverage), so this looked like it might be an artifact of M4's narrower
benchmark methodology rather than a real capability gap. Worth checking
for real rather than trusting the 0% number, especially after
`qwen2.5:7b-instruct` (M4's 40% runner-up) turned out to score *worse*
than that raw number implied (0/10 exhausted - see
`docs/evaluation-qwen25-7b-2026-09-09.md`).

## Result: a real correction to M4's finding

**Status breakdown:** 8/10 completed, 0/10 escalated, 2/10 exhausted (one
exhausted record, `SYNTH-0004`, still scored 6/6 correct - a real write
happened before the loop ran out of iterations; "exhausted" reflects only
how the loop ended, not whether anything was written before that -
correcting an assumption stated in `docs/evaluation-broader-sample-
2026-09-09.md`, "escalated/exhausted... never write by definition", which
this run shows is not reliably true for exhaustion specifically).

**Per-field accuracy, exact same 10 records, both models, same day, same
harness:**

| field | llama3.1:8b | qwen3:8b |
|---|---|---|
| quantity_tonnes | 3/10 (30%) | 3/10 (30%) |
| data_source | 3/10 (30%) | 3/10 (30%) |
| carbon_price_paid_origin | 3/10 (30%) | 3/10 (30%) |
| precursor_emissions | 3/10 (30%) | 2/10 (20%) |
| direct_emissions_actual | 1/8 (12%) | 1/8 (12%) |
| indirect_emissions_actual | 1/8 (12%) | 1/8 (12%) |

| status | llama3.1:8b | qwen3:8b |
|---|---|---|
| completed | 4/10 | **8/10** |
| escalated | 5/10 | **0/10** |
| exhausted | 1/10 | 2/10 |

**Field accuracy is essentially identical** (differing by exactly one
record, on one field) - but `qwen3:8b` reaches a terminal, successful
action **twice as often** (8/10 vs. 4/10) and never once escalated,
whereas `llama3.1:8b` escalated on half the sample. Given the accuracy
is a tie, the completion-rate difference makes `qwen3:8b` arguably the
*stronger* practical choice on this evidence, not the unusable 0%-rate
model M4's raw benchmark suggested.

## Conclusion

M4's raw tool-calling benchmark ranking does **not** hold up for this
model on the real, fixed harness - `qwen3:8b`'s 0% valid-call score was a
real artifact of that benchmark's narrower scoring rule (single tool call
per turn only), not a reflection of its actual usefulness for this
project's actual agent loop, which handles multi-call turns natively.
This is a genuine, evidence-based correction to this project's model
selection, not a hedge: a same-day, same-records, same-harness,
same-fixes comparison is about as fair a test as this session can
produce. `qwen2.5:14b-instruct` (M4's other 0%-scoring model, for the
same multi-tool-call reason) was not re-tested this session and remains
an open question.
