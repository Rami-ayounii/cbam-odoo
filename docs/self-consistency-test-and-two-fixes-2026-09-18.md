# Self-consistency test (rejected), and two real fixes found instead

At the human partner's request, before deciding whether to adopt
self-consistency (running each record twice and taking a majority vote,
to guard against the temperature=0.1 stochasticity documented in
`docs/PROGRESS.md`'s full-50-record benchmark section), ran a controlled
experiment to check whether the cost (roughly doubling wall-clock and GPU
time per job - measured empirically at ~2.2-2.4s per agent-loop iteration,
~4.56 average iterations per record across the real 50-record dataset)
would actually buy anything.

## The experiment

15 records (`SYNTH-0000`-`SYNTH-0014`), 2 independent live runs each
(`qwen2.5:14b-instruct`, same harness, same fixes as every other
comparison this session) - 30 total agent-loop runs.

| outcome | count |
|---|---|
| Both runs fully correct | 13/15 |
| Both runs fully wrong (same failure, both times) | 2/15 |
| **Runs disagreed - one right, one wrong** | **0/15** |

## Decision: self-consistency rejected, not adopted

Zero records showed the pattern self-consistency is built to catch. Every
outcome was internally consistent - the errors present were systematic
(same root cause every run), not random noise a second draw would dodge.
Running twice and majority-voting would have cost 2x compute for zero
measured benefit here, and would have actively **increased false
confidence** on the 2 systematically-wrong records (two identical wrong
answers "agreeing" looks like high confidence, not a warning sign).
Decision: do not adopt self-consistency. Investigate the systematic
failures directly instead - unlike random noise, a systematic failure
has an actual fixable cause.

## Fix 1: carbon_price_paid_origin recovered even when the model never asks for it

**Root cause, traced live (`SYNTH-0009`):** the model's own extraction
plan sometimes only ever covers "extract direct and indirect emissions" -
it genuinely never calls `extract_field(field_name="carbon_price_paid_origin")`
at all, even though the real value (58.01) is sitting in the very same
document it already read for the other two fields. Not a parsing failure
(the regex handles this field correctly, already validated against the
full 50-record dataset) - an attention failure: the field simply never
occurs to the model to ask about.

**Fix (`softworker/orchestrator/tools.py`'s `_extract_field`):**
whenever the model calls `extract_field` for *any* field, the dispatcher
now also opportunistically runs the deterministic regex parse for
`carbon_price_paid_origin` against that same document text and remembers
the result silently (not added to the tool's visible result, to avoid
adding more fields for the model to parse) - filling the gap the same
way `write_declaration_line`'s remembered-field fallback already recovers
an explicitly-null field. The model never needs to think to ask for this
field by name.

TDD'd: `test_extract_field_opportunistically_remembers_carbon_price_even_when_never_asked_for`
reproduces the exact live failure (a dispatcher that only ever sees a
`direct_emissions_actual` extraction, never `carbon_price_paid_origin`)
before the fix, confirmed RED, then GREEN.

**Live-verified:** re-traced `SYNTH-0009` - now writes
`carbon_price_paid_origin=58.01` correctly, 6/6 fields, without the model
ever mentioning that field.

## Fix 2: stop wasting the entire iteration budget on a structurally impossible write

**Root cause, traced live (`SYNTH-0010`):** a `customs_declaration`
document (a document type that, by M1's generator design, never carries
emissions data at all) paired with `data_source="actual"`. There is
genuinely nothing to extract and nothing to quote. Instead of recognizing
this and escalating immediately, the model tried `lookup_default_value`
(a tool meant for `data_source="default"` lines) as a workaround, then
convinced itself in its own reasoning that "the data source is 'default'"
- which is false; `ToolDispatcher.execute()` always overrides
`data_source` from `known_context`, so every subsequent write attempt
kept getting the real `"actual"` value forced back in, re-triggering the
same `source_quote`-required validation error the model kept trying to
argue around. Burned all 9 iterations retrying near-identical failed
calls before the iteration-cap fallback finally escalated it.

**Fix - `SYSTEM_PROMPT` only** (`softworker/orchestrator/main.py`): added
an explicit paragraph stating that `data_source` is fixed by the context
object and cannot be changed by the model, naming the exact failure mode
observed (assuming "actual" must really mean "default" because a
customs-declaration-style document has no emissions data) and instructing
the model to call `flag_for_human_review` immediately in that situation
rather than retrying `lookup_default_value` or a rejected write with
small variations.

**Live-verified:** re-traced `SYNTH-0010` after the prompt change -
3 iterations instead of 9, a clean `escalated` status with the exact
correct reason ("no document contains this information"), instead of
`exhausted` after 9 rounds of self-contradictory reasoning. The field
score itself is unchanged (0/6 - the data is genuinely, structurally
unavailable, so escalating is the only correct outcome, exactly as
before), but the record now reaches that correct outcome using a third
of the iteration budget and with a status that's actually useful to
whoever reviews the escalation queue, instead of an ambiguous
"exhausted."

## Combined re-validation, records 0-19

| field | before both fixes | after both fixes |
|---|---|---|
| quantity_tonnes / data_source / precursor_emissions | 90% | 90% (unchanged - these were never the target) |
| carbon_price_paid_origin | 70% | **80%** |
| direct_emissions_actual | 86% | 86% (unchanged) |
| indirect_emissions_actual | 86% | 86% (unchanged) |

`carbon_price_paid_origin` is the field Fix 1 directly targets, and it's
the only one that moved - consistent with a targeted fix, not a lucky
sample.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 173
passed (172 + 1 new regression test for Fix 1; Fix 2 is prompt-only, no
test to add - `SYSTEM_PROMPT`'s content isn't asserted against by any
test, matching how every prior prompt fix in this project's history was
verified live rather than by unit test).
