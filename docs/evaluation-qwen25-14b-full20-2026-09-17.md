# CBAM Agent Loop Evaluation — qwen2.5:14b-instruct, full 20 records

Model: qwen2.5:14b-instruct, real live Ollama via the nginx gate (local-dev
stack), real `FixtureOdooClient` harness, all prior session's fixes in
effect (known_context injection, lookup-result carryover, temperature=0.1,
the write_declaration_line prompt fix, remembered-write-fields carryover).
Same 20 synthetic records (`SYNTH-0000` through `SYNTH-0019`) and same
harness/fixes as `llama3.1:8b`'s full-20 run
(`docs/evaluation-full20-2026-09-09.md`).

**Why this model:** flagged as the concrete open item in
`docs/evaluation-qwen3-8b-2026-09-09.md`'s conclusion — M4's original raw
tool-calling benchmark scored `qwen2.5:14b-instruct` at 0% for the same
reason `qwen3:8b` was wrongly scored 0% (emitting multiple tool calls per
turn, which `agent_loop.py` handles natively but M4's narrower benchmark
did not credit). Never re-tested against the real, fixed harness until now.

**Run mechanics:** run in 4 batches of 5 records (`records[0:5]`,
`[5:10]`, `[10:15]`, `[15:20]`), each in its own fresh Python process,
after a single-process full-20 attempt was killed by this session's
background-task memory monitor (same memory-pressure pattern documented in
`docs/PROGRESS.md`'s "The full 20-record run" section, despite the
`~/.wslconfig` memory-ceiling fix from that session still being in place).
Batching per fresh process avoided any further kill — no OOM in any of the
4 batches. The model was confirmed fully GPU-resident during the run
(`nvidia-smi`: ~9.8/12.2 GB VRAM used), so the earlier single-process kill
was host-side memory-accounting pressure, not the model spilling to CPU.

**Live spot-check before trusting the aggregate number:** traced
`SYNTH-0007` (aluminium/secondary_recycled/MA, real document text
containing "Direct embedded emissions : 0.105 tCO2e/t" / "Indirect embedded
emissions: 0.331 tCO2e/t") message-by-message. The model called
`extract_field` for all three actual-value fields, correctly read
`direct_emissions_actual=0.105` and `indirect_emissions_actual=0.331` out
of the raw document text, and called `write_declaration_line` with those
exact values under their correct field names — a genuine, unaided
extraction, not a scoring artifact or a known_context pass-through (these
two fields are never dispatcher-injected).

## Result

**Status breakdown:**

| | completed | escalated | exhausted |
|---|---|---|---|
| 20 records | 14 | 0 | 6 |

**Per-field accuracy:**

| field | llama3.1:8b (full 20) | qwen2.5:14b-instruct (full 20) |
|---|---|---|
| quantity_tonnes | 4/20 (20%) | 14/20 (70%) |
| data_source | 4/20 (20%) | 14/20 (70%) |
| carbon_price_paid_origin | 3/20 (15%) | 12/20 (60%) |
| precursor_emissions | 4/20 (20%) | 14/20 (70%) |
| direct_emissions_actual | 1/14 (7%) | 8/14 (57%) |
| indirect_emissions_actual | 1/14 (7%) | 8/14 (57%) |

Every field improves substantially, including the two fields
(`direct_emissions_actual`/`indirect_emissions_actual`) that require
genuine, un-assisted document-text extraction and have been this project's
persistent ceiling across every prompt/plumbing fix tried against the two
smaller models. 14/20 completions all correspond to real writes (verified
by cross-referencing `quantity_tonnes`/`data_source`, which are only ever
correct via a genuine `write_declaration_line` call); the 6 exhausted
records all failed identically across every scored field (never reached a
write), a cleaner, more binary failure pattern than either smaller model's
mixed completed/escalated/exhausted spread.

## Comparison across all four models tested against this harness (same day/session where possible)

| model | completed | field accuracy range (plumbing-reachable fields) | direct/indirect actual accuracy |
|---|---|---|---|
| llama3.1:8b (full 20) | 5/20 | 15–20% | 7% |
| qwen2.5:7b-instruct (10 records) | 0/10 | 0% | 0% |
| qwen3:8b (10 records) | 8/10 | ~30% (tied with llama3.1:8b on the same 10) | 12% |
| **qwen2.5:14b-instruct (full 20)** | **14/20** | **60–70%** | **57%** |

## Conclusion

**A genuine, verified correction to M4's original ranking, and the
strongest result this project has measured against any model.**
`qwen2.5:14b-instruct` was one of two models M4's raw benchmark had
dismissed at 0% for a benchmark-methodology reason (single-tool-call
scoring), not a real capability gap — the same correction already proven
for `qwen3:8b`. Unlike that correction, which produced a result merely
*tied* with `llama3.1:8b`, this one is a clear, large improvement across
every scored field, at full 20-record scale (not just the 10-record
subsample used for the `qwen3:8b`/`qwen2.5:7b-instruct` comparisons).

This is consistent with the project's long-standing framing that the
remaining gap was the small (7-8B) models' own reliability at
constructing correct multi-field tool calls and reading numbers back out
of prose correctly — a larger model in the same family closes much, though
not all, of that gap. 6/20 records still fail completely (never reach a
write), and `carbon_price_paid_origin`/direct+indirect actuals are still
below 100% — this is a real, verified improvement, not a claim of
solved reliability.

**Recommendation:** `qwen2.5:14b-instruct` should be considered the new
default model choice for this project's agent loop, pending a decision on
the added GPU/VRAM cost (9.8 GB vs. `llama3.1:8b`'s much smaller
footprint — both fit this project's development GPU, an RTX 5070 with
12 GB VRAM, but with less headroom for anything else running concurrently).

**Verification:** no test suite changes — a real live-infra model
comparison, not a code change. Raw per-record results (status/iterations/
field_scores for all 20 records) were captured in an ad hoc scratch JSON
file during the run, not committed to the repo, mirroring how prior
sessions kept one-off trace data out of version control.

## Per-record breakdown

| record | status | iterations | fields correct |
|---|---|---|---|
| SYNTH-0000 | completed | 3 | 4/4 |
| SYNTH-0001 | exhausted | 9 | 0/6 |
| SYNTH-0002 | completed | 4 | 4/4 |
| SYNTH-0003 | completed | 7 | 6/6 |
| SYNTH-0004 | exhausted | 9 | 0/6 |
| SYNTH-0005 | exhausted | 9 | 0/6 |
| SYNTH-0006 | completed | 7 | 6/6 |
| SYNTH-0007 | completed | 9 | 6/6 |
| SYNTH-0008 | exhausted | 9 | 0/6 |
| SYNTH-0009 | completed | 5 | 6/6 |
| SYNTH-0010 | exhausted | 9 | 0/6 |
| SYNTH-0011 | completed | 7 | 6/6 |
| SYNTH-0012 | completed | 4 | 4/4 |
| SYNTH-0013 | completed | 7 | 6/6 |
| SYNTH-0014 | completed | 7 | 6/6 |
| SYNTH-0015 | exhausted | 9 | 0/6 |
| SYNTH-0016 | completed | 3 | 3/4 |
| SYNTH-0017 | completed | 3 | 3/4 |
| SYNTH-0018 | completed | 9 | 6/6 |
| SYNTH-0019 | completed | 4 | 4/4 |

("fields correct" denominator varies: 4 for records with no
`direct_emissions_actual`/`indirect_emissions_actual` ground truth to
score, i.e. `data_source="default"` records where those two fields are
`None` in ground truth and skipped by `scoring.py`'s null-skip rule; 6 for
`data_source="actual"` records.)
