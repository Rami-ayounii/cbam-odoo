# CBAM Agent Loop Evaluation — qwen2.5:14b-instruct with hybrid regex/LLM extraction (punch list "Add #1")

Model: `qwen2.5:14b-instruct` (this project's strongest model to date, per
`docs/evaluation-qwen25-14b-full20-2026-09-17.md`), real live Ollama via
the nginx gate, real `FixtureOdooClient` harness, same 20 records
(`SYNTH-0000`-`SYNTH-0019`) as every other full-20 comparison this session.

**What changed:** implemented the punch list's "Add #1" item - a
deterministic regex pre-parse for `extract_field`, targeting the fixed
document templates `shared/synthetic_data/generator.py` actually produces
("Direct embedded emissions : 0.105 tCO2e/t" doesn't need an LLM to read
correctly). New module `softworker/orchestrator/field_extraction.py`;
wired into `tools.py`'s `_extract_field` so a successful regex match adds
the parsed value to the tool result **keyed by the field's own real
argument name** (e.g. `"direct_emissions_actual": 0.105`), alongside a
`source_quote` and guidance text - `document_text` is still always
returned too, so a field with no pattern, or a "hard"-difficulty record
where the field is genuinely absent, falls back to exactly the prior
behavior.

**Validated against the real 50-record dataset before any live model
testing:** `direct_emissions_actual`/`indirect_emissions_actual`/
`quantity_tonnes` all reach 100% correct coverage with zero wrong answers;
`carbon_price_paid_origin` correctly declines to guess (returns no value,
falls back to the model) for the 8/50 records where its document type
never states carbon price at all, rather than risk a wrong answer -
prioritizing safety over coverage.

## Two real regressions found live, fixed, and verified before trusting any result

Live testing surfaced two genuine bugs this static validation couldn't
have caught - both root-caused with real traces, not guessed.

**Bug 1 - shape mimicry into `write_declaration_line`.** A first live run
showed `direct_emissions_actual`/`indirect_emissions_actual` accuracy drop
sharply (57%→21%/14%) instead of improving. Tracing `SYNTH-0003` showed why:
the initial design returned a generic `{"field_name": "direct_emissions_actual",
"parsed_value": 0.59}` shape from `extract_field`, and the model mimicked
that exact shape into `write_declaration_line({"field_name": ...,
"value": ...})` instead of using that tool's own named arguments.
Pydantic silently drops unrecognized extra keys by default, so the call
"succeeded" with every real field left at its 0.0 default. **Fix:** key
the result by the field's own real argument name instead of a generic
wrapper - copying the shape now produces a *correct* call. Verified live:
the same record went from wrong to a fully correct 6/6 write.

**Bug 2 - a null-coercion fix that hid a worse problem.** While fixing Bug
1's trace, the model was observed passing an explicit `null` for a field
it hadn't extracted yet instead of omitting the key - `WriteDeclarationLineArgs`
typed these as required `float` (not `Optional`), so an explicit null
hard-failed validation and wasted a retry. First attempt: coerce null→0.0
in a `field_validator`. This *introduced* a worse bug: a full 20-record
re-run showed `direct_emissions_actual` drop to 29% even though `indirect_emissions_actual`
correctly extracted alongside it - the model would pass a correct
extract_field-derived value for one field and an explicit `null` for the
other (a field it *had* just extracted correctly), and the null-coercion
fix silently zeroed it instead of recovering the real value, because
`extract_field`'s parsed values were never fed into the dispatcher's
existing remembered-value mechanism (the one `lookup_default_value`
already uses). **Real fix:** `_extract_field` now remembers its own
successful parses the same way `_lookup_default_value` already remembers
its result; `write_declaration_line`'s remembered-field fallback now
treats an explicit `null` the same as an absent key (never overriding a
real non-null value the model deliberately states, only filling a gap).
Verified live: the same record (`SYNTH-0006`) went from a wrong 0.0 to a
correct `0.117`, with the model still passing `null` for it exactly as
before - the dispatcher now recovers correctly instead of the model
needing to behave differently.

Both fixes are TDD'd with regression tests reproducing the exact live
failure before the fix (`softworker/tests/test_tools.py`,
`softworker/tests/test_field_extraction.py`); full suite: 172 passed.

## Final result, all fixes in effect

| | completed | escalated | exhausted |
|---|---|---|---|
| 20 records | 17 | 3 | 0 |

| field | before hybrid extraction | after (all fixes) |
|---|---|---|
| quantity_tonnes | 70% | **90%** |
| data_source | 70% | **90%** |
| carbon_price_paid_origin | 60% | **70%** |
| precursor_emissions | 70% | **90%** |
| direct_emissions_actual | 57% | **86%** |
| indirect_emissions_actual | 57% | **86%** |

**This is the strongest result this project has measured on any model,
any fix, at full 20-record scale.** The two genuine-extraction fields
(`direct_emissions_actual`/`indirect_emissions_actual`) - the fields every
prompt/plumbing fix on the smaller 7-8B models never moved past ~10%, and
that even `qwen2.5:14b-instruct` itself only reached 57% on without this
fix - now sit at 86%, and the two are no longer asymmetric (both fixes
resolved the direct-vs-indirect gap the intermediate, buggy versions
showed). 0 exhausted records this run (down from 3), and the completion
pattern is cleaner: every remaining gap is either a genuine document
comprehension miss or one of the 8 structurally-unknowable
`carbon_price_paid_origin` cases already documented above.

## Honest limits, stated plainly

- This targets the harness's own fixed document templates, not
  general-purpose document understanding - a real-world supplier document
  in a different format will not match these regex patterns and falls
  back to exactly the model-reads-document_text behavior from before this
  change existed. The improvement is real for this benchmark; it is not a
  claim about extraction robustness against arbitrary real-world documents.
- The `carbon_price_paid_origin` "infer 0.0 from absence" rule is scoped
  to the harness's own document generation logic (verified: an emissions-
  declaration section marker must be present) - a real production
  document without such a marker would not get this inference either,
  which is the conservative, safe choice.
- Both regressions found here were introduced by this session's own
  changes and fixed within the same session, live-verified each time
  rather than trusted from a single aggregate number - consistent with
  this project's established practice of tracing before concluding.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 172
passed (154 + 18 new: 14 in `test_field_extraction.py`, 4 in
`test_tools.py`; no existing test's expectations changed).
