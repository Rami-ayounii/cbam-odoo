# CBAM Agent Loop Evaluation - broader unselected sample

Records evaluated: 5 (SYNTH-0000 through SYNTH-0004, first 5 of the
standard 20-record M9 set, run in numeric order - not hand-picked)

Model: llama3.1:8b, real live Ollama via the nginx gate, all of this
session's fixes in effect (known_context injection, lookup-result
carryover, temperature=0.1, the write_declaration_line prompt fix, the
remembered-write-fields carryover). Run via `FixtureOdooClient` (the
standard M9 harness), not the real Odoo database - see
docs/PROGRESS.md's "Real production-path verification" section for the
distinct, hand-picked, real-Odoo tests that did succeed.

A second batch (records 5-9) was not run - this machine's available RAM
was already critical (536 MB free of 16 GB) after this first batch, and
the human partner chose to stop and report this honestly rather than risk
further instability chasing more data points.

## Status breakdown
- completed: 1
- escalated: 3
- exhausted: 1

## Iteration distribution
- 3 iteration(s): 1 record(s)
- 4 iteration(s): 2 record(s)
- 8 iteration(s): 1 record(s)
- 9 iteration(s): 1 record(s)

## Per-field accuracy
- quantity_tonnes: 0/5 (0%)
- data_source: 0/5 (0%)
- carbon_price_paid_origin: 0/5 (0%)
- precursor_emissions: 0/5 (0%)
- direct_emissions_actual: 0/3 (0%)
- indirect_emissions_actual: 0/3 (0%)

## Interpretation

0/5 - including `quantity_tonnes`/`data_source`, which are unconditionally
correct whenever a real `write_declaration_line` call actually happens
(they are dispatcher-injected from ground truth, never model-supplied -
see `tools.py`'s `known_context` injection). Their being wrong here means
**no record in this batch reached a real write at all** - 1 "completed"
(which can mean a silent stop with nothing written, a known ambiguity
documented in this project's history) and 4 escalated/exhausted (which
never write by definition).

This is a materially different, more sobering result than the two
hand-picked single-record live tests in docs/PROGRESS.md's "Real
production-path verification" and "Remembered-value carryover" sections,
which both succeeded reproducibly. The difference is sample selection:
those two tests used one specific record each, re-run twice - a real
result, but not a representative one. This batch is the first 5 records
in numeric order, unselected, and shows the underlying `llama3.1:8b`
tool-calling reliability problem (M4's original 50% valid-call-rate
finding) is still very much present across a broader sample - this
session's fixes measurably improved specific, diagnosed failure modes
(missing document_id, schema-required-field burden, value carryover) but
did not make the model reliable in general. Both things are true at once:
the fixes are real and independently verified, and the model remains the
binding constraint on average-case reliability.
