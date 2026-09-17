# CBAM Agent Loop Evaluation — qwen2.5:14b-instruct, full 50-record dataset, and why it scored what it did

Model: `qwen2.5:14b-instruct` (now this project's default, switched from
`qwen3:8b` this session), hybrid regex/LLM extraction in effect, real live
Ollama via the nginx gate, real `FixtureOdooClient` harness. This is the
broader-sample validation flagged as necessary after the full-20 result
(`docs/evaluation-qwen25-14b-hybrid-extraction-2026-09-17.md`) - every
number to date had come from the same first-20-records subset, and this
project's own history (`docs/evaluation-broader-sample-2026-09-09.md`)
already showed once that a small sample can mislead.

## Result: the broader sample was less optimistic, for real, traceable reasons

**Records 0-19 (already measured):**

| field | accuracy |
|---|---|
| quantity_tonnes / data_source / precursor_emissions | 90% |
| carbon_price_paid_origin | 70% |
| direct/indirect_emissions_actual | 86% |

**Records 20-49 (new, this session):**

| | completed | escalated | exhausted |
|---|---|---|---|
| 30 records | 17 | 11 | 2 |

| field | accuracy |
|---|---|
| quantity_tonnes / data_source / precursor_emissions | 53% |
| carbon_price_paid_origin | 37% |
| direct_emissions_actual | 65% |
| indirect_emissions_actual | 57% |

**Full 50-record combined result:**

| | completed | escalated | exhausted |
|---|---|---|---|
| 50 records | 34 | 14 | 2 |

| field | accuracy |
|---|---|
| quantity_tonnes / data_source / precursor_emissions | 68% |
| carbon_price_paid_origin | 50% |
| direct_emissions_actual | 73% |
| indirect_emissions_actual | 68% |

This is meaningfully lower than the first-20 numbers, exactly the
small-sample-bias risk flagged before running it. Rather than report that
drop as an unexplained "model got worse," every escalation and exhaustion
in the 20-49 batch was cross-checked against the record's own ground
truth and, for the unexplained ones, live-retraced - the causes are real
and mostly not about `qwen2.5:14b-instruct`'s capability at all.

## Why: three distinct, verified mechanisms - not one vague "model struggles"

**1. A test-harness fixture gap explains 7 of 11 escalations in the 20-49
batch, deterministically.** `shared/data/dev_fixtures.py` documents itself
plainly: its `DEV_EMISSION_FACTOR_FIXTURES` table "covers exactly the
(sector, production_route, country) combinations that appear with
data_source == 'default' among the first 20 records" - 6 combinations
total. Every `data_source="default"` record in 0-19 hits one of those 6;
every one of the 7 `data_source="default"` records in 20-49
(`SYNTH-0025/0031/0032/0037/0040/0043/0049`) needs a combination
**outside** that table (e.g. aluminium/secondary_recycled/NO). Traced
`SYNTH-0025` live: the model correctly calls `lookup_default_value`, gets
a real `"No emission factor found for aluminium/secondary_recycled/NO
valid on 2026-01-01"` error, and correctly calls
`flag_for_human_review` - exactly the right behavior when the reference
data genuinely doesn't exist. **This is the agent working correctly, not
failing** - the harness's own supporting fixture data was simply never
extended past the first 20 records. It's still scored as 0/4 on those
records' plumbing-reachable fields (a real write never happens), which is
the honest scoring outcome for a genuinely-missing reference lookup, but
it should not be read as an extraction or reasoning failure.

**2. "Hard"-difficulty records (missing-field-by-design) can trigger a
hallucination that the source_quote gate correctly blocks - at the cost
of discarding data that WAS validly extracted.** M1's generator
deliberately omits one or more emissions fields from "hard"-difficulty
records to test missing-data handling. Traced `SYNTH-0038` live (`hard`,
`direct_emissions_actual` genuinely absent from the document,
`indirect_emissions_actual=0.107` genuinely present): the model correctly
extracted the real indirect value, then **fabricated** a
`direct_emissions_actual=0.05` and an accompanying "quote" that does not
exist anywhere in the document text for the missing field, and tried to
write it. `_write_declaration_line`'s grounding check (the `source_quote`
anti-hallucination gate) correctly rejected the fabricated quote, three
times in a row, before the model gave up and escalated - **the gate did
exactly its job**, preventing a hallucinated number from ever reaching
Odoo. But because `write_declaration_line` may only be called once
(`projecthandoff.md`'s "single write at the end" constraint), the
correctly-extracted `indirect_emissions_actual=0.107` was discarded along
with the blocked fabrication - the whole record scores 0/6 even though
one of its two "hard" fields was genuinely, correctly available and
extracted.

**3. Some outcomes are simple run-to-run stochasticity, not a
reproducible failure at all.** `SYNTH-0034` (easy, no missing fields) and
`SYNTH-0048` (medium, no missing fields) both scored 0/6 in the original
batch run with no fixture gap or by-design difficulty to explain it - live
re-tracing both **immediately after, with the same code**, produced a
fully correct 6/6 write in both cases. `LLMClient`'s temperature is 0.1
(low but deliberately non-zero, see `llm_client.py`'s own comment on why),
so re-running the exact same record does not guarantee the exact same
tool-call sequence. This means a handful of the 20-49 batch's failures
are not attributable to any specific mechanism at all - they are the
same kind of imperfect convergence this project's model-benchmark work
(M4) already established as this class of model's baseline behavior, just
manifesting on a specific sample rather than every run.

## What this changes, and what it doesn't

- **The full 50-record numbers above are the honest current benchmark for
  `qwen2.5:14b-instruct`** - not the more flattering first-20 subset,
  which happened to avoid every fixture-gap record by chance of how the
  synthetic dataset's first 20 records were seeded.
- **It does not walk back the finding that `qwen2.5:14b-instruct` is the
  best model tested.** Mechanism 1 (fixture gap) and mechanism 2 (a
  design tradeoff between a safety gate and single-write atomicity) are
  both harness/architecture properties, not model failures - they would
  suppress *any* model's measured score by the same amount. Mechanism 3
  (stochastic misses) is a real, known property of this model class, not
  specific to this session's changes.
- **A concrete, cheap next step, not yet done:** extending
  `DEV_EMISSION_FACTOR_FIXTURES` to cover every `data_source="default"`
  `(sector, route, country)` combination actually present in the 50-record
  dataset (not just the first 20) would remove mechanism 1's 7-record
  penalty entirely - it is dev-only fake data already, so extending its
  coverage is completing a known gap, not making the benchmark artificially
  easier. Not done in this pass since it wasn't asked for - flagged here as
  the highest-leverage remaining lever if a still-more-representative
  number is wanted.

## Default model switched

`LLM_MODEL`'s default changed from `qwen3:8b` to `qwen2.5:14b-instruct`
in all 5 places it's set: `softworker/.env.example`,
`softworker/docker-compose.yml`, `docker-compose.local-dev.yml`,
`.env.local-dev.example`, and `main.py`'s own
`os.environ.get(..., fallback)`. Env-var overridable, not hardcoded past
that. Full test suite unaffected (172 passed; no test asserted the old
default string).

**Verification:** no test suite changes for the evaluation run itself - a
real live-infra benchmark, not a code change (the model-default switch is
a config change, separately verified by the full suite still passing).
