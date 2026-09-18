# check_consistency grounding: catching a fabrication one step earlier

Direct continuation of the punch list's "Change #2" item
(`docs/PROGRESS.md`'s "Session synthesis" section): `check_consistency`
previously validated a dict the model hand-constructs with zero
connection to `self._extracted_texts` - a model could report a fabricated
number and get `{"issues": []}` back. This was already directly evidenced
by the earlier `SYNTH-0038` trace (the "self-consistency test" section):
the model fabricated `direct_emissions_actual=0.05` for a field genuinely
absent from the document, `check_consistency` said nothing was wrong, and
the fabrication was only caught much later by `write_declaration_line`'s
stricter, quote-based `source_quote` gate - after 3 wasted write attempts
arguing about it.

## The fix

`softworker/orchestrator/tools.py`'s `_check_consistency` now checks
`direct_emissions_actual`/`indirect_emissions_actual` against
`self._extracted_texts` (the same session-state list
`write_declaration_line`'s grounding check already uses) - if the claimed
value's string representation doesn't appear anywhere in a document
`extract_field` has actually returned this job, it's flagged as a
possible fabrication, with a specific issue message naming the value and
suggesting `flag_for_human_review`. `0` is exempt (the field's own
Pydantic default, not a plausible hallucination target - a model passing
0 to mean "I don't have this" shouldn't get a misleading extra warning).

TDD'd: `test_check_consistency_flags_a_value_never_actually_extracted`
reproduces the `SYNTH-0038` shape (a fabricated value, no matching
extract_field call) before the fix, confirmed RED, then GREEN.
`test_check_consistency_returns_no_issues_for_clean_data` was updated to
call `extract_field` with matching text first, since "clean data" now
means "grounded data," not just "individually plausible numbers" -
matching how prior anti-hallucination-gate tests were updated the same
way. `test_check_consistency_does_not_flag_zero_as_a_fabrication` covers
the exemption. Full suite: 175 passed (173 + 2 new).

## Live-verified

Re-traced `SYNTH-0038` after the fix. The model fabricated a *different*
value this time (`0.214`, not the earlier `0.05` - confirming this is a
real, recurring failure mode with the same shape each time, not a one-off
coincidence) for the same genuinely-absent field. `check_consistency`
caught it immediately and returned the exact new issue message; the model
correctly interpreted the feedback and escalated in **5 iterations**
(vs. 8 previously) with an honest, specific reason ("could not be
verified against the document text provided"), instead of trying to
write anyway and getting blocked 3 times by the stricter gate at the very
last step.

The field score is unchanged (0/6 - the data is genuinely, structurally
absent from this "hard"-difficulty record, so escalating is the correct
final outcome either way) - the win is reaching that correct outcome
faster, and via an honest signal (the model recognizing its own
fabrication) rather than a hard rejection it kept arguing with.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 175
passed (173 + 2 new regression tests; no existing test's expectations
changed beyond the one updated setup noted above).
