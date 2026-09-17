# CBAM Agent Loop Evaluation — full 50-record dataset, after fixing the dev-fixture coverage gap

Direct continuation of `docs/evaluation-qwen25-14b-full50-2026-09-18.md`,
which identified three mechanisms behind that run's lower-than-expected
score and flagged the dev-fixture coverage gap as "the highest-leverage
remaining step, not implemented in this pass." Implemented and
re-measured here.

## The fix

`shared/data/dev_fixtures.py`'s `DEV_EMISSION_FACTOR_FIXTURES` explicitly
covered only the `(sector, route, country)` combinations needed by the
first 20 synthetic records' `data_source="default"` lines (6 entries).
Extended to cover all 13 combinations actually present across the full
50-record dataset - 7 new entries
(`steel/BF-BOF/MA`, `steel/EAF_scrap/{BR,MA,TR}`,
`aluminium/secondary_recycled/{CA,MA,NO}`), same style as the existing
6 (arbitrary round numbers in generator.py's own plausible per-route
range, `indirect_ef=0.0` throughout matching every existing entry -
consistent with this project's "direct emissions only" constraint, since
`calc_engine` never prices indirect anyway). TDD'd: the existing test
`test_fixtures_cover_every_default_sourced_combo_in_first_20_synthetic_records`
was widened to check the full dataset, confirmed RED against the old
6-entry table (failed with exactly the 7 missing combos), then GREEN
after extending it.

**Live-verified before trusting the aggregate:** re-traced `SYNTH-0025`
(aluminium/secondary_recycled/NO, previously a 2-iteration escalation on
a real "no emission factor found" error) - `lookup_default_value` now
resolves a real factor (`emission_factor_id=13`, the new fixture) and the
record completes with a genuine write.

## Result: exactly the improvement the diagnosis predicted

**Records 20-49, before vs. after the fixture fix:**

| | completed | escalated | exhausted |
|---|---|---|---|
| before | 17 | 11 | 2 |
| after | 24 | 4 | 2 |

Escalations dropped by exactly 7 - the exact count of `data_source="default"`
records that needed a combination outside the original 6-entry table.

| field | records 20-49, before | records 20-49, after |
|---|---|---|
| quantity_tonnes / data_source / precursor_emissions | 53% | 83% |
| carbon_price_paid_origin | 37% | 60% |
| direct_emissions_actual | 65% | 78% |
| indirect_emissions_actual | 57% | 70% |

**Full 50-record result, before vs. after:**

| field | full 50, before | full 50, after |
|---|---|---|
| quantity_tonnes / data_source / precursor_emissions | 68% | **86%** |
| carbon_price_paid_origin | 50% | **64%** |
| direct_emissions_actual | 73% | **81%** |
| indirect_emissions_actual | 68% | **76%** |

This is now close to the original (misleadingly optimistic) first-20-only
numbers (90%/90%/70%/90%/86%/86%) rather than far below them, on the
honest full 50-record sample - confirming the diagnosis in the prior
section correctly identified the dominant, fixable cause.

## What's left, honestly

The remaining gap between "after" and the first-20 numbers is now mostly
mechanisms 2 (source_quote gate correctly blocking a hallucination on a
"hard" record, at the cost of the whole write) and 3 (run-to-run
stochasticity at temperature=0.1) from the prior section - both
architecture/model properties, not further fixture gaps. Not re-traced
individually again here; the prior section's live evidence for those two
mechanisms still stands (they were not touched by this fix).

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 172
passed (unchanged count - `test_dev_fixtures.py`'s coverage test was
widened in place to check the full dataset instead of just the first 20,
not added as a new test; no other existing test's expectations changed).
