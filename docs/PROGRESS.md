# CBAM Project — Progress Tracker

*Academic project: Odoo 17 + Agentic LLM (Ollama) for EU Carbon Border Adjustment Mechanism declarations.*
*Last updated: 2026-09-06*

---

## Quick Status

| Milestone | Status | Commit |
|-----------|--------|--------|
| M0 — Repo scaffold & networking | **Done** | `16ec5ec` |
| M1 — Synthetic data generator | **Done** | `58c4baa` |
| M2 — Calculation engine | **Done** | `2d89d37` |
| M3 — Odoo module (`cbam`) | **Done, live-installed** (real Odoo 17 + Postgres, no addon changes needed) | `6a2e1b4` |
| M4 — LLM inference container (Machine A) | **Done** — real benchmark, winner `llama3.1:8b` (50% valid-rate), nginx API-key gate verified for real | `9d4851a` |
| M5 — Tool schemas | **Done** | `2d89d37` |
| M6 — Orchestrator agent loop | **Done, live-verified** (first real end-to-end LLM+Odoo run; job `completed`, 3 real infra bugs found and fixed) | `b1a7d17` |
| M7 — Versioned emission factor data load | **Mechanism done, data blocked** | `2d89d37` |
| M8 — Security hardening | **Done** | `2d89d37` |
| M9 — Evaluation | **Done, real run** — 17/20 completed, 3/20 escalated, 0% field accuracy (model tool-calling limitation, not a harness bug) | `ceaf01c` |

---

## What Is Built

### M0 — Repo scaffold & networking (commit `16ec5ec`)

**Files created:**
- `machineA/docker-compose.yml` — Ollama + nginx sidecar on Tailscale network
- `machineA/nginx.conf.template` — API-key gate (`X-Api-Key` header), rate limiting (10 r/s), streaming proxy (no buffering)
- `machineB/docker-compose.yml` — Odoo 17 + PostgreSQL 16 + orchestrator placeholder on Tailscale network
- `machineA/.env.example` / `machineB/.env.example` — document all required secrets
- `tailscale-acl-example.json` — ACL restricting Machine B → Machine A:8443 TCP only (blocks reverse)
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
- `machineB/addons/cbam/utils/calc_engine.py` — the four functions below, plus `EmissionFactor` dataclass
- `machineB/tests/test_calc_engine.py` — 15 tests, all passing
- `machineB/tests/conftest.py` — adds `machineB/addons` to `sys.path` so tests import `cbam.utils.calc_engine` without the Odoo module needing a manifest yet
- `machineB/addons/cbam/__init__.py`, `machineB/addons/cbam/utils/__init__.py` — package markers (M3 will add `__manifest__.py` alongside)
- `machineB/requirements-dev.txt` — `pytest>=8.0.0`

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
# N = max(embedded_emissions_total - benchmark*cbam_factor_year*quantity_tonnes, 0)
# N_final = N * (1 - min(carbon_price_paid_origin / reference_certificate_price, 1.0)), never negative

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

**Done:** `pytest machineB/tests/test_calc_engine.py -v` → 15 passed, built test-first (RED confirmed
via `ModuleNotFoundError` before `calc_engine.py` existed, then GREEN).

**Not done yet:** committed in `2d89d37`; `benchmark`, `cbam_factor_year`, and
`reference_certificate_price` still need a real source (JRC/EU ETS benchmark decisions, the phase-out
schedule, and the published reference certificate price) — deferred to M7 alongside emission factors.

---

### M3 — Odoo module (`cbam`) (built 2026-07-30, commit `2d89d37`)

**IMPORTANT CAVEAT — not runtime-verified.** No Docker or Odoo installation
is available in this dev environment, so this module has only been checked
statically (`py_compile` on every `.py` file, `xml.dom.minidom` parse on
every view/report XML — both clean). It has **not** been loaded into a real
Odoo 17 instance. First thing to do once Machine B is up: `docker compose up`
and install the module, then fix whatever the ORM registry actually
complains about.

**Files created:**
- `machineB/addons/cbam/__manifest__.py` — depends on `base`, `mail`; no external Python packages
- `machineB/addons/cbam/models/` — `cbam_production_route.py`, `cbam_installation.py`, `cbam_good.py`, `cbam_emission_factor.py` (versioned, with an `@api.constrains` overlap guard), `cbam_year_parameter.py` (**new, not in the original data model**), `cbam_declaration.py`, `cbam_declaration_line.py`, `cbam_source_document.py`
- `machineB/addons/cbam/utils/odoo_adapters.py` — `OdooEmissionFactorSession`, the ORM-backed adapter `lookup_emission_factor()` needs; kept out of `calc_engine.py` so the calc engine stays Odoo-free and standalone-testable
- `machineB/addons/cbam/security/ir.model.access.csv` — base user (mostly read + line-level write) vs. `base.group_system` (full CRUD) for all 7 models
- `machineB/addons/cbam/views/` — `cbam_declaration_views.xml` (form embeds an editable line list with a "Lookup Default EF" button), `cbam_declaration_line_views.xml`, `cbam_source_document_views.xml`, `cbam_menus.xml` (root menu + a Configuration submenu for the 5 reference-data models, using Odoo's auto-generated views — needed so the Many2one fields have something to select, wasn't explicitly asked for but the module is unusable without it)
- `machineB/addons/cbam/reports/cbam_declaration_report.xml` — basic QWeb PDF summary (declarant, year, status, totals, one row per line)

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

### M4 — LLM inference container (Machine A) — BLOCKED in this environment

**Why blocked:** steps 1-5 below need actual Docker + a real (or at least
present) Machine A to pull and benchmark models against. This dev sandbox
has neither Docker nor an Ollama install (`docker --version` → command not
found). Nothing here is a code deliverable I can produce without live
infra - the `docker-compose.yml`/`nginx.conf.template` from M0 already
contain everything needed to run this once real hardware is available.

**Steps (unchanged from the plan, still to do on real Machine A hardware):**
1. Bring up `machineA/docker-compose.yml`
2. Pull candidate models: `qwen2.5:7b-instruct`, `qwen2.5:14b-instruct`, `llama3.1:8b-instruct`
3. Benchmark tool-calling reliability (10 attempts each with a JSON tool schema) — does the model return valid JSON calls consistently?
4. Pick the winner, document in `docs/model-benchmark.md`
5. Verify nginx: `curl -H "X-Api-Key: wrong" https://machineA:8443/` → 401

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

**Files created (all in `machineB/orchestrator/`):**
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
- `machineB/tests/conftest.py` now also adds `machineB/orchestrator` to `sys.path`, alongside the existing `cbam/utils` entry, so tests can `import agent_loop`, `tools`, etc. as bare modules too.
- `docker-compose.yml`'s `orchestrator` service build `context` changed from `./orchestrator` to `.` (machineB/), because the Dockerfile needs to `COPY addons/cbam/utils/calc_engine.py` in alongside the orchestrator's own files - a path outside the old, narrower build context. `dockerfile:` updated to `orchestrator/Dockerfile` to match.

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

**Done:** `pytest machineB/tests/ -q` → 41 passed (15 M2 + 11 tools + 7 agent_loop + 3 llm_client + 5 main).

**Not done:** committed in `2d89d37`; no live LLM or Odoo was ever contacted; `SYSTEM_PROMPT` is a first draft, unrefined by any actual model behavior since M4 is blocked; in-memory job store has no persistence (acceptable for this academic scope, flagged as a known limitation).

**Correctness/security review (2026-07-31) — 3 real bugs found and fixed, all in `machineB/orchestrator/`:**
1. `odoo_client.py` `write_declaration_line()` called `model.create(data)`, always creating a brand-new, disconnected `cbam.declaration.line` instead of updating the job's own `declaration_line_id` (the line the source document is attached to and the one Odoo's UI reloads per this doc's own data-flow step 6). Fixed to `model.write([declaration_line_id], data)`, with `declaration_line_id` supplied from the job's own scope (`tools.py`), never from the LLM - same reasoning as the existing `declaration_id` check.
2. `tools.py` `ToolDispatcher` had no guard against `write_declaration_line` being called more than once in a job - `agent_loop.py` only treats `flag_for_human_review` as a loop terminator, so nothing stopped a non-converging model from writing twice, violating section 7's "single write... do not let the agent write mid-loop." Added a one-shot flag on the dispatcher (not tool-ordering logic - it doesn't constrain what runs before/after, only refuses to repeat the one side-effecting call).
3. `llm_client.py` did a bare `json.loads(call.function.arguments)` with no handling for malformed JSON - a real, expected failure mode for 7-8B models that this doc already anticipates for tool-calling generally. This raised `json.JSONDecodeError` straight out of `chat()`, uncaught by the tenacity retry (not a retryable error type) and uncaught by `agent_loop.py`, crashing the whole job instead of giving the model a chance to self-correct. Fixed to fall back to a placeholder args dict that Pydantic's existing `tool_args.py` validation rejects the same way it already rejects any other malformed tool call - fed back to the model as a tool error, not a crash.

Architectural compliance re-verified: the only tool-name branch in `agent_loop.py` is still the documented `flag_for_human_review` termination check; tool execution order within a turn is preserved (not resorted); Odoo stays read-only until the single write. 3 new/updated tests added (`test_tools.py` x2, `test_llm_client.py` x1); `pytest machineB/tests/ -q` → 70 passed after the fixes (no existing test's expectations changed).

---

### M7 — Versioned emission factor data load (mechanism built 2026-07-30, real data BLOCKED)

**Why blocked:** this milestone's actual deliverable is authoritative
numbers, not code, and this sandbox cannot reliably get them. Tried, in
order: (1) `WebFetch` on the EUR-Lex HTML page for IR 2025/2621 - returned
empty content both times, on two different URL formats; (2) `WebFetch` on
the JRC134682 PDF - saved the binary but the text layer is unusable
(garbled output); (3) local PDF rendering via the `Read` tool - failed,
`pdftoppm`/poppler-utils isn't installed here; (4) `WebSearch` for
secondary-source numbers - got answers, but two independent search queries
returned **contradicting numbers for the same regulation** (one claimed
steel BF-BOF benchmark 1.530 tCO2/t, DRI/EAF 1.033, scrap EAF 0.288; a
direct fetch of the actual cited article instead showed hot metal 1.248,
EAF carbon steel 0.142, EAF high-alloy 0.176 - and didn't even mention the
first set of figures). Given the project's own non-negotiable rule (never
invent a number, verify against the primary text), I stopped rather than
guess which secondary source to trust, and stopped before fetching from an
unofficial PDF mirror (`api.pks.rs`) that isn't a defensible source anyway.

**What got built instead, per your call to build the mechanism with
placeholders:**
- `shared/data/seed_emission_factors.py` - typed seed tables (`EmissionFactorSeed`, `YearParameterSeed`, `GoodBenchmarkSeed` dataclasses) for 5 emission-factor records (steel BF-BOF/FR, EAF_scrap/FR, EAF_DRI/TR; aluminium primary_electrolysis/NO, secondary_recycled/TN - TN chosen per `projecthandoff.md` §3's stated Tunisia relevance), one 2026 year-parameter record, and 2 good-benchmark records. **Every numeric field is `None`**, with an inline comment naming the exact primary source/table to pull the real value from.
- `find_incomplete_seeds()` - lists every placeholder still outstanding.
- `seed_odoo(env, allow_incomplete=False)` - **refuses to write to Odoo while any placeholder remains**, specifically so this can't accidentally seed a real declaration with fabricated numbers. `--allow-incomplete` exists only for testing the loading mechanism itself.
- `main()` - standalone CLI using `odoorpc`, matching M6's connection pattern (not run inside Odoo's own process).
- `test_seed_emission_factors.py` (5 tests, TDD'd) - every seed has a citation, `find_incomplete_seeds()` correctly flags the current all-placeholder state, `seed_odoo()` refuses by default and writes when explicitly overridden, and production-route records aren't duplicated across repeated runs.

**To actually finish this milestone:** open the primary sources directly
(not through this sandbox's tooling) - JRC134682 PDF, EUR-Lex CELEX
32025R2621, and the actual EU ETS benchmark regulation (Commission
Implementing Regulation (EU) 2026/1412 per a verified-secondary-source
mention, but confirm this number too) - and fill in each `None` in
`seed_emission_factors.py`, updating `source_document` to drop the
"PLACEHOLDER, not yet verified" suffix once confirmed.

---

### M8 — Security hardening (built/verified 2026-07-30, commit `2d89d37`)

- **8a - Odoo record rules:** `machineB/addons/cbam/security/cbam_security_rules.xml` (new) - `ir.rule` records scoping `cbam.declaration`, `cbam.declaration.line`, and `cbam.source.document` to `[('declarant_id', '=', user.partner_id.id)]` (and the equivalent traversal for the two child models) for `base.group_user` only; `base.group_system` is untouched by these rules and keeps the unrestricted access `ir.model.access.csv` already grants. Added to `__manifest__.py`'s `data` list. Not runtime-verified (same Odoo-instance caveat as M3).
- **8b - Pydantic tool-argument validation:** `machineB/orchestrator/tool_args.py` (new) - one Pydantic model per tool, mirroring `shared/tool_schemas/*.json` field-for-field (including the enums). `ToolDispatcher.execute()` now validates args through the matching model before calling the handler; a `ValidationError` becomes a `ValueError`, which `agent_loop.py` already catches and feeds back to the model as a tool error instead of crashing on a malformed call from a small model. 4 new tests added to `test_tools.py` (missing required arg, wrong type, invalid enum on two different tools) - all TDD'd (confirmed failing with `TypeError`/no-error before the validation existed).
- **8c - nginx rate limits / ACL:** reviewed, not rebuilt - M0 already has this right. `machineA/nginx.conf.template` rejects any request without a matching `X-Api-Key` (401) and rate-limits at 10 r/s with a burst of 20. `tailscale-acl-example.json` restricts Machine B → Machine A:8443 TCP only and has an explicit test asserting the reverse direction (A → B:8069/5432) is denied. `OLLAMA_BASE_URL` is documented as `http://` (not https) consistently in both nginx and `.env.example` - intentional, encryption is the Tailscale WireGuard tunnel's job, not an app-layer TLS cert nobody asked to manage.
- **8d - `.env` hygiene + secret rotation:** verified `git check-ignore -v machineA/.env machineB/.env` - both match the root `.gitignore`'s `*.env` pattern. Verified `git log --all --full-history -- '*.env'` returns nothing - no `.env` file has ever been committed. Wrote `docs/secret-rotation.md`: rotation steps for `OLLAMA_API_KEY`, `TS_AUTHKEY`, `POSTGRES_PASSWORD`, `ODOO_PASSWORD`, plus a periodic check for accidental force-adds.

**Done:** `pytest machineB/tests/test_tools.py -v` → all pass (15, incl. the 4 new ones); `.env`/git history checks passed with real commands, not assumed.

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

**Orchestrator (`machineB/orchestrator/`):** see the M6 section above for
the 3 bugs fixed there (orphan-record write, missing single-write guard,
crash on malformed LLM tool-call JSON). Additionally, `MAX_AGENT_ITERATIONS`
is now clamped to `[8, 10]` in `main.py` regardless of env misconfiguration,
matching section 7's "hard iteration cap (8-10 loops)" exactly instead of
trusting the env var unclamped. `ORCHESTRATOR_API_KEY` enforcement
(fail-closed, constant-time comparison, checked on both endpoints) was
reviewed and found already correct — no change needed.

**Infra (`machineA/`, `machineB/docker-compose.yml`, Dockerfile):** 3
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

**Verification:** `python -m pytest machineB/tests/ shared/ -q` → 108
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
meshed machines (Machine A running Ollama+nginx, Machine B running
Odoo+orchestrator). This machine has no Tailscale install and the intended
Machine B was not reachable this session, so standing up the real
cross-machine mesh was out of scope here. Instead, `docker-compose.local-dev.yml`
(new, committed, clearly header-labeled as dev-only) runs everything on this
one host — Ollama + nginx (reusing `machineA/nginx.conf.template`
byte-for-byte) + Postgres + Odoo + orchestrator — reaching each other over
`localhost` with no Tailscale sidecar. `machineA/docker-compose.yml` /
`machineB/docker-compose.yml` are unmodified and remain the real deployment
topology for when Machine B is available. Full rationale in
`docs/superpowers/specs/2026-09-06-m4-live-infra-design.md`'s "Non-goals" and
"Approach" sections.

**M4 — real model benchmark (commit `9d4851a`):** 4 candidate models
benchmarked for real against a live local `ollama serve`, 10 tool-calling
attempts each, scored against the exact production Pydantic validation in
`machineB/orchestrator/tool_args.py`. Winner: `llama3.1:8b` (the real Ollama
tag — `llama3.1:8b-instruct` from the original plan doesn't exist as a
published tag) at 50% valid-rate, ahead of `qwen2.5:7b-instruct` (40%),
`qwen3:8b` (0%), and `qwen2.5:14b-instruct` (0%, both zero-scores from
emitting multiple tool calls per turn rather than the one this benchmark
scores). Full methodology and numbers: `docs/model-benchmark.md`. The nginx
gate — `machineA/nginx.conf.template`, reused byte-for-byte by the
`docker-compose.local-dev.yml` stack described above (no Tailscale sidecar
on this host, so the real `machineA/docker-compose.yml` topology itself was
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

**Verification:** `python -m pytest machineB/tests/ shared/ -q` → 122
passed (unchanged from the count recorded in `b1a7d17`; no existing test's
expectations changed as part of this pass).

---

## Agentic completion-gap follow-up (2026-09-08)

Direct follow-up to M6/M9 above's finding — "the model calls tools but
never reaches `write_declaration_line`". The fix is text-only: the
orchestrator's `SYSTEM_PROMPT` (`machineB/orchestrator/main.py`) now states
explicitly that the task is not finished until `write_declaration_line` has
been called, tells the model to call `flag_for_human_review` rather than
just stopping when it can't converge, and tells it to gather real values via
`extract_field`/`lookup_default_value` before calling `calculate_emissions`
rather than passing placeholder/zero values. `write_declaration_line.json`'s
schema `description` gained one sentence stating the same completion signal
at the tool-schema level. Per this task's own constraint,
`agent_loop.py` and `tools.py` were not touched — confirmed with `git diff
--stat machineB/orchestrator/agent_loop.py machineB/orchestrator/tools.py`
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
This is a real behavior change from the prior `no_write`/silent-stop
finding: the model now reaches an actual terminal state via a real tool
call instead of just stopping mid-loop.

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
from `machineB/orchestrator/main.py`. This meant the first M9 re-run above
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

**Verification:** `python -m pytest machineB/tests/ shared/ -q` → 127 passed
(125 + the 2 new regression tests from this task's Step 1; no existing
test's expectations changed; unchanged after the `run_evaluation.py` prompt-
unification fix).

---

## Architecture Reference

```
Machine A                          Machine B
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
