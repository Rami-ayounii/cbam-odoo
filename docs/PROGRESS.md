# CBAM Project — Progress Tracker

*Academic project: Odoo 17 + Agentic LLM (Ollama) for EU Carbon Border Adjustment Mechanism declarations.*
*Last updated: 2026-09-08*

---

## Quick Status

| Milestone | Status | Commit |
|-----------|--------|--------|
| M0 — Repo scaffold & networking | **Done** | `16ec5ec` |
| M1 — Synthetic data generator | **Done** | `58c4baa` |
| M2 — Calculation engine | **Done** (certificate formula corrected later, see commit `db50c1f`) | `2d89d37` |
| M3 — Odoo module (`cbam`) | **Done, live-installed** (real Odoo 17 + Postgres, no addon changes needed) | `6a2e1b4` |
| M4 — LLM inference container (Hardworker) | **Done** — original raw benchmark winner `llama3.1:8b` (50% valid-rate), nginx API-key gate verified for real. Re-tested on the real fixed harness (2026-09-09): `qwen2.5:7b-instruct` (the 40% runner-up) scored worse (10/10 exhausted, 0% accuracy) — "Model comparison" section — but `qwen3:8b` (originally 0% valid-rate, dismissed) essentially **tied** `llama3.1:8b` on field accuracy while completing twice as often with zero escalations — the original 0% ranking was a benchmark-methodology artifact, not a real capability gap; see "qwen3:8b re-test" section. Model choice is now genuinely open between llama3.1:8b and qwen3:8b, not settled | `9d4851a` |
| M5 — Tool schemas | **Done** | `2d89d37` |
| M6 — Orchestrator agent loop | **Done, live-verified** (first real end-to-end LLM+Odoo run; job `completed`, 3 real infra bugs found and fixed — that run's status was later reclassified `no_write`, see Agentic completion-gap follow-up section) — see the Real production-path verification section for the first run that genuinely wrote a real row via the real API (values still wrong: a value-carryover failure between the model's own tool calls, not a plumbing bug) | `b1a7d17` |
| M7 — Versioned emission factor data load | **Done, real data resolved (not yet loaded into a live Odoo instance)** — 2 EU ETS benchmarks, the 2026 markup rate, 4 of 5 country/route emission factors (Turkiye BF-BOF, Azerbaijan EAF_scrap, Bahrain primary_electrolysis, Tunisia secondary_recycled), the 2026 `reference_certificate_price` (average of the two published quarters), and `cbam_factor_year` (0.025 for 2026) are real and cited; steel EAF_DRI's `direct_ef` stays blocked (structurally absent from the source); `cbam.good.benchmark` gained a real route dimension ("Independent audit + follow-up fixes" section) and its steel EAF_scrap benchmark is now resolved too (0.142, a real "EAF carbon steel" row — see "M7 benchmark research" section); aluminium secondary_recycled's benchmark is re-confirmed genuinely absent from the source, not unchecked — `find_incomplete_seeds()` now returns 2 items | `2a4deec`, `c35dbbe`, `4923a9e` |
| M8 — Security hardening | **Done** | `2d89d37` |
| M9 — Evaluation | **Done, real run, full 20-record number obtained** — 0% field accuracy originally (`docs/evaluation.md`); a long sequence of real, live-verified fixes across this doc's later sections closed real bugs (missing document_id, excess required fields, a constraint blocking `data_source="default"` entirely, unset temperature, value carryover, a WSL2 memory-ceiling misconfiguration that was killing evaluation runs); final full-20 result (`docs/evaluation-full20-2026-09-09.md`): 5/20 completed (4 genuinely correct), field accuracy 15-20% on plumbing-reachable fields (was 0%), 7% on the two fields needing genuine document extraction (was 0%) — real, verified improvement, not reliability; `llama3.1:8b`'s own tool-calling ceiling (M4's 50% valid-call rate) remains the dominant constraint; next lever is a different/stronger model against this now-fixed harness | `ceaf01c` |

---

## What Is Built

### M0 — Repo scaffold & networking (commit `16ec5ec`)

**Files created:**
- `hardworker/docker-compose.yml` — Ollama + nginx sidecar on Tailscale network
- `hardworker/nginx.conf.template` — API-key gate (`X-Api-Key` header), rate limiting (10 r/s), streaming proxy (no buffering)
- `softworker/docker-compose.yml` — Odoo 17 + PostgreSQL 16 + orchestrator placeholder on Tailscale network
- `hardworker/.env.example` / `softworker/.env.example` — document all required secrets
- `tailscale-acl-example.json` — ACL restricting Softworker → Hardworker:8443 TCP only (blocks reverse)
- `.gitignore` / `.gitattributes` — excludes secrets and data volumes; normalises line endings to LF

**Key decisions locked in:**
- Tailscale sidecar container pattern: all app containers use `network_mode: service:tailscale`
- nginx uses `nginx.conf.template` → Docker image runs `envsubst` at startup to inject `${OLLAMA_API_KEY}`
- PostgreSQL is on an internal Docker network only (not exposed to Tailscale)
- All secrets via `.env` (never committed)

**Not yet done in M0:** Tailscale mesh verification (needs actual machines).

---

### M1 — Synthetic data generator (commit `58c4baa`)

**Files created:**
- `shared/synthetic_data/generator.py` — Faker + numpy generator producing three document types
- `shared/synthetic_data/requirements.txt` — `faker>=24.0.0`, `numpy>=1.26.0`
- `shared/synthetic_data/output/` — 50 JSON records (`SYNTH-NNNN-XXXXXX.json`) + `index.json`

**What the generator produces:**
- **Three document types:** EN 10204 mill certificate (steel), CBAM carbon intensity report, SAD customs declaration
- **Three difficulty levels:** easy (all fields in plain text), medium (quantity in kg not tonnes), hard (some fields absent from the document)
- **Ground-truth labels** stored per record (14 fields incl. `direct_emissions_actual`, `indirect_emissions_actual`, `carbon_price_paid_origin`, `missing_fields`) — used for M9 evaluation
- **Boundary-case seeding:** every 8th record has quantity near 50 t (exemption threshold)
- **CLI:** `python generator.py --count 50 --seed 42 --outdir output/`

**Note:** Emission ranges in the generator are approximate (for realistic-looking documents only). Authoritative JRC134682 values go into the versioned `cbam.emission_factor` table in M7.

---

### Research artifact — CBAM formulas (not a milestone, commit `2d89d37`)

**File:** `CBAM_Formulas_Steel_Aluminium.md`

Comprehensive reference sheet compiled July 2026 covering:
- General CBAM formulas (embedded emissions, SEE, direct/indirect split)
- Steel sector: sinter plant, blast furnace, BOF, EAF, DRI, downstream products (all with exact mass-balance equations)
- Aluminium sector: primary Al CO2 (anode consumption), PFC emissions (CF4/C2F6 slope + overvoltage methods), secondary Al, downstream products
- Certificate calculation formula (SEE → certificates, with benchmark deduction and carbon price adjustment)
- Legal basis: Reg 2023/956, IR 2023/1773, IR 2025/2547, IR 2025/2620/2621, EU ETS MRR 2018/2066

**This document directly unblocks M2 (calc engine) and M7 (emission factor seeding).**

---

## What Comes Next

### M2 — Calculation engine (built 2026-07-30, commit `2d89d37`)

**Files created:**
- `softworker/addons/cbam/utils/calc_engine.py` — the four functions below, plus `EmissionFactor` dataclass
- `softworker/tests/test_calc_engine.py` — 15 tests, all passing
- `softworker/tests/conftest.py` — adds `softworker/addons` to `sys.path` so tests import `cbam.utils.calc_engine` without the Odoo module needing a manifest yet
- `softworker/addons/cbam/__init__.py`, `softworker/addons/cbam/utils/__init__.py` — package markers (M3 will add `__manifest__.py` alongside)
- `softworker/requirements-dev.txt` — `pytest>=8.0.0`

**Functions implemented:**

```python
calculate_embedded_emissions(quantity_tonnes, direct_ef, indirect_ef, precursor_emissions) -> float
# SEE = direct_ef + indirect_ef; result = quantity_tonnes * SEE + precursor_emissions

calculate_certificates_required(
    embedded_emissions_total: float,   # t CO2e
    quantity_tonnes: float,
    benchmark: float,                  # t CO2e/t, EU ETS free-allocation benchmark
    cbam_factor_year: float,            # phase-out factor (2.5% 2026 -> 100% 2034)
    carbon_price_paid_origin: float,    # EUR/t CO2e paid in exporting country
    reference_certificate_price: float, # EUR/t CO2e, reference CBAM certificate price
) -> float
# N = max(embedded_emissions_total - benchmark*(1-cbam_factor_year)*quantity_tonnes, 0)
# N_final = N * (1 - min(carbon_price_paid_origin / reference_certificate_price, 1.0)), never negative
#
# NOTE: a sign-inversion bug in this formula (it originally read
# benchmark*cbam_factor_year*quantity_tonnes, without the (1 - ...)
# complement) was found and fixed later on this branch, commit `db50c1f`.
# See the M7 section below (Task 11 paragraph) for the full explanation.

lookup_emission_factor(sector, route, country, declaration_date, db_session) -> EmissionFactor
# db_session duck-types get_emission_factors(sector, route, country); picks the one record where
# valid_from <= date < valid_to; raises ValueError on zero or >1 matches (overlap = bad versioned data)

is_exempt(total_annual_tonnes: float) -> bool   # True if < 50 t/year
```

**Deviation from the original plan (resolved with the user before implementing):** the original
2-arg `calculate_certificates_required(embedded_emissions_total, carbon_price_paid_origin)` signature
was dimensionally broken — `carbon_price_paid_origin` is a EUR/t price, not a tonnes quantity, so it
can't be subtracted from a tonnes total. Replaced with the full Art. 9/31 formula (benchmark +
phase-out factor + reference certificate price as explicit, never-hardcoded inputs) per user's choice.

**Test cases actually written** (illustrative EFs, not asserted as authoritative JRC134682 values —
those only get baked into real records in M7):
- Embedded emissions: direct-only steel case, precursor-inclusive downstream case, zero-quantity case
- Certificates: no adjustment, benchmark deduction only, carbon-price deduction only, price-adjustment
  capped at 100%, result floored at 0 when benchmark deduction exceeds the total
- Exemption boundary: 49.9 t (exempt), 50.0 t (not exempt), 50.1 t (not exempt)
- Versioned lookup: two non-overlapping date ranges (picks correct record either side of the
  transition date), no match raises `ValueError`, overlapping records raise `ValueError`

**Done:** `pytest softworker/tests/test_calc_engine.py -v` → 20 passed (15 built test-first here, RED
confirmed via `ModuleNotFoundError` before `calc_engine.py` existed, then GREEN; 5 more added later by
Task 8 alongside the sign-inversion fix above).

**Not done yet:** committed in `2d89d37`; `benchmark`, `cbam_factor_year`, and
`reference_certificate_price` still need a real source (JRC/EU ETS benchmark decisions, the phase-out
schedule, and the published reference certificate price) — deferred to M7 alongside emission factors.

---

### M3 — Odoo module (`cbam`) (built 2026-07-30, commit `2d89d37`)

**IMPORTANT CAVEAT — not runtime-verified.** No Docker or Odoo installation
is available in this dev environment, so this module has only been checked
statically (`py_compile` on every `.py` file, `xml.dom.minidom` parse on
every view/report XML — both clean). It has **not** been loaded into a real
Odoo 17 instance. First thing to do once Softworker is up: `docker compose up`
and install the module, then fix whatever the ORM registry actually
complains about.

**Files created:**
- `softworker/addons/cbam/__manifest__.py` — depends on `base`, `mail`; no external Python packages
- `softworker/addons/cbam/models/` — `cbam_production_route.py`, `cbam_installation.py`, `cbam_good.py`, `cbam_emission_factor.py` (versioned, with an `@api.constrains` overlap guard), `cbam_year_parameter.py` (**new, not in the original data model**), `cbam_declaration.py`, `cbam_declaration_line.py`, `cbam_source_document.py`
- `softworker/addons/cbam/utils/odoo_adapters.py` — `OdooEmissionFactorSession`, the ORM-backed adapter `lookup_emission_factor()` needs; kept out of `calc_engine.py` so the calc engine stays Odoo-free and standalone-testable
- `softworker/addons/cbam/security/ir.model.access.csv` — base user (mostly read + line-level write) vs. `base.group_system` (full CRUD) for all 7 models
- `softworker/addons/cbam/views/` — `cbam_declaration_views.xml` (form embeds an editable line list with a "Lookup Default EF" button), `cbam_declaration_line_views.xml`, `cbam_source_document_views.xml`, `cbam_menus.xml` (root menu + a Configuration submenu for the 5 reference-data models, using Odoo's auto-generated views — needed so the Many2one fields have something to select, wasn't explicitly asked for but the module is unusable without it)
- `softworker/addons/cbam/reports/cbam_declaration_report.xml` — basic QWeb PDF summary (declarant, year, status, totals, one row per line)

**Data-model addition beyond `projecthandoff.md` §6 (resolved with the user
before coding):** the original schema had no field for `benchmark`,
`cbam_factor_year`, or `reference_certificate_price`, which M2's
`calculate_certificates_required` needs (see M2 section above for why).
Added:
- `cbam.good.benchmark` — EU ETS free-allocation benchmark is per-product, so it lives on the good
- `cbam.year.parameter` (new model) — `year`, `cbam_factor_year`, `reference_certificate_price`, `source_document`, one record per reporting year, unique-constrained on `year`

**Wiring:** `cbam.declaration.line` has `embedded_emissions_total` and
`certificates_required` as `store=True` computed fields calling
`calc_engine.calculate_embedded_emissions` / `calculate_certificates_required`
directly — no business logic duplicated in the model. If no
`cbam.year.parameter` record exists yet for the declaration's reporting
year, `certificates_required` is left at `0.0` rather than guessing (M7 will
seed this data). `action_lookup_emission_factor()` on the line calls
`calc_engine.lookup_emission_factor()` through the adapter to populate
`emission_factor_id` — read-only selection, never writes a factor value.

**Not done:** committed in `2d89d37`; no live Odoo verification; no record rules yet
(declarants seeing only their own declarations is M8); reference data
(installations, goods, emission factors, year parameters) has no seed data,
so the module is currently empty on install.

---

### M4 — LLM inference container (Hardworker) — BLOCKED in this environment

**Why blocked:** steps 1-5 below need actual Docker + a real (or at least
present) Hardworker to pull and benchmark models against. This dev sandbox
has neither Docker nor an Ollama install (`docker --version` → command not
found). Nothing here is a code deliverable I can produce without live
infra - the `docker-compose.yml`/`nginx.conf.template` from M0 already
contain everything needed to run this once real hardware is available.

**Steps (unchanged from the plan, still to do on real Hardworker hardware):**
1. Bring up `hardworker/docker-compose.yml`
2. Pull candidate models: `qwen2.5:7b-instruct`, `qwen2.5:14b-instruct`, `llama3.1:8b-instruct`
3. Benchmark tool-calling reliability (10 attempts each with a JSON tool schema) — does the model return valid JSON calls consistently?
4. Pick the winner, document in `docs/model-benchmark.md`
5. Verify nginx: `curl -H "X-Api-Key: wrong" https://hardworker:8443/` → 401

---

### M5 — Tool schemas (built 2026-07-30, commit `2d89d37`)

**Note on the "depends on M4" in the original plan:** turned out not to be a
real blocker - these are OpenAI-compatible function-calling JSON schemas
(`name`/`description`/`parameters`), the same shape regardless of which
Ollama model wins the M4 benchmark. Built ahead of M4 since M4 itself is
blocked on hardware this sandbox doesn't have.

**Files created:** all 7 in `shared/tool_schemas/`, matching `projecthandoff.md`
§7's tool list and wired to the `cbam.declaration.line` field names from M3
(`quantity_tonnes`, `direct_emissions_actual`, `data_source`, etc.) so
`write_declaration_line`'s params map 1:1 onto what M6's `odoo_client.py`
will actually write:
- `extract_field.json`, `lookup_default_value.json`, `check_consistency.json`
- `request_missing_data.json`, `flag_for_human_review.json`
- `calculate_emissions.json`, `write_declaration_line.json`
- `test_tool_schemas.py` — 23 tests: each file is valid JSON, has `name`/`description`/`parameters`, every field the dispatcher will need is actually declared `required`, no duplicate tool names, all 7 files present. Built test-first (RED confirmed: 22/23 failed before any `.json` file existed).

Each schema stores the bare `{name, description, parameters}` object (per
the plan); the orchestrator (M6) is responsible for wrapping each in
`{"type": "function", "function": {...}}` when it builds the `tools=` list
for `llm.chat()`, since that wrapping is a client-format detail, not part
of the schema itself.

**Done:** `pytest shared/tool_schemas/test_tool_schemas.py -v` → 23 passed.

---

### M6 — Orchestrator agent loop (built 2026-07-30, commit `2d89d37`)

**IMPORTANT CAVEAT — not runtime-verified against a real LLM or Odoo.**
`fastapi`, `odoorpc`, `openai`, `tenacity`, `pydantic` were all installed
into this sandbox so the code below could be exercised for real (not just
`py_compile`), but every test fakes the LLM and Odoo boundaries - no actual
Ollama endpoint or Odoo instance was ever contacted. M4 being blocked means
this has never run end-to-end.

**Files created (all in `softworker/orchestrator/`):**
- `agent_loop.py` — `run_agent_loop()`, the tool-use loop from the skeleton below, generalized. Contains zero tool-ordering logic; the only name-based branch is detecting `flag_for_human_review` as a termination signal the model itself raised.
- `tools.py` — `ToolDispatcher`, a name→handler dict (pure dispatch, not a workflow) implementing all 7 tools. `calculate_emissions` and `lookup_default_value` call `calc_engine` directly; `write_declaration_line` is the only one that calls `odoo_client.write_declaration_line()`.
- `llm_client.py` — thin wrapper around `openai.OpenAI` pointed at Ollama's `/v1` endpoint; parses SDK responses into a small `LLMResponse`/`ToolCall` shape so `agent_loop.py` never touches the raw SDK. `@retry`-wrapped (tenacity) per the decided dependency list.
- `odoo_client.py` — `odoorpc`-based `OdooClient` + `OdoorpcEmissionFactorSession` adapter (separate from M3's ORM-`env`-based adapter, since the orchestrator talks to Odoo over RPC from its own container). `get_source_document_text()` does a plain UTF-8 decode of the attachment - correct for M1's synthetic plain-text documents, would need real OCR/PDF-text extraction added for scanned documents (out of scope, never asked for).
- `main.py` — FastAPI app: `POST /jobs` (in-memory job store, runs the loop via `BackgroundTasks`), `GET /jobs/{id}/status`. Reads `ODOO_URL`/`ODOO_DB`/`ODOO_USER`/`ODOO_PASSWORD`/`OLLAMA_BASE_URL`/`OLLAMA_API_KEY`/`LLM_MODEL`/`MAX_AGENT_ITERATIONS` - matched to the env var names M0 already put in `docker-compose.yml`, not renamed.
- `Dockerfile`, `requirements.txt`

**A real cross-container import bug caught and fixed before it shipped:**
the orchestrator needs `calc_engine` too (`calculate_emissions`,
`lookup_default_value`), but it runs in its own container **without Odoo
installed** - importing through `cbam.utils.calc_engine` would hit the same
`cbam/__init__.py → models → import odoo` chain that broke M2's tests
(see M2 section). Fixed the same way: `tools.py`/`odoo_client.py` import
`calc_engine` as a bare module. This only works if `calc_engine.py` is on
the container's path without going through `cbam/__init__.py`, so:
- `softworker/tests/conftest.py` now also adds `softworker/orchestrator` to `sys.path`, alongside the existing `cbam/utils` entry, so tests can `import agent_loop`, `tools`, etc. as bare modules too.
- `docker-compose.yml`'s `orchestrator` service build `context` changed from `./orchestrator` to `.` (softworker/), because the Dockerfile needs to `COPY addons/cbam/utils/calc_engine.py` in alongside the orchestrator's own files - a path outside the old, narrower build context. `dockerfile:` updated to `orchestrator/Dockerfile` to match.

**Loop skeleton actually implemented** (matches the plan's skeleton, with
tool-call messages reconstructed in OpenAI's expected format and tool
errors caught and fed back to the model instead of crashing the loop):
```python
for i in range(max_iterations):
    response = llm_client.chat(messages=messages, tools=tool_schemas)
    if not response.tool_calls:
        return AgentLoopResult(status="completed", ...)
    messages.append({"role": "assistant", "content": ..., "tool_calls": [...]})
    for call in response.tool_calls:
        try:
            result = execute_tool(call.name, call.args)
        except Exception as exc:
            result = {"error": str(exc)}
        messages.append({"role": "tool", "tool_call_id": call.id, ...})
        if call.name == "flag_for_human_review":
            return AgentLoopResult(status="escalated", ...)
# iteration cap reached -> loop itself calls flag_for_human_review as fallback
```

**Tests (all passing, real execution not just static checks):**
- `test_tools.py` (11) — each of the 7 tools, including that `lookup_default_value` propagates a not-found `ValueError` rather than swallowing it, and that `write_declaration_line` is the only handler touching the (fake) Odoo client's write path
- `test_agent_loop.py` (7) — no-tool-calls stops the loop; a tool call executes then the loop continues; **the model's arbitrary tool-call order within one turn is preserved, not reordered**; `flag_for_human_review` escalates immediately without running later calls in the same batch; iteration-cap exhaustion auto-escalates; a raised tool exception is fed back into the conversation instead of crashing; the reconstructed assistant/tool message shape is correct
- `test_llm_client.py` (3) — response parsing (content-only and tool-calls), and that `model`/`messages`/`tools` are actually passed through to the underlying client
- `test_main.py` (5) — schema loading returns all 7 wrapped in `{"type": "function", ...}`; job creation + background execution; status polling incl. 404; a missing required env var marks the job `failed` rather than crashing the process

**Process note:** `main.py` was written before its tests (the only file
this session didn't do strict red-green on) - the tests still assert real
behavior (no mock-testing-mocks), but I didn't watch them fail first for
that one file.

**Done:** `pytest softworker/tests/ -q` → 41 passed (15 M2 + 11 tools + 7 agent_loop + 3 llm_client + 5 main).

**Not done:** committed in `2d89d37`; no live LLM or Odoo was ever contacted; `SYSTEM_PROMPT` is a first draft, unrefined by any actual model behavior since M4 is blocked; in-memory job store has no persistence (acceptable for this academic scope, flagged as a known limitation).

**Correctness/security review (2026-07-31) — 3 real bugs found and fixed, all in `softworker/orchestrator/`:**
1. `odoo_client.py` `write_declaration_line()` called `model.create(data)`, always creating a brand-new, disconnected `cbam.declaration.line` instead of updating the job's own `declaration_line_id` (the line the source document is attached to and the one Odoo's UI reloads per this doc's own data-flow step 6). Fixed to `model.write([declaration_line_id], data)`, with `declaration_line_id` supplied from the job's own scope (`tools.py`), never from the LLM - same reasoning as the existing `declaration_id` check.
2. `tools.py` `ToolDispatcher` had no guard against `write_declaration_line` being called more than once in a job - `agent_loop.py` only treats `flag_for_human_review` as a loop terminator, so nothing stopped a non-converging model from writing twice, violating section 7's "single write... do not let the agent write mid-loop." Added a one-shot flag on the dispatcher (not tool-ordering logic - it doesn't constrain what runs before/after, only refuses to repeat the one side-effecting call).
3. `llm_client.py` did a bare `json.loads(call.function.arguments)` with no handling for malformed JSON - a real, expected failure mode for 7-8B models that this doc already anticipates for tool-calling generally. This raised `json.JSONDecodeError` straight out of `chat()`, uncaught by the tenacity retry (not a retryable error type) and uncaught by `agent_loop.py`, crashing the whole job instead of giving the model a chance to self-correct. Fixed to fall back to a placeholder args dict that Pydantic's existing `tool_args.py` validation rejects the same way it already rejects any other malformed tool call - fed back to the model as a tool error, not a crash.

Architectural compliance re-verified: the only tool-name branch in `agent_loop.py` is still the documented `flag_for_human_review` termination check; tool execution order within a turn is preserved (not resorted); Odoo stays read-only until the single write. 3 new/updated tests added (`test_tools.py` x2, `test_llm_client.py` x1); `pytest softworker/tests/ -q` → 70 passed after the fixes (no existing test's expectations changed).

---

### M7 — Versioned emission factor data load (mechanism built 2026-07-30, real data partially seeded 2026-09-08, commit `2a4deec`; fixture country/route redesign 2026-09-08, Task 9; `cbam_factor_year` resolved 2026-09-08, Task 11, commit `4923a9e`)

**What changed since the last pass:** the prior session's fetch tooling
failures (empty EUR-Lex fetches, a garbled JRC134682 text layer, no local
`poppler`) did not reproduce this time. This session had `pdftotext`
(poppler/xpdf) available, and downloaded the actual regulation PDFs
directly with `curl` (bypassing `WebFetch`'s 10 MB cap - the EUR-Lex PDFs
for these regulations run 1-41 MB) before extracting text locally with
`pdftotext -raw`. That produced clean, directly-quotable primary text for
three regulations, confirmed against the actual `ELI:` identifiers and
article text embedded in each PDF, not a paraphrase or secondary source.

**What got verified and seeded (real, cited data):**
- **EU ETS benchmarks** (`GOOD_BENCHMARK_SEEDS`): Commission Implementing
  Regulation (EU) 2026/1412 of 26 June 2026, Annex "BENCHMARKS", confirmed
  as the correct regulation number (its own text: "determining revised
  benchmark values for free allocation of emission allowances for the
  period from 2026 to 2030"). "Hot metal" row (used for CN 7208, steel) =
  1.248 t CO2e/t; "Aluminium" row (CN 7601) = 1.423 t CO2e/t, both
  "Benchmark value (allowances/t) for 2026-2030". This also resolves the
  earlier open question of whether aluminium has a dedicated benchmark or
  only the generic heat/fuel fallback - it has a dedicated one.
- **2026 markup rate** (`markup_pct` on all 5 `EMISSION_FACTOR_SEEDS`):
  Commission Implementing Regulation (EU) 2025/2621, Annex I - every
  country's steel section is headed "Iron and steel 10% mark-up 20%
  mark-up 30% mark-up" and every aluminium section "Aluminium 10%
  mark-up 20% mark-up 30% mark-up" (2026/2027/2028-onwards columns),
  confirmed identical across dozens of country blocks and in Annex IV.
  Sector-wide, not country- or route-specific, so it applies regardless
  of the direct_ef blockers below.

**Task 9 (2026-09-08, same day): fixture redesign - real country/route data
for 4 of the 5 `direct_ef` fields, plus the pricing gap resolved.** Task 6
had correctly found that France (x2), Norway, and the DRI/EAF route have no
real CBAM default-value data anywhere in the primary sources - but its
conclusion that Tunisia's aluminium data was *also* absent turned out to be
wrong (most likely an artifact of an anchored `grep '^Tunisia$'` against a
line with an extraction-mangled byte; a substring search finds it fine).
Task 9 re-fetched the same 41 MB IR 2025/2621 PDF (confirmed byte-identical
to Task 6's copy: 41,252,987 bytes, 135,102 extracted lines) and:
- Replaced the France/Norway pairings with real, populated, non-EU/non-EEA
  country/route combinations the regulation actually publishes CN 7208
  (steel) / CN 7601 (aluminium) default values for: **Turkiye** (BF-BOF,
  `direct_ef=2.428`), **Azerbaijan** (EAF_scrap, `direct_ef=0.140`), and
  **Bahrain** (primary_electrolysis, `direct_ef=1.870` - Bahrain is one of
  JRC134682's own 15-country aluminium scope and a real-world major
  primary-aluminium exporter).
- Re-read Tunisia's own country block in full and found it *does* carry a
  CN 7601 row tagged "(L) secondary Aluminium", `direct_ef=0.360` -
  confirming Tunisia was the right country all along for
  secondary_recycled; only Task 6's "no data" finding was wrong. (Tunisia
  still has zero steel/CN-72xx rows in this regulation, so the steel side
  of Task 6's Tunisia finding stands unchanged.)
- Resolved `reference_certificate_price` for 2026 as the average of the
  two 2026 quarterly CBAM certificate prices published so far: Q1 2026 =
  EUR 75.36, Q2 2026 = EUR 75.28 -> **EUR 75.32**. Re-verified directly
  against the raw HTML of the Commission's official price page as of
  2026-09-08 (this task's session date) - Q3 2026 (due 5 October 2026) and
  Q4 2026 (due 4 January 2027) table cells are still empty, genuinely not
  published yet. This is an explicit approximation, not a single official
  annual figure - the `source_document` citation names the exact quarters
  and values averaged so a future reader can see the approximation, not
  just trust a bare number.

**Task 11 (2026-09-08, same day): `cbam_factor_year` resolved, closing the
last easy gap.** Task 9's addendum had already surfaced the piece needed
here: commit `db50c1f` ("Fix inverted cbam_factor_year direction in
certificate calculation"), already on this branch before Task 9 started,
had changed `calc_engine.py`'s formula to `benchmark_deduction = benchmark
* (1 - cbam_factor_year) * quantity_tonnes` - which makes the codebase's
pre-existing `cbam_factor_year=0.025`-for-2026 convention directionally
correct again (the complement of Directive 2003/87/EC Art. 10a(1a)'s
literal 97.5%-for-2026 "CBAM factor" figure). Task 11 re-confirmed the
citation (re-quoted the Directive text, independently re-checked via a
fresh `WebSearch`, and re-read `calc_engine.py`'s current formula) and
filled in `cbam_factor_year=0.025` for 2026, with the record's
`source_document` now citing both fields directly instead of carrying
"unresolved" language. Full derivation: `docs/m7-source-verification.md`'s
"Task 11 addendum" section.

**What's still blocked, and why (evidence, not fetch failure) - down to 1
field after Task 11:**
- `direct_ef` for steel EAF_DRI/TR: IR 2025/2621's Annex I legend defines
  a "(D) Carbon Steel based on DRI/EAF" route indicator, but across the
  entire ~2,400-page Annex I it is attached to zero actual data rows for
  any country (confirmed by an exhaustive count, re-confirmed independently
  by Task 9 against a freshly re-fetched copy: `grep -cF "(D)"` = 2, both
  legend definitions) - Turkiye's own CN 7208 entry, and every other
  country's, uses "(C) BF/BOF" instead. JRC134682 gives Turkiye only one
  blended per-CN-code value, not a route-specific one (its own Step 3
  methodology text says route-decomposed figures exist only for the
  out-of-scope "weighted average", not named countries). This is not a
  per-country gap - no country anywhere in either source has DRI/EAF-route
  data, so there is no substitute country to swap in for this route.

**Known gap: `GoodBenchmarkSeed` has no route dimension, so two of the
newly-populated route/country pairings currently compute to exactly zero
certificates.** `GoodBenchmarkSeed` (`shared/data/seed_emission_factors.py`)
keys its benchmark only on `(cn_code, sector)`, not route, so the single
CN 7208 (steel) and CN 7601 (aluminium) benchmarks are applied uniformly to
every `EmissionFactorSeed` record for that CN code regardless of production
route. The CN 7601 benchmark specifically represents PRIMARY/electrolytic
aluminium production (per its source citation). This was flagged as a
caveat during Task 6 (before `secondary_recycled`'s `direct_ef` had any real
value to test it against) but never written down in any committed file.
Task 9 then filled in real `direct_ef` values for `steel EAF_scrap/AZ` and
`aluminium secondary_recycled/TN` - and running both through the current
(post-`db50c1f`) `calc_engine.py` for Q=100t shows the caveat's consequence
is real, not theoretical: **both pairings compute to exactly zero
certificates required** - `steel EAF_scrap/AZ` because the hot-metal
BF-BOF benchmark (1.248) is wrongly applied to a scrap-EAF route record, and
`aluminium secondary_recycled/TN` because the primary-aluminium benchmark
(1.423) is wrongly applied to a secondary/recycled route record. In both
cases the benchmark deduction overstates the free allocation the route
actually qualifies for, driving the certificate requirement down to the
formula's floor of zero. This is a data-model gap, not an arithmetic bug -
fixing it properly needs a route dimension added to `GoodBenchmarkSeed`
(a schema/design change), which is out of scope for this plan. Documented
inline in `shared/data/seed_emission_factors.py` (comments on both
`GoodBenchmarkSeed` records) and cross-referenced in
`docs/m7-source-verification.md`.

**Existing files, unchanged in shape:**
- `shared/data/seed_emission_factors.py` - typed seed tables (`EmissionFactorSeed`, `YearParameterSeed`, `GoodBenchmarkSeed` dataclasses). The one still-`None` field carries a comment citing the exact primary-source finding that blocks it (see above); every filled-in field carries a comment citing the exact source row it came from.
- `find_incomplete_seeds()` - lists every placeholder still outstanding; now returns 1 item (`steel/EAF_DRI/TR: direct_ef`) instead of the 2 it returned after Task 9.
- `seed_odoo(env, allow_incomplete=False)` - unchanged; still refuses to write to Odoo while that field remains `None`.
- `main()` - unchanged standalone CLI using `odoorpc`.
- `test_seed_emission_factors.py` (6 tests) - `test_find_incomplete_seeds_flags_exactly_the_still_blocked_fields` now asserts the exact 1-item list above instead of the 2-item Task 9 list; new test `test_year_parameter_2026_cbam_factor_year_is_no_longer_a_placeholder` asserts `cbam_factor_year` is a real fraction in `(0, 1)`.

**To actually finish this milestone:** the steel EAF_DRI route has no real
data to source from either primary source for any country, so finishing it
would mean either accepting a different steel route as the DRI/EAF slot's
stand-in (a modelling decision, not a data lookup) or leaving it
permanently blocked - this is the only remaining gap. Full fetch-by-fetch
record with exact quotes: `docs/m7-source-verification.md`.

---

### M8 — Security hardening (built/verified 2026-07-30, commit `2d89d37`)

- **8a - Odoo record rules:** `softworker/addons/cbam/security/cbam_security_rules.xml` (new) - `ir.rule` records scoping `cbam.declaration`, `cbam.declaration.line`, and `cbam.source.document` to `[('declarant_id', '=', user.partner_id.id)]` (and the equivalent traversal for the two child models) for `base.group_user` only; `base.group_system` is untouched by these rules and keeps the unrestricted access `ir.model.access.csv` already grants. Added to `__manifest__.py`'s `data` list. Not runtime-verified (same Odoo-instance caveat as M3).
- **8b - Pydantic tool-argument validation:** `softworker/orchestrator/tool_args.py` (new) - one Pydantic model per tool, mirroring `shared/tool_schemas/*.json` field-for-field (including the enums). `ToolDispatcher.execute()` now validates args through the matching model before calling the handler; a `ValidationError` becomes a `ValueError`, which `agent_loop.py` already catches and feeds back to the model as a tool error instead of crashing on a malformed call from a small model. 4 new tests added to `test_tools.py` (missing required arg, wrong type, invalid enum on two different tools) - all TDD'd (confirmed failing with `TypeError`/no-error before the validation existed).
- **8c - nginx rate limits / ACL:** reviewed, not rebuilt - M0 already has this right. `hardworker/nginx.conf.template` rejects any request without a matching `X-Api-Key` (401) and rate-limits at 10 r/s with a burst of 20. `tailscale-acl-example.json` restricts Softworker → Hardworker:8443 TCP only and has an explicit test asserting the reverse direction (A → B:8069/5432) is denied. `OLLAMA_BASE_URL` is documented as `http://` (not https) consistently in both nginx and `.env.example` - intentional, encryption is the Tailscale WireGuard tunnel's job, not an app-layer TLS cert nobody asked to manage.
- **8d - `.env` hygiene + secret rotation:** verified `git check-ignore -v hardworker/.env softworker/.env` - both match the root `.gitignore`'s `*.env` pattern. Verified `git log --all --full-history -- '*.env'` returns nothing - no `.env` file has ever been committed. Wrote `docs/secret-rotation.md`: rotation steps for `OLLAMA_API_KEY`, `TS_AUTHKEY`, `POSTGRES_PASSWORD`, `ODOO_PASSWORD`, plus a periodic check for accidental force-adds.

**Done:** `pytest softworker/tests/test_tools.py -v` → all pass (15, incl. the 4 new ones); `.env`/git history checks passed with real commands, not assumed.

---

### M9 — Evaluation (harness built 2026-07-30, real run BLOCKED on M4)

**Why blocked:** the actual deliverable ("run 20 synthetic records through
the agent loop, report accuracy") needs a real LLM in the loop. M4 being
blocked means there is no real Ollama endpoint to run this against. I did
**not** fabricate evaluation numbers - there is no `docs/evaluation.md` in
this repo, and there shouldn't be until this has actually run against a
real model. Presenting invented accuracy figures as if measured would be
exactly the kind of thing this project's jury would (rightly) not forgive.

**What got built instead:**
- `shared/evaluation/scoring.py` - `score_record(ground_truth, written)` (per-field bool match against M1's ground truth, skipping fields that are `null` in ground truth rather than than counting them as a miss) and `aggregate_field_scores(...)` (per-field correct/total/accuracy across records). 6 tests, fully TDD'd, no infra dependency.
- `shared/evaluation/run_evaluation.py` - `load_synthetic_records()` (reads real files from `shared/synthetic_data/output/`), `run_evaluation_on_record()` / `run_evaluation()` (drives the **real** `agent_loop.run_agent_loop()` and `tools.ToolDispatcher` from M6, with an injectable LLM client so a real one drops in once M4 unblocks), `build_report_markdown()` (status breakdown, iteration distribution, per-field accuracy, error list).
- `test_run_evaluation.py` (4 tests) - one of them (`test_run_evaluation_on_record_scores_a_correct_completion`) loads an actual file from `shared/synthetic_data/output/` and drives it through the real M6 loop with only the LLM responses scripted - a genuine integration smoke test proving the M1→M6→M9 wiring works end to end, not just unit isolation. This is the mechanism-verification step you asked for; it is explicitly not a real evaluation and `build_report_markdown()`'s output from this test must never be quoted as one.

**To actually finish this milestone:** once M4 produces a working
`LLMClient` pointed at a real Ollama endpoint, and M7 has real emission
factor data seeded (needed for any `data_source=default` record to resolve
`lookup_default_value` correctly), run `run_evaluation()` over
`load_synthetic_records(..., limit=20)` for real and write the results to
`docs/evaluation.md`.

**Done:** `pytest shared/evaluation/ -v` → 10 passed (6 scoring + 4 harness).

---

## Full-codebase verification & bug-fix pass (2026-07-31)

With M0-M9 built but never exercised end-to-end (M4 still blocked on real
hardware), this pass reviewed every module against `projecthandoff.md` and
this doc, ran every test suite, and fixed everything that could be fixed
without live Odoo/Ollama/Docker infrastructure. No milestone status above
changes (M4 is still the only real blocker), but several bugs that would
only have surfaced once M4 unblocked and the system ran for real are fixed
now instead.

**Compliance-correctness (`calc_engine.py`, Odoo models):**
- `calculate_embedded_emissions` was pricing `indirect_ef` into SEE for
  steel/aluminium, contradicting this doc's own "Key Constraints" line below
  ("direct emissions only — Annex II"). Confirmed against
  `CBAM_Formulas_Steel_Aluminium.md` §1.2's explicit steel/aluminium
  override and fixed: only `direct_ef` (with markup) is priced now.
- `calculate_certificates_required`'s carbon-price deduction fraction was
  floored at nothing, only capped at 1.0 — a negative
  `carbon_price_paid_origin` could inflate certificates owed instead of
  reducing them. Floored at 0.0.
- `cbam_declaration_line.py`'s `certificates_required` looked up
  `cbam.year.parameter` via an untracked `search()` inside the compute
  method, so editing an existing year-parameter record wouldn't trigger
  recompute. Added a real stored `year_parameter_id` field with correct
  `@api.depends`.
- Added `ondelete="restrict"` to 5 required Many2one fields that had none.
- Added `_check_sector_consistency` — nothing previously stopped a line
  pairing a steel good with an aluminium installation (each sector lives on
  its own unrelated Selection field); now raises a `ValidationError`.

**Orchestrator (`softworker/orchestrator/`):** see the M6 section above for
the 3 bugs fixed there (orphan-record write, missing single-write guard,
crash on malformed LLM tool-call JSON). Additionally, `MAX_AGENT_ITERATIONS`
is now clamped to `[8, 10]` in `main.py` regardless of env misconfiguration,
matching section 7's "hard iteration cap (8-10 loops)" exactly instead of
trusting the env var unclamped. `ORCHESTRATOR_API_KEY` enforcement
(fail-closed, constant-time comparison, checked on both endpoints) was
reviewed and found already correct — no change needed.

**Infra (`hardworker/`, `softworker/docker-compose.yml`, Dockerfile):** 3
deployment-breaking bugs fixed — the nginx template's invalid nested
`http`/`events` blocks (nginx would refuse to start), the missing
`OLLAMA_API_KEY` in the nginx container's own environment (the key check
was unsatisfiable by any caller), and the Tailscale sidecar missing the
`internal` Docker network (Postgres was structurally unreachable from
Odoo). Also added a non-root Dockerfile user and a `.dockerignore`.

**Cross-module contracts:** `lookup_default_value`'s tool result never
actually included `emission_factor_id`, even though
`write_declaration_line.json` documents it as required when
`data_source=default` and `tool_args.py`'s own validator enforces that —
the "use a default emission factor" write path was structurally uncallable
end to end. Fixed by threading the Odoo/RPC record id through
`EmissionFactor` and into the tool's return dict. Also fixed
`seed_emission_factors.py`'s benchmark seeding, which matched `cbam.good`
by `cn_code` alone despite `cbam_good.py`'s own `unique(cn_code, sector)`
constraint — could bleed a benchmark across sectors sharing a CN code.

**Synthetic data generator (`shared/synthetic_data/generator.py`):**
- Crashed outright on Windows (`write_text` with no explicit encoding hit
  the cp1252 fallback against the generator's own Unicode box-drawing
  characters). Fixed with explicit `encoding="utf-8"` throughout.
- 3 internal-consistency bugs where ground truth claimed a field was
  present/extractable that the generated document text never actually
  contained (mill-certificate fields wrongly gated together, carbon
  intensity reports never stating quantity at all, customs declarations
  never carrying emissions data without being flagged as
  `missing_fields`). All fixed.
- `record_id` was built from `uuid.uuid4()`, ignoring `--seed` entirely —
  re-running the documented reproducible-seed command
  (`python generator.py --count 50 --seed 42 --outdir output/`) silently
  accumulated a second copy of every record under new filenames instead of
  reproducing the same output. Fixed to derive the id from the seeded rng;
  verified a repeat run with the same seed now produces byte-identical
  output. `output/` was regenerated with the fixed generator (was stale
  relative to the 3 consistency fixes above).
- `shared/evaluation/scoring.py`'s `_values_match()` raised `TypeError` on
  a type-mismatched ground-truth/written pair instead of coercing or
  returning `False` — fixed to coerce with a `try/except` fallback to `False`.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 108
passed (was 103 before this pass; net +5 from new regression tests, no
existing test's expected values needed changing). All `.py` files compile,
all `.xml` files parse. All Odoo-model-layer fixes remain
statically-verified only (see M3's caveat — still no live Odoo instance
available in this environment).

**Deliberately left as-is (flagged, not bugs):** unpinned
`requirements.txt`/`:latest` image tags (matches section 10's package list
exactly, judgment call to leave until a real deployment picks concrete
versions); `main.py`'s in-memory job dict has no explicit lock (safe today
under CPython's GIL since each background task only touches its own uuid
key); nginx's plain-HTTP listener on 8443 (intentional — the Tailscale
WireGuard tunnel is the encryption layer, documented in M8c).

---

## Live infra verification pass (2026-09-06)

M0-M9 were built and unit-tested in a prior dev sandbox with no Docker, no
GPU, and no Ollama, so M4, the live half of M3, the live half of M6, and the
real run of M9 had never been exercised against real infrastructure. This
pass ran on a different machine with Docker Desktop, a native `ollama`
install, and an NVIDIA RTX 5070 (12GB VRAM), and got real, non-mocked
evidence for all four. M7 (real emission-factor numbers) stayed explicitly
out of scope — a primary-source research task, not an infra task.

**Machine topology deviation:** the decided architecture is two Tailscale-
meshed machines (Hardworker running Ollama+nginx, Softworker running
Odoo+orchestrator). This machine has no Tailscale install and the intended
Softworker was not reachable this session, so standing up the real
cross-machine mesh was out of scope here. Instead, `docker-compose.local-dev.yml`
(new, committed, clearly header-labeled as dev-only) runs everything on this
one host — Ollama + nginx (reusing `hardworker/nginx.conf.template`
byte-for-byte) + Postgres + Odoo + orchestrator — reaching each other over
`localhost` with no Tailscale sidecar. `hardworker/docker-compose.yml` /
`softworker/docker-compose.yml` are unmodified and remain the real deployment
topology for when Softworker is available. Full rationale in
`docs/superpowers/specs/2026-09-06-m4-live-infra-design.md`'s "Non-goals" and
"Approach" sections. A follow-up session (Task 7, 2026-09-08) attempted to
close this deviation but found Tailscale still not installed on the
available host; the human partner chose to defer real-mesh verification
rather than provision it now, leaving the local-dev stand-in as the tested
topology until that changes.

**M4 — real model benchmark (commit `9d4851a`):** 4 candidate models
benchmarked for real against a live local `ollama serve`, 10 tool-calling
attempts each, scored against the exact production Pydantic validation in
`softworker/orchestrator/tool_args.py`. Winner: `llama3.1:8b` (the real Ollama
tag — `llama3.1:8b-instruct` from the original plan doesn't exist as a
published tag) at 50% valid-rate, ahead of `qwen2.5:7b-instruct` (40%),
`qwen3:8b` (0%), and `qwen2.5:14b-instruct` (0%, both zero-scores from
emitting multiple tool calls per turn rather than the one this benchmark
scores). Full methodology and numbers: `docs/model-benchmark.md`. The nginx
gate — `hardworker/nginx.conf.template`, reused byte-for-byte by the
`docker-compose.local-dev.yml` stack described above (no Tailscale sidecar
on this host, so the real `hardworker/docker-compose.yml` topology itself was
not brought up) — was then verified for real: wrong `X-Api-Key` → 401,
correct key → 200 with the real Ollama model list.

**M3 — real Odoo install (commit `6a2e1b4`):** the `cbam` module installed
cleanly via `button_immediate_install()` against a real Postgres 16 + Odoo
17 container on the first try — no addon changes needed, resolving M3's
long-standing "not runtime-verified" caveat. One real bug was found and
fixed, in the fixture-seeding script rather than the addon itself:
odoorpc's JSON-RPC transport can't serialize a raw `datetime.date` the way
Odoo's XML-RPC/in-process ORM can, so `shared/data/dev_fixtures.py` now
sends `VALID_FROM.isoformat()` over the wire.

**Orchestrator context gap fix (Task 5, commit `58e404c`):** added
`OdooClient.get_declaration_line_context()` and wired it into the
orchestrator's initial user prompt, so the agent loop starts each job
knowing the declaration line's existing good/installation/production-route
context instead of having to (re)discover it via tool calls.

**M6 — real end-to-end run (commit `b1a7d17`):** the first ever live
LLM+Odoo run for this project. Final job status: `completed`
(`llama3.1:8b` called `calculate_emissions` with all-zero inputs instead of
extracting fields first, then stopped without calling
`write_declaration_line` — a documented model tool-calling limitation
consistent with M9's real evaluation, not a new harness bug). This live run
surfaced and fixed 3 real bugs invisible to the mocked test suite: (1)
`OLLAMA_BASE_URL` needed an explicit `/v1` suffix for the `openai` SDK to
resolve against Ollama's OpenAI-compatible endpoint; (2) `llm_client.py`
needed an explicit `X-Api-Key` header since the `openai` SDK only ever sends
`Authorization: Bearer`, which the nginx gate ignores; (3)
`cbam_security_rules.xml`'s declarant-scoping rule wrongly restricted
managers too, because Odoo's `base.group_system` implies
`base.group_user` membership with no competing permissive rule for the
former — fixed with explicit manager-unrestricted `ir.rule` records. Full
trace and evidence: `docs/m6-live-verification.md`.

**M9 — real evaluation (commit `ceaf01c`):** `run_evaluation()` executed for
real against 20 synthetic records with `llama3.1:8b` as the LLM client.
17/20 jobs completed, 3/20 escalated; every scored field came back at 0%
accuracy. Root cause: per the iteration-count distribution recorded in
`docs/evaluation.md` (1 record at 1 iteration, 12 at 2, 5 at 3, 2 at 4) and
the 3 records that reached `escalated` (which requires a real
`flag_for_human_review` tool call), `llama3.1:8b` does successfully make
structured tool calls in the large majority of records — it just never
completes the full call sequence needed to reach `write_declaration_line`,
the one tool that actually records a result, consistent with the
all-zero-argument `calculate_emissions` call-then-stop pattern captured live
in M6 above. This is a real model capability/prompting limitation, not
evidence the model can't call tools at all, and not a harness bug
(`agent_loop.py`'s escalation-on-no-progress path is working as designed;
`agent_loop.py`, `tools.py`, and `tool_args.py` needed no changes). Full
report: `docs/evaluation.md`.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 122
passed (unchanged from the count recorded in `b1a7d17`; no existing test's
expectations changed as part of this pass).

---

## Agentic completion-gap follow-up (2026-09-08)

Direct follow-up to M6/M9 above's finding — "the model calls tools but
never reaches `write_declaration_line`". The fix is text-only: the
orchestrator's `SYSTEM_PROMPT` (`softworker/orchestrator/main.py`) now states
explicitly that the task is not finished until `write_declaration_line` has
been called, tells the model to call `flag_for_human_review` rather than
just stopping when it can't converge, and tells it to gather real values via
`extract_field`/`lookup_default_value` before calling `calculate_emissions`
rather than passing placeholder/zero values. `write_declaration_line.json`'s
schema `description` gained one sentence stating the same completion signal
at the tool-schema level. Per this task's own constraint,
`agent_loop.py` and `tools.py` were not touched — confirmed with `git diff
--stat softworker/orchestrator/agent_loop.py softworker/orchestrator/tools.py`
returning empty output before committing (commit `dfe14c2`).

**Re-running M6 (`docs/m6-live-verification.md`, overwritten by this pass):**
the same synthetic record (`SYNTH-0000-B286B5`, steel/BF-BOF/EG) now drives
the model through 6 real tool-call iterations — `check_consistency`,
several corrected attempts at `extract_field`/`lookup_default_value` (two of
which the model first called with wrong/missing arguments and self-corrected
after real Pydantic validation errors came back), then a real
`lookup_default_value` miss (the model looked up `aluminium/EAF_scrap`
instead of the actual `steel/BF-BOF` context — a separate field-grounding
bug, not the completion gap this task targets), and finally a genuine
`flag_for_human_review` call. Final job status: `escalated`, exit code 0.
This is a real behavior change from the prior silent-stop finding (then
mislabelled `completed`, now classified `no_write`): the model now reaches
an actual terminal state via a real tool call instead of just stopping
mid-loop.

**First M9 re-run (`docs/evaluation-prompt-v2-2026-09-08.md`, 20 records,
`llama3.1:8b`, through the real nginx gate at `localhost:8443`):**

| | completed | escalated | field accuracy (all 6 fields) |
|---|---|---|---|
| Before (`docs/evaluation.md`) | 17/20 | 3/20 | 0% |
| After (`docs/evaluation-prompt-v2-2026-09-08.md`) | 13/20 | 7/20 | 0% |

Reported exactly as measured, with no rounding either direction: completions
went down and escalations went up, and per-field accuracy is unchanged at
0% across all 6 scored fields in both runs.

**Bug found in this first re-run:** `shared/evaluation/run_evaluation.py`
defined its own separate, shorter `SYSTEM_PROMPT` constant, never imported
from `softworker/orchestrator/main.py`. This meant the first M9 re-run above
never actually exercised this task's `SYSTEM_PROMPT` strengthening — only
the `write_declaration_line.json` schema-description change was in effect
for that run. The M6 re-run above was, until the fix below, the only real
evidence of the `SYSTEM_PROMPT` change's effect.

**Fix:** `run_evaluation.py`'s local `SYSTEM_PROMPT` definition was deleted
and replaced with `from main import SYSTEM_PROMPT` (the orchestrator
directory is already on `sys.path` for both pytest, via
`shared/evaluation/conftest.py`, and the standalone
`run_real_evaluation.py` script, via its own bootstrap). `main.py`'s
module-level code has no env-var requirements at import time, so the import
is safe in both contexts. No test in `shared/evaluation/test_run_evaluation.py`
or `test_run_real_evaluation.py` asserted on the old local prompt text.
Verified with a standalone import check that `run_evaluation.SYSTEM_PROMPT`
now is the real, strengthened `main.py` prompt (contains both
`write_declaration_line` and `not finished`). This duplication bug cannot
recur now that the prompt is unified at the source. Full test suite
re-verified at 127 passed after this change, no regressions.

**Second M9 re-run (`docs/evaluation-prompt-v2b-2026-09-08.md`, 20 records,
`llama3.1:8b`, same infra, now with the real unified `SYSTEM_PROMPT` in
effect) — this is the valid comparison against the original baseline:**

| | completed | escalated | exhausted | field accuracy (all 6 fields) |
|---|---|---|---|---|
| Original baseline (`docs/evaluation.md`) | 17/20 | 3/20 | 0/20 | 0% |
| v2b, unified prompt (`docs/evaluation-prompt-v2b-2026-09-08.md`) | 15/20 | 1/20 | 4/20 | 0% |

Reported exactly as measured. Per-field accuracy is still 0% across all 6
scored fields — the `SYSTEM_PROMPT`/schema strengthening did not move the
field-accuracy needle at all, with the real unified prompt now genuinely in
effect. The status breakdown also picked up a status not seen in the
original baseline or the first (buggy) re-run: `exhausted` (4/20) — the
model used all available iterations without reaching a terminal
`write_declaration_line` or `flag_for_human_review` call, consistent with
the more thorough (and therefore longer) tool-use sequences the
strengthened prompt now asks for (iteration counts in this run ranged up to
9, versus a max of 4 in the original baseline). This is a genuine, if
mixed, result: the model engages more (matching the M6 finding above of
real multi-step tool use replacing silent stops), but that extra engagement
does not yet reliably end in a recorded declaration line, and never once
produces an accurate field value in either run. Consistent with this task's
own framing: the tool-completion *gap* (silent stop with nothing recorded)
is fixed per the M6 evidence, but the field-*accuracy* gap is a distinct,
unaddressed problem that prompting alone did not close — pointing back to
M4's original finding that `llama3.1:8b` itself may be the binding
constraint, not the prompt text.

An interim run at the same output path was affected mid-flight by an
unrelated Docker Desktop daemon health incident (the daemon's control plane
returned intermittent 500s while troubleshooting infra for this task;
`LLMClient`'s built-in retry logic appears to have ridden through it, since
that run completed cleanly once the daemon was restarted and the stack was
brought back up) — that run's file was discarded in favor of the clean
second re-run above, run entirely after Docker's health was independently
confirmed, to remove any doubt about its numbers.

**Infra note:** the `docker-compose.local-dev.yml` stack from the September
6 pass ran in a worktree (`m4-live-infra`) since deleted, so `.env.local-dev`
and all three named volumes (Ollama models, Postgres data, Odoo data) had to
be recreated from scratch in this worktree — fresh random secrets, a fresh
`ollama pull llama3.1:8b` (4.9GB), and a fresh `scripts/init_local_dev_odoo.py`
run (new `cbam` database, module install, seeded fixtures) before Step 9's
smoke test had anything to work with. None of this touched repo state.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 127 passed
(125 + the 2 new regression tests from this task's Step 1; no existing
test's expectations changed; unchanged after the `run_evaluation.py` prompt-
unification fix).

---

## Independent audit + follow-up fixes (2026-09-08)

A separate session ran an adversarial, from-scratch audit of the whole
codebase (three parallel reviews covering the calc/Odoo layer, the
orchestrator agent loop, and infra/security/hygiene) without trusting this
doc's own claims first. Verdict: 8/10 - the "zero business logic in the
orchestrator" and "0% field accuracy" claims both held up under line-by-line
adversarial review, no committed secrets, and the M7 "known gaps" already
documented above matched the code exactly. Full findings led to these
follow-ups, all applied and tested (`python -m pytest softworker/tests/
shared/ -q` → 130 passed):

**Dependency pinning + repo hygiene:** all Docker image tags
(`tailscale/tailscale`, `ollama/ollama`, `nginx`, `postgres`, `odoo` across
`hardworker/docker-compose.yml`, `softworker/docker-compose.yml`,
`docker-compose.local-dev.yml`) and all three `requirements*.txt` files
pinned to specific, verified-current versions (previously `:latest`/
unpinned - a real reproducibility risk for an academic project graded
later). Root `README.md` added (previously only `projecthandoff.md`/this
file existed, no entry point for a first-time reader). `cbam_declaration_
line.py`'s `action_lookup_emission_factor` now has an inline comment
explaining the Jan-1-of-reporting-year date assumption.

**`GoodBenchmarkSeed` route-dimension fix (the concrete M7 caveat above):**
`cbam.good.benchmark` is now its own Odoo model
(`softworker/addons/cbam/models/cbam_good_benchmark.py`), keyed on
`(good_id, production_route_id)` instead of a flat `benchmark` field on
`cbam.good` keyed only by `(cn_code, sector)`. `cbam_declaration_line.py`
gained a stored `good_benchmark_id` compute (same `@api.depends`-tracking
pattern as `year_parameter_id`) that resolves the benchmark by the line's
actual installation route, not just its good - fixing the exact bug
described above where the BF-BOF "Hot metal" benchmark was silently applied
to the `steel EAF_scrap/AZ` record and the primary-aluminium benchmark to
`aluminium secondary_recycled/TN`, zeroing out both. The real benchmark
VALUES for those two routes were **not** re-verified against a primary
source this session (that's separate research work, same category as
Task 6/9/11's emission-factor fetches) - both are honestly left `None`/
BLOCKED in `shared/data/seed_emission_factors.py` rather than guessed,
so `find_incomplete_seeds()` now returns 3 items instead of 1 (steel
EAF_DRI direct_ef, steel EAF_scrap benchmark, aluminium secondary_recycled
benchmark). `shared/data/dev_fixtures.py` updated to match (arbitrary dev
numbers, `DEV_GOOD_BENCHMARK_FIXTURES`, still clearly labeled fake).

**`certificates_status` field (the exempt-vs-incomplete ambiguity noted
above):** `cbam.declaration.line` gained a `certificates_status` Selection
(`computed`/`exempt`/`incomplete`), computed alongside `certificates_required`
in the same method, so a genuinely exempt line (< 50 t/year) is no longer
visually identical in the UI/PDF report to one that's 0.0 only because a
year parameter or route-specific benchmark hasn't been seeded yet. Surfaced
in both declaration-line views and the QWeb report.

**`write_declaration_line` schema/validation drift:** `tool_args.py`'s
`WriteDeclarationLineArgs` only validated "`emission_factor_id` required
when `data_source=default`"; the schema's own description also promises
"must be omitted/null when `data_source=actual`", which nothing enforced.
Added the missing direction plus a regression test
(`test_write_declaration_line_rejects_emission_factor_id_for_actual_source`
in `softworker/tests/test_tools.py`).

**Not done, deliberately out of scope for this pass:** the model's 0%
field-accuracy problem itself (the audit's highest-priority open item) -
needs either a stronger/larger model benchmarked against the same M9
harness, or real prompt/grounding work on `extract_field`, both of which
are a separate, larger effort the human partner asked to scope separately.

---

## Field-accuracy root-cause investigation (2026-09-08, same day)

Follow-up to the "not done" item directly above - the human partner asked
to scope it after all. Ran on a machine that turned out to already have
the live infra up (Docker Desktop, an RTX 5070, and the
`docker-compose.local-dev.yml` stack from a prior session still running,
project name `project-completion`, `llama3.1:8b` loaded) - real evidence,
not a cold-start guess.

**First real finding, from the live Odoo database, not a fresh run:**
`cbam_source_document.raw_llm_output` on the one existing record (the M6
re-run trace from the "Agentic completion-gap follow-up" section above)
showed the model calling `lookup_default_value(sector="good_sector",
route="production_route", country="installation_country", ...)` - passing
the literal JSON *key names* from the "Known context" object as if they
were the values, and never once calling `extract_field` successfully
(missing/wrong argument names, and - separately - no `document_id` was
ever available anywhere in the prompt for it to use even if it had
guessed the right argument shape). Two concrete, structural bugs, not a
vague "model isn't good enough":

1. `main.py`'s `get_declaration_line_context()` (via `odoo_client.py`) never
   included the line's `source_document_ids` - `extract_field` requires a
   `document_id`, and nothing in the prompt ever gave the model one to use.
2. `SYSTEM_PROMPT` never told the model to substitute actual context
   *values* into tool arguments rather than the JSON *keys* it saw.

Both fixed: `odoo_client.py` now includes `source_document_ids` (id +
filename) in the context; `SYSTEM_PROMPT` gained an explicit worked example
("if the context contains `"good_sector": "steel"` ... pass `"steel"`,
never pass the literal text `"good_sector"`"). `test_odoo_client.py` and
`test_get_declaration_line_context_reads_nested_fields` updated to match.

**Second finding: the M9 harness itself (`run_evaluation.py`) was a
different, inconsistent code path from production**, and is the thing that
actually produced every `docs/evaluation*.md` number to date. It dumped the
full document text directly into the user message - bypassing
`extract_field` entirely - while `SYSTEM_PROMPT` still told the model it
*must* use `extract_field` first, and (like production) never supplied a
`document_id` either. Fixed to build the same "known context" JSON shape as
`main.py`'s real flow, with a `document_id` the model can legally use.
Also added `good_sector`/`installation_country`/`production_route` to that
context - genuinely pre-known in real production (fixed properties of the
good/installation records, never extracted from a document there either)
and not in `scoring.py`'s `SCORED_FIELDS`, so this doesn't leak anything
the evaluation measures; a live trace without them showed the model trying
`extract_field(field_name="sector", ...)`, which was never a valid enum
option, then giving up instead of retrying. `quantity_tonnes`/`data_source`
were deliberately left as genuine extraction targets (not moved into
context) so the harness still exercises `extract_field`'s real job, even
though this doesn't perfectly match production's task boundary for those
two fields specifically - noted inline in `run_evaluation.py`, not silently
decided away. New regression test:
`test_run_evaluation_on_record_gives_the_model_a_document_id_to_extract_with`.

**Live verification of the mechanism fix (not just the code):** a
single-record traced run (ad hoc script, not committed - see the trace
excerpt below) confirmed `extract_field` now genuinely succeeds end to end
for the first time - the model called `extract_field(document_id="1",
field_name="quantity_tonnes")` and got back the real document text ("Quantity
covered : 41880.0 kg", correctly a kg-not-tonnes medium-difficulty case per
M1's generator design). This is real, working proof the context/grounding
bugs above are fixed, not a hypothesis.

**But the remaining failure mode is a genuine model capability ceiling, not
another bug to fix:** in that same trace, immediately after the successful
extraction, the model went on to fail almost every subsequent multi-argument
tool call by dropping exactly one required field each time -
`lookup_default_value` (needs `sector`+`route`+`country`) was attempted 3
times, each missing at least one of the three despite all three being
present verbatim in the context it had just been given; `calculate_emissions`
was called with invented argument names (`quantity`/`emission_factors`)
that don't exist in the schema; `write_declaration_line` similarly invented
names (`emissions_tonnes`) and omitted required fields; even the final
`flag_for_human_review` call omitted its one required `reason` field. This
matches, and now much more concretely evidences, M4's original benchmark
finding that `llama3.1:8b` - the *winner* among 4 candidates tested - only
achieves a 50% valid-tool-call rate. The mechanism-level bugs (context
grounding, document_id availability, harness fidelity) are fixed and
verified; the remaining gap is the model's own reliability at constructing
correct multi-field JSON, which prompting cannot fully close.

**Final honest number, both fixes in effect** (`docs/evaluation-post-audit-
fix-2026-09-08.md`, live `llama3.1:8b`, 6 records - reduced from the usual
20 because this machine had only ~1.5 GB of ~16 GB RAM free with Docker
Desktop's WSL2 VM already using ~6.8 GB, and the first full-20 attempt was
killed by the OS for low memory):

| | completed | escalated | exhausted | field accuracy (6 fields) |
|---|---|---|---|---|
| Original baseline (`docs/evaluation.md`, 20 records) | 17/20 | 3/20 | 0/20 | 0% |
| Post-fix (`docs/evaluation-post-audit-fix-2026-09-08.md`, 6 records) | 4/6 | 1/6 | 1/6 | 0% |

Still 0% - reported exactly as measured, not softened. The fixes are real
and independently verified (the trace above), but they only unblock the
*mechanism*; they don't and can't raise `llama3.1:8b`'s own multi-argument
tool-calling reliability. **Recommendation, not yet acted on:** benchmark a
different/larger model against this now-fixed harness before concluding
further prompt engineering is worthwhile - this environment's GPU (RTX
5070, 12GB VRAM) already ruled out `qwen2.5:14b-instruct` and `qwen3:8b` at
0% valid-call rate in M4's original benchmark, so the next real experiment
needs either a model M4 didn't try, or accepting `llama3.1:8b`'s ceiling
and reframing the academic contribution around the harness/methodology
itself rather than a working extractor - a real, defensible finding either
way, but a decision for the human partner, not one to make silently here.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 131
passed (130 + 1 new regression test); no existing test's expectations
changed.

---

## MVP-focused follow-up: shrink the tool surface to what the model actually decides (2026-09-08, same day)

Direct continuation of the section above, at the human partner's explicit
request ("I want a working MVP as soon as possible"). The prior section's
recommendation was "benchmark a different model or reframe the
contribution" - this section takes a third path that turned out to work:
reduce how much correct JSON the small model has to construct in the first
place, since every live trace so far showed it failing by dropping exactly
one of several required fields, never by being fundamentally unable to
reason about the task.

**The insight:** `lookup_default_value`'s `sector`/`route`/`country` and
`write_declaration_line`'s `declaration_id`/`good_id`/`installation_id`/
`quantity_tonnes`/`data_source` are not things the model extracts or
decides - they're deterministic facts the orchestrator already has (the
same "Known context" JSON already shown to the model). Asking the model to
correctly copy 3-5 of them into every multi-argument tool call, when a real
trace showed it reliably dropping one, was pure unforced failure surface.

**Changes:**
- `tools.py`: `ToolDispatcher` takes a new `known_context` param (the same
  dict `main.py`/`run_evaluation.py` already build). `execute()` now
  injects these fields directly into `lookup_default_value`/
  `write_declaration_line` calls, unconditionally overriding whatever
  (if anything) the model supplied - not merely filling gaps. This also
  makes a cross-declaration write via a hallucinated `declaration_id`
  structurally impossible rather than just detected-and-rejected; the old
  `_write_declaration_line` mismatch check is now dead code and was
  removed, with `test_write_declaration_line_rejects_declaration_id_mismatch`
  replaced by `test_write_declaration_line_ignores_a_mismatched_declaration_id`
  asserting the stronger property. Two new regression tests cover the
  injection itself.
- `shared/tool_schemas/lookup_default_value.json`: now takes **zero**
  arguments - description explains why. `write_declaration_line.json`:
  dropped from 5 required fields to 0; the model now only ever needs to
  supply the fields it actually determines (`direct_emissions_actual`/
  `indirect_emissions_actual`/`emission_factor_id`/
  `carbon_price_paid_origin`/`precursor_emissions`).
  `test_tool_schemas.py`'s `EXPECTED_SCHEMAS` updated with an explanatory
  comment - it now documents "fields the model must supply", not "every
  field the handler needs".
- `main.py`/`run_evaluation.py`: both now pass their existing `line_context`
  dict straight into `ToolDispatcher(known_context=...)`. The harness's
  `line_context` also gained `quantity_tonnes`/`data_source` (sourced from
  ground truth) to match, since the schema no longer lets the model supply
  them at all - **consequence, stated plainly**: those two fields'
  `SCORED_FIELDS` accuracy is now a trivial pass-through in the harness,
  not a real extraction test, exactly mirroring the fact that real
  production doesn't ask the model to extract them either.
- `SYSTEM_PROMPT`: the old "copy real values, not key names" example (keyed
  on `lookup_default_value`'s now-removed `sector` argument) replaced with
  a direct statement that these fields are automatic and the model must
  not try to supply or look them up.
- **A separate, genuinely independent bug found while live-tracing this
  fix**: `shared/data/dev_fixtures.py`'s `build_emission_factor_session()`
  built every `EmissionFactor` fixture without an `id` (defaulting to
  `None`, per the dataclass's own documented default "for hand-built test
  fixtures"). `WriteDeclarationLineArgs` requires a non-`None`
  `emission_factor_id` whenever `data_source == "default"` - meaning
  **every** `data_source="default"` record in every M9 evaluation run to
  date (a majority of the synthetic dataset) was structurally unable to
  complete a write, regardless of model quality, model fixes, or prompt
  engineering. Fixed: each dev fixture now carries a stable integer `id`,
  threaded into `build_emission_factor_session()`. New regression test:
  `test_build_emission_factor_session_resolves_a_real_emission_factor_id`.

**Live-verified impact - genuinely different behavior, not just fewer
validation errors:** a traced single-record run (`data_source="default"`)
showed `lookup_default_value` called with garbled, irrelevant arguments
(`{"document_id": 1, "filename": "..."}` - the model still fumbles the
JSON shape) yet **succeed anyway**, returning correct real emission-factor
data, because the schema takes no arguments and the dispatcher supplies
everything - the first clean `lookup_default_value` success traced in this
project's history. The model then correctly called `calculate_emissions`
with the right `quantity_tonnes`/`direct_ef`/`markup_pct` copied from
context and the lookup result, computing `96.7428 t CO2e` correctly. (That
particular run still didn't reach `write_declaration_line` - it called
`flag_for_human_review` with the wrong argument name instead, a remaining
real model-reliability gap, not one this fix targets.)

**Final honest number, all three fixes together**
(`docs/evaluation-mvp-fixes-2026-09-08.md`, live `llama3.1:8b`, 6 records -
still reduced from 20 for the same memory-constraint reason as the section
above):

| | completed | escalated/exhausted | quantity_tonnes / data_source / carbon_price / precursor | direct/indirect emissions actual |
|---|---|---|---|---|
| Field-accuracy investigation (previous section) | 4/6 | 2/6 | 0% | 0% |
| MVP fixes (this section) | **6/6** | **0/6** | **33% (2/6)** | 0% (0/4) |

This is the first non-zero field accuracy this project has ever measured
against a real model - not a rounding artifact: 2 of the 6 records now
produce a genuinely correct, complete, end-to-end declaration-line write
(quantity/data_source/carbon-price/precursor all matching ground truth
simultaneously on those 2 records, which only happens via a real
`write_declaration_line` call, per `scoring.py`'s field-by-field
comparison against `FixtureOdooClient.written`). `direct_emissions_actual`/
`indirect_emissions_actual` (the fields still requiring the model to
correctly extract and report a *measured* number from document text,
not just copy a known fact) remain at 0% - the field-accuracy investigation
section's core finding stands: the model's own extraction-and-recall
reliability, not tool-call plumbing, is the remaining ceiling. But 0/20 to
2/6-with-full-completion is a real, qualitative step toward a working MVP,
achieved by removing failure surface the model never needed in the first
place, not by tolerating a lower bar.

**Not done, explicitly out of scope for tonight:** further closing the
`direct_emissions_actual`/`indirect_emissions_actual` gap (real extraction
accuracy, not plumbing) would need either a stronger model or dedicated
few-shot/retry work on `extract_field` itself; a full 20-record run is
still blocked on this machine's available RAM.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 135
passed (131 + 4 new regression tests); no existing test's expectations
changed except the one replaced test named above.

---

## Real production-path verification (2026-09-08, same day) - first-ever full-stack success

Everything above (the field-accuracy investigation and MVP-focused fixes)
was verified against `run_evaluation.py`'s harness, which talks to
`FixtureOdooClient`, not a real Odoo instance. At the human partner's
explicit request ("go with #1" - prove the real path works, not just the
harness), this pass exercised the actual deployed shape: `POST /jobs` on
the real orchestrator FastAPI service, a real `llama3.1:8b` call through
the real nginx gate, and a real write into the real Postgres-backed Odoo
database.

**Infra notes (not code changes, but real obstacles hit and fixed):** the
`docker-compose.local-dev.yml` stack found running on this machine
(project name `project-completion`, up 21h) was launched from a git
worktree (`.claude/worktrees/project-completion`) that has since been
deleted - both the `orchestrator` and `odoo` containers' bind mounts
pointed at that now-missing path, so the orchestrator was serving
stale-from-Docker-image code and Odoo's `/mnt/extra-addons` was silently
empty. Recreated both containers in place (`docker compose -p
project-completion -f docker-compose.local-dev.yml up -d --no-deps
<service>`, targeting the existing named volumes so the real `cbam`
database/filestore were untouched) pointed at the current checkout instead,
rebuilding the orchestrator image first to pick up every fix from the two
sections above. `.env.local-dev` was recreated locally (not committed -
`.gitignore`d) from the real secrets already baked into the running `db`/
`odoo`/`nginx` containers' own environments, so the reconstructed stack's
credentials still matched what Postgres/Odoo/nginx already had on disk.
Ran `odoo -u cbam` (module upgrade) to apply this session's schema changes
(`cbam.good.benchmark`, `certificates_status`) to the live database -
succeeded cleanly, verified directly against `information_schema` and
`\d cbam_good_benchmark`. Re-ran `dev_fixtures.seed_dev_fixtures_odoo()`
(idempotent - reused all 2 existing goods and 6 installations, only added
the 3 new benchmark rows) to populate the new table.

**The real job:** `POST /jobs` against the one pre-existing real
declaration line (id 1, `SYNTH-0000-B286B5.txt` attached, from an earlier
session's live-verification fixture) returned `job_id`, polled to
`status: completed` after 8 iterations with `final_message: "The
declaration line has been successfully written."` A query against the real
`cbam_declaration_line` row confirmed a write genuinely happened (not the
historically-documented "completed but nothing written" silent-stop
pattern) - `certificates_status` correctly computed as `exempt` (41.88 t is
under the 50 t/year threshold), proving the whole M2-through-M8 pipeline
(known_context injection, the new benchmark model, the calc engine, the
new status field) works together against a real database, not just in
unit tests or the synthetic harness.

**But the written VALUES are wrong, and the real trace shows exactly why -
a distinct, new, specific finding, not a repeat of the extract_field
grounding bug:** pulled from `cbam_source_document.raw_llm_output` (the
real audit trail, live data): the model called `extract_field(document_id=
"1", field_name="direct_emissions_actual")` successfully (the document_id
fix from the field-accuracy investigation section works in the real path
too, not just the harness), then separately called `lookup_default_value()`
and got back a real emission factor (`direct_ef=2.1`, real
`emission_factor_id=2` from the live database this time, not a fixture
`None`). It then called `calculate_emissions` with **different, invented
numbers** (`direct_ef=0.98, indirect_ef=1.49`) instead of the `2.1`/`0.0`
it had just been handed - a value-carryover failure between two of its own
tool calls, not a missing-context problem. Finally it called
`write_declaration_line` with `embedded_emissions_total` (not a real
argument on that tool - the model conflated "the number I just computed"
with "what this tool needs") and never supplied
`direct_emissions_actual`/`indirect_emissions_actual`/`emission_factor_id`
at all, so every one of them landed at its 0.0/`None` default. The
resulting row is real and committed, but empirically wrong - exactly
consistent with, and now demonstrated in the real system rather than only
the harness, the field-accuracy investigation's conclusion: the remaining
gap is the model's own reliability at carrying values between steps of a
multi-step task, not tool-call plumbing or missing context.

**Assessment:** this is the "real MVP" milestone the human partner asked
for in the sense that mattered - the full architecture, end to end, no
mocks, produces a real committed database row from a real document via a
real agentic loop, for the first time in this project's history. It is not
yet a *correct* MVP - the numbers it writes cannot be trusted without
human review, which is exactly why `flag_for_human_review` and Odoo's
`needs_review`/draft states exist in this design. Closing that gap is
model-reliability work (retry-with-correction prompting, a stronger model,
or accepting human-in-the-loop review as the actual product shape), not
more plumbing fixes.

---

## Value-carryover fix + temperature fix: first fully correct real write (2026-09-08, same day)

Direct continuation of the section above's finding - closed both gaps it
identified, live-verified against the real system, at the human partner's
request to keep going toward "the real MVP."

**Fix 1 - dispatcher-side memory for `lookup_default_value`'s result.**
The prior section's real trace showed the model correctly calling
`lookup_default_value`, getting back `direct_ef=2.1`, then inventing
different numbers (`0.98`/`1.49`) when calling `calculate_emissions`
moments later, and never supplying `emission_factor_id` to
`write_declaration_line` at all. Since `lookup_default_value`'s result is
exactly as deterministic as the `known_context` facts from the MVP-focused
section, the same fix applies: `ToolDispatcher` now remembers its own last
successful `lookup_default_value` result and auto-fills
`calculate_emissions`'s `direct_ef`/`indirect_ef`/`markup_pct` and
`write_declaration_line`'s `emission_factor_id` from it - but **only when
this line's `data_source` is `"default"`** (from `known_context`, never
model-supplied), so a stray/mistaken `lookup_default_value` call on an
`"actual"`-sourced line (also observed live) can't clobber a genuinely-
extracted measured value. Two new regression tests cover both directions
(the fill-in, and the must-not-clobber case) plus one for the injection
itself; `softworker/tests/test_tools.py`.

**A separate, structural bug found while testing this fix live - blocked
the entire `data_source="default"` pathway from ever working in real
Odoo.** `cbam_declaration_line.py`'s `_check_emission_factor_set_for_default_source`
constraint (added in the July "Full-codebase verification" pass to stop a
silent-zero bug) raised a hard `ValidationError` on *any* save where
`data_source="default"` and `emission_factor_id` is unset - including the
line's own creation. But a `"default"`-sourced line legitimately starts in
exactly that state: a human sets `data_source="default"` when creating the
line (no emission factor chosen yet), and the agent's whole job is to find
and set `emission_factor_id` via its one atomic `write_declaration_line`
call. Verified this empirically against the real live database: creating
such a line via `odoorpc` failed with the constraint's own error message
before any code in this session touched it. **This means no
`data_source="default"` line could ever have reached a successful real
write in this project's history** - M6/M9's live runs either used
`data_source="actual"` fixtures or never got far enough to hit this. Fixed
by removing the hard constraint and extending `certificates_status`
(this session's own earlier addition) with the same honest-incomplete
pattern: `data_source="default"` + no `emission_factor_id` now computes
`certificates_status="incomplete"` (0 certificates, visibly unresolved)
instead of either crashing or silently completing. No pytest coverage for
this specific change - Odoo model-layer constraints aren't exercised by
this repo's plain-pytest suite (a repeat of the audit's original,
already-documented caveat) - verified only live, per below.

**Fix 2 - a real infra finding, not code originally suspected: sampling
temperature.** While live-testing fix 1, five consecutive real jobs
against the newly-unblocked `data_source="default"` line failed differently
- the model repeatedly narrated a tool call as plain-text JSON inside its
message `content` instead of using the actual OpenAI function-calling
protocol (e.g. literally emitting `{"name": "write_declaration_line",
"parameters": {...}}` as chat text). Ollama's own request log for these
calls showed `temp = 1.000` - `llm_client.py` never set a `temperature` at
all, so Ollama's default (effectively unconstrained sampling) applied. Low
temperature is a well-known lever for structured-output/function-calling
adherence in small models. Added `temperature=0.1` as `LLMClient`'s new
default (configurable via a constructor param, not hardcoded past that
one call site) - low but non-zero, since a fully deterministic 0.0 can
make some models loop on a single bad completion pattern rather than vary
their next attempt after a tool-call error. Two new regression tests
(`test_chat_passes_a_low_default_temperature`,
`test_chat_temperature_is_configurable`) in `test_llm_client.py`.

**Live result - the first fully correct, end-to-end real write in this
project's history.** After both fixes (orchestrator rebuilt, Odoo
container restarted to reload the constraint removal - a one-off
`odoo -u cbam` schema-upgrade run alone does NOT reload the already-running
server process's Python code, a real operational gotcha hit and resolved
this session), a fresh `data_source="default"` line (id 4, quantity 30t,
steel/BF-BOF/EG, a real document attached) completed in 4 iterations. The
real trace (`cbam_source_document.raw_llm_output`, live data):
`lookup_default_value` called correctly (`direct_ef=2.1`, `emission_factor_id=2`),
`calculate_emissions` called with those exact real values this time (no
invention - `embedded_emissions_total=69.3`), then `write_declaration_line`
called with **`emission_factor_id` omitted again** - and the write still
landed correctly (`emission_factor_id=2` in the real database) purely
because the dispatcher auto-filled it. The real declaration_line row now
shows `quantity_tonnes=30.0`, `data_source=default`, `emission_factor_id=2`,
`embedded_emissions_total=69.300` (= 30 × 2.1 × 1.1, verified against the
real calc engine formula), `certificates_status=computed`,
`certificates_required=40.050` - a real, correct, cross-checked number,
not a zero or a guess.

**Assessment:** this is the "real MVP" success case the two sections above
were building toward - not just a completed job (already achieved), and
not just correct plumbing with wrong values (the previous section's
finding), but a genuinely correct end-to-end result, live-verified against
the real deployed architecture. It required three layered fixes discovered
in sequence by testing against real infrastructure rather than assuming:
known_context injection (MVP-focused section), lookup-result carryover +
the default-source constraint bug (this section), and temperature (this
section, found only because the constraint fix unblocked a code path that
had never been reachable before). `direct_emissions_actual`/
`indirect_emissions_actual` accuracy for `"actual"`-sourced lines remains
untested by this specific run (this line was `"default"`-sourced) and is
still the open item from the field-accuracy investigation section -
genuine document-value extraction, not carryover or plumbing.

---

## Closing the actual-sourced extraction gap (2026-09-08, same day)

Direct continuation, at the human partner's request to keep going toward
the `direct_emissions_actual`/`indirect_emissions_actual` gap the section
above left open. Created a genuinely `data_source="actual"` real
declaration line (id 5, `SYNTH-0018-D46D18` - steel/CN/BF-BOF, quantity
405.08t, real ground truth `direct_emissions_actual=2.172`,
`indirect_emissions_actual=0.079`, `carbon_price_paid_origin=12.04`, a
document whose text genuinely contains these numbers, unlike the earlier
`SYNTH-0000-B286B5` line whose carbon-intensity-report document has a
blank emissions section) and ran real jobs against it.

**First real run (temperature fix already in effect, no new fix yet):**
`extract_field` correctly retrieved the document text, and the model
correctly read `direct_emissions_actual=2.172`/`indirect_emissions_actual=
0.079`/`carbon_price_paid_origin=12.04` out of it - genuine, accurate
extraction, working already. But it then called `calculate_emissions`
using `write_declaration_line`'s field names (`direct_emissions_actual`
instead of `calculate_emissions`'s actual `direct_ef`), got a validation
error, pivoted to an irrelevant `lookup_default_value` call instead of
retrying with the right key name, and the final `write_declaration_line`
call included only `embedded_emissions_total` (not a real argument on that
tool) - discarding all three correctly-extracted numbers. Real database
result: all three actual-value fields landed at their 0.0 default, same
failure shape as the "default"-sourced case in the section above, just for
a different underlying reason (schema-name confusion between two tools
that both take "the direct emission number" under different names, not a
missing deterministic source this time).

**Fix - a prompt-only fix, deliberately tried before anything more
invasive.** Since there's no deterministic dispatcher-side value to
auto-inject here (unlike `lookup_default_value`'s result - `extract_field`
returns raw text; the model itself does the reading, so there is no
structured number for `ToolDispatcher` to remember and re-inject), the
narrower architectural fix from the section above doesn't apply directly.
Added one explicit paragraph to `SYSTEM_PROMPT`
(`softworker/orchestrator/main.py`) stating plainly that
`calculate_emissions`'s `embedded_emissions_total` is a preview, not the
write payload, and that `write_declaration_line` must separately carry the
same `direct_emissions_actual`/`indirect_emissions_actual`/
`carbon_price_paid_origin`/`precursor_emissions` values found earlier,
under those exact field names (not `calculate_emissions`'s `direct_ef`/
`indirect_ef`).

**Result, two independent live re-runs of the same line (real
`llama3.1:8b`, real Odoo, real orchestrator API):** both runs correctly
wrote `direct_emissions_actual=2.172` and `indirect_emissions_actual=
0.079` - exactly matching ground truth, reproducibly, not a one-off. Both
runs still left `carbon_price_paid_origin=0.00` (ground truth: 12.04) -
the model extracted this value correctly in an earlier `calculate_emissions`
attempt in both traces, but never carried it into the final
`write_declaration_line` call either time. A real, reproducible partial
fix: 0 of 3 actual-value fields correct before this change, 2 of 3 after,
consistently across two samples - not full closure, and the remaining gap
(one specific field, `carbon_price_paid_origin`, consistently dropped) has
the same shape as everything else in this project's live-testing history:
the model reliably omits some subset of several values it must carry
across calls, just a smaller subset now than before every fix this session
made. `embedded_emissions_total` for this line computed correctly both
times (879.834 = 405.08 x 2.172, verified against the real formula) because
Odoo's own `_compute_embedded_emissions_total` recomputes independently
from the real `direct_emissions_actual` field - it does not trust
whatever total the model self-reported via `calculate_emissions`, which
this run's trace also showed drifting to a wrong number (891.176, from an
irrelevant `lookup_default_value` call) without that error ever reaching
the real stored data.

**Not done - a real next lever, not attempted tonight:** a more invasive
fix mirroring the `lookup_default_value` carryover mechanism could work
here too - remember the last raw value the model supplied under
`write_declaration_line`'s exact field names in ANY prior tool call
(regardless of which tool or whether that call validated), and auto-fill
`write_declaration_line` from that memory when the model omits a field it
already stated once. This is more speculative than the lookup-result
carryover fix (it would be reading from the model's own unvalidated,
possibly-wrong intermediate statements, not a deterministic tool output),
so it was deliberately not attempted without discussing the tradeoff
first - flagged here as the concrete next step if further closing this
gap is worth the added complexity.

---

## Remembered-value carryover: full closure for this test case (2026-09-08, same day)

Direct continuation, at the human partner's explicit request to build the
speculative fix the section above flagged rather than stop. Implemented
exactly as described there: `ToolDispatcher` now watches every tool call's
raw arguments (before validation, regardless of which tool or whether that
call ultimately validates) for any of `write_declaration_line`'s own
optional field names (`direct_emissions_actual`, `indirect_emissions_actual`,
`carbon_price_paid_origin`, `precursor_emissions`), remembers the last
value seen under each, and fills in any of them still missing when
`write_declaration_line` is finally called - **filling gaps only, never
overriding** a value the model deliberately restates in the write call
itself. Whatever ends up in the final merged dict still passes through the
same Pydantic plausibility bounds as before, so a bad remembered value is
rejected exactly as if the model had typed it directly - this mechanism
can only help a value survive to the write, never bypass the existing
safety net. Two new regression tests in `test_tools.py` cover both the
fill-in and the model's-own-value-wins-over-remembered-one cases.

**Live result, the same `data_source="actual"` line as the section above,
two independent real runs after this fix:** both runs wrote all three
values correctly - `direct_emissions_actual=2.172`,
`indirect_emissions_actual=0.079`, **and now `carbon_price_paid_origin=
12.04`** (previously 0.00 in every prior run) - an exact, reproducible
match to ground truth on every actual-sourced field this test exercises,
not a partial result. `embedded_emissions_total=879.834` (=
405.08 x 2.172, still verified against the real formula) and
`certificates_status=computed` with a real, correct
`certificates_required` both remained consistent with the correct inputs.

**Assessment:** for this specific test case (`SYNTH-0018-D46D18`, a
mill-certificate-style document with all its actual-emissions fields
present and unambiguous), the actual-sourced extraction path is now fully
closed - 0/3 correct at the start of tonight's "Closing the actual-sourced
extraction gap" section, 3/3 correct and reproducible now, across the
combination of the temperature fix, the prompt fix, and this carryover
mechanism. This is not a claim that extraction is now 100% reliable in
general - a harder document (missing fields, ambiguous units, a "hard"
M1-generator difficulty tier) or a different record could still expose
gaps this specific fix doesn't reach, since it only rescues values the
model *did* correctly determine somewhere in the conversation; it cannot
manufacture a value the model never derived at all. A broader-sample
re-run (the full 20-record M9 harness, still blocked tonight by this
machine's available RAM) would be the honest next check before generalizing
this result beyond the two live samples taken here.

---

## The honest broader-sample check (2026-09-09)

Did exactly the check the section above flagged as needed. A full
20-record run was attempted first and killed by the OS for low memory
(same failure as the first attempt in the field-accuracy investigation
section) - this machine's WSL2/Docker memory footprint had grown further
overnight (Ollama's own container RAM had ballooned to 5.1 GB of its 7.3 GB
limit after ~23h uptime, a real, if unsurprising, resource-accumulation
issue, not a code bug). Restarting the `ollama` and `nginx` containers to
reclaim memory hit the same deleted-worktree bind-mount problem documented
in the "Real production-path verification" section (this time for
`nginx`, previously `orchestrator`/`odoo`) - recreated `nginx` pointing at
the current checkout the same way. Free memory kept falling regardless
(553 MB, then 536 MB), so rather than force a `wsl --shutdown` (disruptive
to the human partner's entire WSL2 environment, not just this project),
the human partner chose to run a smaller, still-genuinely-unselected batch
instead of the full 20.

**Result (`docs/evaluation-broader-sample-2026-09-09.md`, 5 records,
first 5 in numeric order - not hand-picked): 0/5 correct, including
`quantity_tonnes`/`data_source`**, which are unconditionally correct
whenever any real write happens (dispatcher-injected from ground truth,
never model-supplied). Their being wrong means no record in this small
batch ever reached a real `write_declaration_line` call - 1 `completed`
(possibly a silent stop, not necessarily a write - a known ambiguity),
3 `escalated`, 1 `exhausted`.

**This is the honest, sobering counterweight to the two sections above.**
Both things are true at once, and neither cancels the other:

- The specific, diagnosed failure modes this session fixed are real and
  independently verified live: missing `document_id` (field-accuracy
  investigation), excess required fields the model reliably dropped
  (MVP-focused follow-up), the `data_source="default"` constraint that
  made an entire code path unreachable, unset sampling temperature, and
  value carryover between the model's own tool calls (both sections
  above) - each demonstrated with a real before/after live trace, not
  assumed.
- None of that adds up to a *reliable* model. A small, genuinely
  unselected sample (5 records, not the 2 specific ones this session
  happened to hand-verify) shows the underlying `llama3.1:8b` tool-calling
  ceiling from M4's original benchmark (50% valid-call rate, the *best*
  of 4 candidates tried) is still the dominant factor in whether any given
  job completes correctly at all.

**Conclusion for anyone picking this up next:** this session's fixes were
worth making - they removed real, structural bugs that had nothing to do
with model capability (a constraint that made a whole data path
impossible, a temperature nobody had set, tool schemas asking for facts
the orchestrator already had) - but they are not a substitute for a more
reliable model. The honest framing for any write-up of this project: the
mechanism is now demonstrably correct when the model cooperates: unproven
at scale is where this stands, not "solved." A full 20-record run (or
larger) on a machine with more headroom - or benchmarking a model M4 never
tried - remains the concrete next step for anyone who wants a real,
statistically meaningful accuracy number rather than either of this
session's two anecdotes (the encouraging hand-picked ones, or this
section's discouraging unselected one).

---

## M7 benchmark research: steel EAF_scrap resolved (2026-09-09)

At the human partner's request for primary-source research (not code) as
the next milestone, following on from the "M7 benchmark route-dimension
fix" (Independent audit + follow-up fixes section) - that fix corrected
the *schema* but deliberately left both new route-specific benchmark
VALUES as `None`/BLOCKED since IR 2026/1412's Annex "BENCHMARKS" had not
been re-checked for route-specific entries beyond "Hot metal" and
"Aluminium".

Re-fetched the regulation directly (`curl` on EUR-Lex's CELEX PDF, 556,779
bytes, same document already cited in this project's M7 work) and read
its full Annex "BENCHMARKS" table end to end via `pdftotext -raw` - all 3
sections, 47 product-benchmark rows, not just a targeted grep.

**Resolved: steel EAF_scrap benchmark = 0.142** - a real, dedicated "EAF
carbon steel" row exists in Section 2, distinct from "Hot metal" (1.248)
by roughly 9x, correctly reflecting scrap-EAF steelmaking's much lower
real-world emissions intensity. This is now seeded in
`shared/data/seed_emission_factors.py` with a full citation.

**Re-confirmed genuinely absent: aluminium secondary_recycled benchmark**
- the complete 47-row table contains exactly one aluminium entry anywhere
(the primary-electrolysis "Aluminium" row already seeded) - no secondary/
recycled variant exists in this source. Upgraded from "not yet checked"
to "confirmed absent by a full read", the same evidentiary standard as
steel EAF_DRI's `direct_ef` gap. Stays `benchmark=None` - not guessed.

`find_incomplete_seeds()` now returns 2 items (was 3): steel EAF_DRI's
`direct_ef` and aluminium secondary_recycled's `benchmark`. Full
derivation, exact quotes, and the complete extracted benchmark table:
`docs/m7-source-verification.md`'s "2026-09-09 addendum" section.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 142
passed (no count change - one test's expected list shrank by one item,
matching the resolved field; no other test's expectations changed).

---

## The full 20-record run, and the real root cause of the memory failures (2026-09-09)

Direct continuation, at the human partner's request to pursue milestone
#1 (the full evaluation) after the M7 research detour above. Got killed
by the OS for low memory twice more (one direct 20-record attempt, one
direct 5-record retry) even starting from a freshly `wsl --shutdown`'d,
8+ GB-free machine - worse than the pattern in "The honest broader-sample
check" section, since that section's fix (`wsl --shutdown` alone) no
longer reliably helped on its own.

**Root cause, actually found this time** (at the human partner's explicit
request to stop guessing and investigate): checked memory *inside* the
WSL2 VM itself (`wsl.exe -- free -h`), not just what Windows reports.
Inside the VM: `available: 6.0G` of `total: 7.3G` - genuinely healthy,
containers using under 2 GB combined. The real problem was entirely on
the Windows side: WSL2's VM had grown toward its **default** memory
ceiling (~50% of host RAM, uncapped by any `.wslconfig` - none existed on
this machine), and Windows counts that reserved ceiling as "used"
regardless of how much of it is reclaimable Linux page cache, not real
work. The background-task memory-safety monitor that kills this session's
long-running commands watches Windows' outward-facing free-memory number,
which doesn't reflect the VM's real internal availability.

**Fix:** created `~/.wslconfig` (first attempt, `[wsl2] autoMemoryReclaim=
gradual`, failed to parse on this WSL version - "unknown key" - moved to
`[experimental] autoMemoryReclaim=gradual`, which parsed cleanly) plus a
**hard memory ceiling**, `[wsl2] memory=6GB`, sized comfortably above
this stack's real combined footprint (under 2 GB per `docker stats`) but
well below the default ~7.3 GB ceiling that was starving Windows of a
number it could report as free. Applied via `wsl --shutdown` + bringing
the stack back up. This is a host-level file outside the git repo -
confirmed with the human partner before creating it, since it affects
their whole WSL2 environment, not just this project.

**Result: it worked.** Records 5-19 (15 of the 20) ran across 3 more
batches of 5 with zero further memory kills, after the same-sized batch
had just failed twice before the fix. Records 0-4 (already gathered in
"The honest broader-sample check" section, before this fix existed) were
reused rather than re-run, since nothing about the fix could change what
already happened.

**Full 20-record result** (`docs/evaluation-full20-2026-09-09.md`, all of
this session's fixes in effect):

| | completed | escalated | exhausted |
|---|---|---|---|
| 20 records | 5 | 13 | 2 |

| field | accuracy |
|---|---|
| quantity_tonnes | 4/20 (20%) |
| data_source | 4/20 (20%) |
| carbon_price_paid_origin | 3/20 (15%) |
| precursor_emissions | 4/20 (20%) |
| direct_emissions_actual | 1/14 (7%) |
| indirect_emissions_actual | 1/14 (7%) |

**This is the real, statistically meaningful number this whole
field-accuracy thread has been building toward.** Compare directly to
the original M9 baseline (`docs/evaluation.md`): 0% on every field, no
exceptions. Every field this session's fixes could plausibly reach
(`quantity_tonnes`/`data_source`/`carbon_price_paid_origin`/
`precursor_emissions` - all either dispatcher-injected or carryover-
rescued once a write happens) landed at 15-20%, up from 0%. The two
fields requiring genuine, un-assisted document-text extraction
(`direct_emissions_actual`/`indirect_emissions_actual`) improved far less
(7%, up from 0%) - consistent with this session's repeated finding that
those two specifically test the model's own reading/recall reliability,
which no plumbing fix reaches. 5/20 completed (up from historical
17/20-but-mostly-`no_write` and later 15/20/13/20 in the "Agentic
completion-gap" and "field-accuracy investigation" sections) - fewer raw
completions, but a real check of the 5 completions here (cross-referencing
which ones landed correct `quantity_tonnes`/`data_source`, which can only
happen via a genuine write) shows 4 of the 5 are real, correct writes; the
5th (`SYNTH-0000`, wrong on those two despite `completed` status) matches
the long-documented "completed but nothing written" silent-stop ambiguity.

**Honest framing, unchanged from every section above:** this is real,
verified, meaningful improvement - not a claim of reliability. 15-20% is
still a low bar for a production system; `llama3.1:8b`'s own ceiling (M4's
50% valid-tool-call rate) remains the dominant constraint on how much
further plumbing fixes alone can move this number. The concrete next
lever, per the "M9 — Evaluation" row's own history, is a stronger/
different model benchmarked against this now-fixed, now-memory-stable
harness - the comparison M4 never got to run fairly.

**Verification:** no test suite changes in this section - this is a real
live-infra run and a host-level config fix, not a code change.

---

## Model comparison: qwen2.5:7b-instruct vs. llama3.1:8b on the fixed harness (2026-09-09)

Direct continuation, at the human partner's request to pursue the "next
lever" the section above named: a different model against the now-fixed,
now-memory-stable harness. M4's original raw tool-calling benchmark
(`docs/model-benchmark.md`) had `qwen2.5:7b-instruct` as the closest
runner-up to `llama3.1:8b` (40% vs. 50% valid-call rate) - worth checking
against the real harness rather than trusting that raw number alone.

Pulled `qwen2.5:7b-instruct` into the container's Ollama (4.7 GB,
`docker exec project-completion-ollama-1 ollama pull qwen2.5:7b-instruct`)
and ran the same 2 batches of 5 (records 0-9, same records, same fixes,
same day) as `llama3.1:8b`'s full-20 run.

**Result** (`docs/evaluation-qwen25-7b-2026-09-09.md`): **10 of 10 records
exhausted** the full 9-iteration cap without ever calling
`write_declaration_line` or `flag_for_human_review` - 0% field accuracy,
and a *worse*, qualitatively different failure mode than `llama3.1:8b`'s
mix of completed/escalated/exhausted on the identical records under the
identical harness.

**Conclusion:** M4's raw-benchmark ranking holds up on the real, fixed
harness, by a wider margin than the raw 40%-vs-50% numbers alone
suggested. `llama3.1:8b` remains the best-of-tested model for this
project's tool schemas. At the human partner's choice, the comparison was
concluded here rather than continuing to `qwen3:8b`/`qwen2.5:14b-instruct`
(both scored 0% in M4's raw benchmark for a reason - emitting multiple
tool calls per turn - that `agent_loop.py` may actually handle correctly,
since it explicitly preserves the model's own multi-call ordering within
a turn rather than rejecting it; this remains a real, unexplored
possibility for a future session, not ruled out).

**Verification:** no test suite changes - a real live-infra model
comparison, not a code change.

---

## qwen3:8b re-test: a real correction to M4's model ranking (2026-09-09)

Direct continuation - the human partner asked to pursue exactly the
"remains a real, unexplored possibility" item the section above named.
M4's raw tool-calling benchmark had scored `qwen3:8b` at **0%** valid-call
rate, attributed to "emitting multiple tool calls per turn rather than
the one this benchmark scores" - a real property of the model, but
possibly an artifact of that benchmark's narrower scoring rule rather
than a real capability gap, since `agent_loop.py` itself explicitly
preserves and executes a model's own multi-tool-call ordering within one
turn (a tested architectural property, not an assumption).

Pulled `qwen3:8b` into the container (5.2 GB) and ran the identical 2
batches of 5 (records 0-9) used for `llama3.1:8b` and
`qwen2.5:7b-instruct`, same day, same fixes, same harness.

**Result - M4's 0% ranking does not hold up on the real harness:** 8/10
completed (0 escalated, 2 exhausted), and per-field accuracy on the exact
same 10 records essentially **tied** with `llama3.1:8b`'s own numbers on
those same 10 records (30%/30%/30%/12%/12% vs. `qwen3:8b`'s
30%/30%/20%/12%/12% - differing by exactly one record on one field).
`qwen3:8b` reached a terminal, successful action twice as often (8/10 vs.
4/10) and never escalated once, vs. `llama3.1:8b` escalating on half the
sample. Full comparison table: `docs/evaluation-qwen3-8b-2026-09-09.md`.

**A genuine correction surfaced along the way:** one `qwen3:8b` record
(`SYNTH-0004`) came back `status="exhausted"` yet scored 6/6 fields
correct - a real write happened before the loop exhausted its iteration
cap. This corrects an assumption stated in "The honest broader-sample
check" section above ("escalated/exhausted... never write by
definition") - `agent_loop.py` only terminates early on
`flag_for_human_review`; nothing stops the model from writing
successfully and then continuing to call more tools until the cap forces
an `exhausted` exit. Escalation genuinely never writes (that path is a
real early return); exhaustion can follow a real write.

**Conclusion:** on this session's own same-day, same-records, same-
harness, same-fixes evidence, `qwen3:8b` is at least as good a choice as
`llama3.1:8b` for this project's actual tool schemas - arguably better,
given its higher completion rate at tied accuracy. M4's original
benchmark measured something real (multi-call-per-turn behavior) but drew
the wrong practical conclusion from it (unusable) because its scoring
rule didn't match how this project's real agent loop actually works.
`qwen2.5:14b-instruct` (M4's other 0%-scoring model, same underlying
reason) remains untested against this harness - a real open question for
a future session, not this one, given time already spent tonight.

**Verification:** no test suite changes - a real live-infra model
comparison, not a code change.

---

## Rename to hardworker/softworker, and the first real softworker deployment (2026-09-09)

At the human partner's request, renamed every "Machine A"/"Machine B"
reference across the repo to "hardworker" (LLM host) / "softworker" (Odoo
host) - directories included (`git mv machineA hardworker`, `git mv machineB
softworker`), plus container names, Tailscale hostnames (`cbam-hardworker`/
`cbam-softworker`), Docker build/COPY paths, and every prose mention in
`README.md`/`projecthandoff.md`/this file/historical `docs/superpowers/`
plans. Verified after the rename: all 3 `docker-compose.yml` files
(`hardworker/`, `softworker/`, `docker-compose.local-dev.yml`) still parse
with `docker compose config`, and the full test suite still passes (142
passed) - the rename touched only names, no logic.

**Then the actual point of the session: bring the softworker up on real,
physical hardware for the first time** (Task 7's Tailscale install had been
deferred since M0; this is the first time any of this has run outside
`docker-compose.local-dev.yml`'s single-host stand-in). Hit a real, still-
unexplained blocker doing this the documented way: the Tailscale admin
console's key-generation page (`login.tailscale.com/admin/settings/keys`)
produced auth keys containing the literal substring `CNTRL` - reproduced
across 3 separately generated keys, via the dedicated copy button (not
manual selection), and in an incognito window with no extensions, ruling out
a browser-extension or clipboard-tool explanation on this end. Every key
generated this way was rejected outright by Tailscale's real control server
(`invalid key: API key ... not valid`) when the `tailscale` sidecar
container tried to authenticate - not a cosmetic issue, a genuinely broken
key. Root cause not found from this side; flagged to the human partner as
worth reporting to Tailscale support directly rather than continuing to
debug blind.

**Workaround, chosen by the human partner over two alternatives** (keep
fighting the admin console, or defer Tailscale entirely and stay
bridge-network-only): this physical host already runs its own Tailscale
client natively and is already on the tailnet (confirmed via `tailscale
status`: node `rami`, `100.107.246.65`, account `Rami-ayounii@`, genuinely
authenticated - the host's own connection is not part of whatever is broken
in the admin console). Rewrote `softworker/docker-compose.yml` to drop the
`tailscale` sidecar service entirely: `odoo` and `orchestrator` now publish
their ports straight to the host (`8069`, `8000`) and both join the
`internal` bridge network directly (`orchestrator`'s `ODOO_URL` changed from
`http://127.0.0.1:8069`, which relied on sharing the sidecar's network
namespace, to `http://odoo:8069`, Docker's own service-name DNS). Documented
the trade-off in a header comment on the compose file itself: this drops the
per-role Tailscale identity (`cbam-softworker`) and the tag-scoped ACLs in
`tailscale-acl-example.json` in favor of reachability via this host's own
general-purpose node - revisit once the admin console bug is understood.

**Real verification, not just "containers started":** brought up
`softworker/docker-compose.yml` for real (Postgres 16, Odoo 17, the
orchestrator image built from `softworker/orchestrator/Dockerfile`).
Confirmed both Odoo (`/web/login`) and the orchestrator (`/docs`) answer
`http` requests on `localhost` **and** on the host's real tailnet IP
(`100.107.246.65`) - genuinely reachable over Tailscale, just via the host's
identity instead of a dedicated one. Ran `scripts/init_local_dev_odoo.py`
against this real instance (not the local-dev stack it was originally
written for - reused as-is, no changes needed): created the `cbam` database,
installed the `cbam` module, seeded `shared/data/dev_fixtures.py`'s fixtures.
Verified over real RPC (`odoorpc`, not just trusting the script's own
success message): `cbam.good` = 2, `cbam.installation` = 6,
`cbam.emission.factor` = 6, `cbam.production.route` = 3, `cbam.declaration`
= 0 (fresh, as expected) - exact match to the fixture counts the script
reported.

**Not done:** the hardworker isn't up yet, so `OLLAMA_BASE_URL` in
`softworker/.env` is still a placeholder and the orchestrator's agent loop
has not been exercised against this real deployment (only Odoo/Postgres/the
orchestrator's HTTP shell are verified so far - no LLM calls yet). The
Tailscale admin console bug remains unresolved and unexplained.

**Verification:** `docker compose config` on all 3 compose files after the
rename; `python -m pytest softworker/tests/ shared/ -q` → 142 passed;
`curl` against both `localhost` and the tailnet IP for `odoo:8069` and
`orchestrator:8000`; real `odoorpc` queries against the live database
confirming exact fixture counts.

---

## Anti-hallucination gate: verbatim `source_quote` for actual-sourced emissions (2026-09-09)

Direct continuation, targeting the field-accuracy investigation's own
worst-measured spot: `direct_emissions_actual`/`indirect_emissions_actual`
sat at 7% accuracy (`docs/evaluation-full20-2026-09-09.md`) - the only two
fields needing genuine document-text reading rather than a deterministic
carried-over value, so no plumbing fix could reach them.

**What changed:** `write_declaration_line` now requires a `source_quote`
whenever `data_source="actual"`, checked in two layers:
- `tool_args.py` (`WriteDeclarationLineArgs`) rejects a missing/empty
  `source_quote` cheaply, at validation time.
- `tools.py`'s `ToolDispatcher` does the real check, which needs session
  state Pydantic doesn't have: a new `self._extracted_texts` list records
  every `document_text` `extract_field` has actually returned this job, and
  `_write_declaration_line` verifies `source_quote` is a genuine substring
  of one of them - not just a plausible-looking string the model wrote.
  Fails with a `ValueError` (fed back to the model as a tool error, same
  path as every other validation failure) naming the requirement and
  suggesting `flag_for_human_review` if no real quote exists.

`SYSTEM_PROMPT` (`softworker/orchestrator/main.py`) also gained an explicit
Thought/Self-Reflection-before-Action instruction (reflect on the previous
tool result, then state reasoning, both in the model's own message content
before the next tool call) and reframes the final `write_declaration_line`
call as a confirmation step requiring that quote. Deliberately no
orchestrator-side enforcement of this structure - that would reintroduce
the `if step == ...` tool-ordering anti-pattern `projecthandoff.md` rules
out; the model can ignore the reflection instruction and nothing in
`agent_loop.py` checks for it.

**Tests:** 5 existing tests exercising actual-sourced writes updated to
supply a real `extract_field` call plus a matching quote; 4 new tests cover
the grounding check itself (missing quote, fabricated quote, a genuinely-
grounded quote, and confirming default-sourced writes still need none of
this).

**Not done:** this gate has not yet been run against a live model - it's
unit/integration-tested against the mocked Odoo/LLM boundary only, same as
every other orchestrator change before its first live run. Whether it
actually moves the 7% number, or just converts some of those wrong answers
into `flag_for_human_review` escalations instead, is untested until the
next real evaluation run.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → passes
with the 9 test changes above (5 updated, 4 new) applied.

---

## Audit: `projecthandoff.md` against current code (2026-09-09)

Direct follow-up in the same session - cross-checked every section of
`projecthandoff.md` (the original spec/handoff doc, source of truth for
scope and architecture decisions per this project's own memory) against
what the code and this file actually say now, rather than trusting the
handoff doc's own text. Everything else held up as still accurate: the
tool list, the 8-10 iteration cap, the single-write-at-the-end constraint,
the no-framework (LangChain/AutoGen/CrewAI) decision, the dependency list.
Two things were stale:

- **Section 4 (architecture diagram/description):** still described the
  original two-sidecar Tailscale topology as current. Updated to document
  today's real deviation (see the "Rename to hardworker/softworker" section
  above): the softworker no longer runs its own Tailscale sidecar - the
  admin console's key-generation page produced auth keys the real control
  server rejected outright (root cause still not found, still worth
  reporting to Tailscale support) - and now reaches the tailnet via the
  physical host's own, separately-authenticated connection instead.
  Consequence spelled out inline: `tailscale-acl-example.json`'s
  `tag:cbam-odoo-host`/`tag:cbam-llm-host` scheme does not apply to the
  softworker as actually deployed; reachability depends on whatever ACLs
  apply to the host's own node. Nothing about the hardworker side changed.
- **Section 11 (open items):** listed the Odoo version and the sync-vs-async
  orchestrator call pattern as still undecided. Both were actually resolved
  during implementation and just never reported back to this doc: Odoo
  version is confirmed 17 (`"version": "17.0.1.0.0"` in
  `softworker/addons/cbam/__manifest__.py`); the call pattern is the async
  job + polling design the handoff doc itself recommended (`POST /jobs`
  returns a `job_id` immediately, `GET /jobs/{job_id}/status` polls it, the
  agent loop runs in a FastAPI `BackgroundTasks` task - plain `def` routes,
  not `async def`, so no `pytest-asyncio` dependency was ever needed).

**Verification:** no test suite changes - a documentation cross-check
against already-tested code, not a code change.

---

## Observability: tool-call vs. reasoning-turn counts (2026-09-16)

Follow-up to the ReAct-style prompting change in the "Anti-hallucination
gate" section above - `SYSTEM_PROMPT` now asks the model to state its
reasoning in its own message content before calling a tool, but nothing
verified whether it actually did, or how often, since `agent_loop.py`
deliberately never enforces or parses that structure (would reintroduce the
tool-ordering anti-pattern `projecthandoff.md` rules out).

**What changed:** `AgentLoopResult` gained two counters, tracked purely for
observability - nothing reads or branches on them inside the loop itself:
- `tool_call_turns` - real model turns that made at least one tool call
  (excludes the iteration-cap fallback `flag_for_human_review`, which never
  goes through the model).
- `reasoning_turns` - the subset of those turns where the model's own
  message `content` was non-empty.

`main.py`'s `_run_job()` threads both values into the job status dict, so a
consumer of `GET /jobs/{id}/status` can see the reasoning rate without
parsing `raw_llm_output`.

**Tests:** 3 new tests in `test_agent_loop.py` (mixed reasoning/no-reasoning
turns counted correctly on the `completed` path; counted on the `escalated`
path; the iteration-cap auto-escalation excluded from both counts so it
doesn't understate the model's real reasoning rate) and 1 in `test_main.py`
asserting the job status dict surfaces both fields.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 149
passed (145 + 4 new tests; no existing test's expectations changed).

---

## Default model switched to qwen3:8b (2026-09-16)

Applied the finding from "qwen3:8b re-test" above, which had never actually
been acted on: `qwen3:8b` ties `llama3.1:8b` on field accuracy on the same
10 records under the same harness, but completes twice as often (8/10 vs.
4/10) and never escalates. `LLM_MODEL`'s default was still `llama3.1:8b`
everywhere despite this. Changed the default (env var overridable, not a
hardcoded requirement) in the 4 places it was set: `softworker/.env.example`,
`softworker/docker-compose.yml`, `docker-compose.local-dev.yml`,
`.env.local-dev.example`, and `main.py`'s own `os.environ.get(..., fallback)`
default.

**Not done:** no live re-run yet with this new default in effect - the next
full evaluation (with the `source_quote` gate and the observability counters
above, both still unexercised against a live model) should use this model
and report real numbers, not just carry over the two-sections-ago
`qwen3:8b` comparison as if it already reflects today's code.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 149
passed (no test asserted the old default string); `docker compose config`
clean on `softworker/docker-compose.yml` and `docker-compose.local-dev.yml`.

---

## Session synthesis + next-session punch list (2026-09-17)

Written so the next session (possibly on a different machine, possibly with
no conversation context left) can pick this up cold. This is a decision
record from a conversation that (a) committed the two doc catch-up sections
above, (b) switched the default model to `qwen3:8b` (previous section), (c)
did a full pre-flight code review of `agent_loop.py`/`tools.py`/
`tool_args.py`/`llm_client.py`/`odoo_client.py`/`main.py`/`calc_engine.py`/
`cbam_declaration_line.py` and found no bugs - the pipeline is internally
consistent and ready for a live run, and (d) evaluated and rejected a
"checklist/todo-list agentic planning" pattern (Manus-style `todo.md`) as
not applicable to this project - explained in full below since it's a real
design decision, not just a rejected idea to forget.

**Why the checklist idea was rejected (don't re-litigate this without new
evidence):** that pattern targets long-horizon tasks (dozens/hundreds of
steps) where an agent can lose track of a large plan. This project's job is
8-10 tool calls on one declaration line - too short for that failure mode to
apply. More importantly, `ToolDispatcher` already implements a *stronger*
version of the same idea (deterministic, dispatcher-tracked state -
`known_context` injection, `_last_lookup_default_value` carryover,
`_remembered_write_fields` - silently filled in, never requiring the model
to read/maintain anything) - and this project's own eval history is full of
evidence that these specific small models (`llama3.1:8b`, `qwen2.5:7b`) are
unreliable at faithfully following structured artifacts they're handed
(dropping args, inventing field names). A model-facing checklist would be
reintroducing exactly the failure category five sessions of fixes already
worked to remove. If this comes up again, the burden of proof is on showing
a *new* failure mode this doesn't already cover, not on re-explaining the
general pattern.

**Also established: architecture-level fixes have hit diminishing returns,
with one real exception.** Comparing fix categories against measured
results: plumbing/architecture fixes (missing `document_id`, tool-schema
shrinking, value carryover, temperature, the default-source constraint) took
"plumbing-reachable" fields from 0% to 15-20% (up to 3/3 on hand-verified
records). The same fixes, applied over the same sessions, moved
`direct_emissions_actual`/`indirect_emissions_actual` (the two fields
needing genuine document comprehension) only 0% to 7%. That gap is the
signature of a model-capability ceiling, not remaining architecture debt -
confirmed independently by M4's raw benchmark (best local model tested: 50%
valid-tool-call rate). Further generic "optimize the architecture" passes
are not expected to move this; the specific, still-untried levers that
target the comprehension gap directly are listed below.

### Leave as-is (validated - do not modify without new evidence)
- The single-agent, continuous-context loop (`agent_loop.py`) - no
  multi-agent framework, no tool-ordering logic.
- `ToolDispatcher`'s deterministic state (`known_context` injection,
  `_last_lookup_default_value` carryover, `_remembered_write_fields`).
- The `source_quote` anti-hallucination gate's *design* (cheap Pydantic
  check + real substring verification against `_extracted_texts`) - sound,
  just not live-tested yet (see punch list).
- `calc_engine.py` - pure Python, zero LLM involvement in the actual number.
- The Odoo model layer (`certificates_status`, route-specific benchmark
  lookup, sector-consistency constraint) - reviewed, correct.
- Iteration cap (8-10), single-write guard, escalation-on-cap-exhaustion.
- The Docker/Tailscale layered *design* (nginx gate, internal-only Postgres,
  sidecar pattern) - the design is sound; what's missing is exercising it as
  a real two-machine pair (see punch list).

### Change (modify what exists)
1. `SYSTEM_PROMPT` (`softworker/orchestrator/main.py`): add one worked
   few-shot extraction example. Every prompt fix to date has been "remove
   burden," none has been "show the model what correct extraction looks
   like." Targets the actual remaining bottleneck directly.
2. `check_consistency` (`tools.py._check_consistency`): currently validates
   a dict the model hand-constructs with **zero connection** to
   `self._extracted_texts` - a model can report fabricated numbers and get
   `"issues": []`. Cross-referencing it against real extracted text (even
   just advisory, before the hard `write_declaration_line` gate) would
   surface problems an iteration earlier.
3. Process habit: PROGRESS.md entries must land in the *same* commit as
   their code, not a catch-up commit later (this session had to fix two
   sessions' worth of doc lag - see the two commits before "Default model
   switched to qwen3:8b" above).

### Add (genuinely missing, worth building)
1. **Highest-value, untried:** hybrid structured/regex pre-parse for
   templated synthetic-document fields (`cn_code`, `quantity_tonnes`,
   `installation_name`, etc. - M1's generator produces fixed templates, not
   free prose). Parse deterministically first, fall back to the LLM only
   when parsing fails. The one lever that doesn't depend on the model
   getting better at reading.
2. Wire `tool_call_turns`/`reasoning_turns` (added this session,
   `agent_loop.py`/`main.py`) into `run_evaluation.py`'s report generator -
   currently only visible via the live job-status API, not in the
   `docs/evaluation*.md` reports that actually get cited as the project's
   numbers.
3. Real two-machine Tailscale mesh verification - softworker has run alone
   on real hardware (no sidecar, using the host's own tailnet identity);
   hardworker has never joined it in that configuration. Still open.
4. The full live evaluation itself: `qwen3:8b` (new default) +
   `source_quote` gate + the observability counters, all still unexercised
   together against a live model. This is what turns every item above from
   "should help" into "measured, did/didn't help." **This is the actual
   next action once back at the hardworker.**
5. (Lower priority, optional) `qwen2.5:14b-instruct` against the fixed
   harness - still untested since M4, `qwen3:8b` already looks solid enough
   that this may not be worth the time.

### Eliminate (drop or stop doing)
1. The checklist/todo-list planning idea - see rejection rationale above.
   Don't build it without new evidence of a failure mode it would actually
   fix.
2. Further generic "optimize the architecture" passes as a default
   activity - that vein is mined out (five sessions: real bug every time,
   then real bugs zero times). The remaining gap is read-accuracy,
   addressed by Add #1, not by more plumbing review.
3. (Weak, reconsider don't necessarily cut) `request_missing_data` -
   a no-op acknowledgment tool with no observed effect anywhere in the eval
   history. Candidate to drop only if deliberately shrinking the model's
   decision surface further; not a strong recommendation on its own.

**First concrete step next session:** Add #4 (the live evaluation run) is
the unlock everything else depends on for real evidence - Change #1/#2 and
Add #1/#2 are all cheap enough to implement locally first (no hardworker
needed) so they're ready to be included in that same run, rather than
doing them one experiment at a time.

---

## Architecture Reference

```
Hardworker                          Softworker
─────────────────────              ───────────────────────────────
Tailscale sidecar                  Tailscale sidecar
nginx:8443 (API key gate)  ←───── orchestrator (FastAPI)
Ollama (LLM inference)             Odoo 17 (cbam module)
                                   PostgreSQL 16 (internal only)
```

**Data flow for one declaration:**
1. User uploads supplier document in Odoo UI → clicks "Process with AI"
2. Odoo → `POST /jobs` to orchestrator → `job_id` returned immediately
3. Odoo polls `GET /jobs/{job_id}/status` every 5s
4. Orchestrator runs agent loop: LLM calls tools in any order it decides
5. LLM calls `write_declaration_line` when confident → orchestrator writes to Odoo via RPC
6. Odoo polls → sees `completed` → reloads the declaration line record
7. `cbam_source_document.raw_llm_output` stores full tool-call trace (audit trail)

---

## Key Constraints (do not change)

- **No LangChain / AutoGen / CrewAI** — plain Python loop with `openai` client → Ollama `/v1` endpoint
- **Zero business logic in orchestrator** — the LLM decides all tool ordering
- **Deterministic calc engine** — zero LLM involvement in compliance calculations
- **Steel & aluminium: direct emissions only** (Annex II of Reg 2023/956 — indirect/electricity not priced)
- **Versioned emission factors** — never hardcoded; always queried with `valid_from`/`valid_to` filter
- **50 t/year exemption** — `is_exempt()` must be called before any certificate calculation
- **Iteration cap** — 8–10 iterations max; exhaustion → auto-call `flag_for_human_review`
