# CBAM Odoo Module — Academic Project Handoff

## 1. What this project is

Academic project (no commercial/production use, no money changes hands). Goal:
integrate a module into Odoo that calculates a CBAM (Carbon Border Adjustment
Mechanism, EU regulation) declaration for imports of **steel and aluminium**
only. The interesting technical contribution is the architecture: the
compliance calculation runs on one machine, a locally-hosted LLM running on a
**separate machine** handles document extraction and process orchestration,
the two communicate over a private network, and the orchestration layer is a
genuine **agentic tool-use loop**, not a hardcoded pipeline.

Author's background/specialty: system design and agentic AI. The project
should showcase both, not just "connect an LLM to Odoo."

## 2. Regulatory grounding (do not skip this — it drives the data model)

- CBAM entered its **definitive phase on Jan 1, 2026**. Declarations are now
  **annual**, not quarterly (first annual declaration due 30/09/2027 for
  2026 imports). A binding 50-tonne/year exemption applies.
- Default emission values are **not static** — from 2026 they're set per
  exporting country + a yearly markup (10% in 2026, rising through 2028) via
  an implementing act that gets revised. **Never hardcode these values in
  code.** Model them as a versioned reference table.
- Sources to pull actual numbers from (do not invent numbers):
  - JRC134682 — Vidovic, Marmier, Zore, Moya (2023), "Greenhouse gas emission
    intensities of the steel, fertilisers, aluminium and cement industries,"
    DOI 10.2760/359533 (publications.jrc.ec.europa.eu)
  - taxation-customs.ec.europa.eu/cbam — official implementing act default
    values, updated periodically
  - Regulation (EU) 2023/956, Annex I — authoritative CN code scope (verify
    the full steel/aluminium code list here, don't trust any partial list
    handed to you including this doc)

## 3. Scope decisions already made

- Sectors: **steel and aluminium only** (not fertilizers/cement/hydrogen/electricity)
- Data: no real company data available — using synthetic data (generator
  already built, see `shared/synthetic_data/`)
- The LLM **never computes the compliance number**. Calculation is
  deterministic Python. LLM only does extraction, reconciliation reasoning,
  and tool-selection.
- Relevance to Tunisia (not required for the code, but relevant context):
  Tunisia exports steel/aluminium/phosphate products to the EU and is
  directly affected by CBAM reporting requirements from EU-side importers.



## 4. Architecture — two machines, Docker, Tailscale

```
Hardworker (LLM host, has/may have GPU)          Softworker (Odoo host)
┌─────────────────────────────┐   Tailscale    ┌──────────────────────────────┐
│ tailscale sidecar container │◄──── VPN ─────►│ tailscale sidecar container  │
│  ├─ ollama (LLM inference)  │  (encrypted,   │  ├─ postgres                 │
│  └─ nginx (API-key gate)    │   private,     │  ├─ odoo + custom addon      │
└─────────────────────────────┘   mesh net)    │  └─ orchestrator (agent loop)│
                                                └──────────────────────────────┘
```

- Networking: Tailscale (mesh VPN, WireGuard-based), sidecar pattern —
  app containers use `network_mode: service:tailscale` to share the tunnel
  without public exposure. ACLs restrict Softworker → Hardworker:8443 only,
  nothing else, nothing in reverse.
- Plan B if Tailscale is unavailable (blocked network, no third-party
  dependency wanted): self-hosted WireGuard, static tunnel IPs, manual
  keypair exchange. Fallback if same LAN: static IPs + firewall rule, no VPN.
- Auth: nginx in front of Ollama checks an `X-Api-Key` header. Never expose
  the raw Ollama API on the tailnet without this.
- Config files already produced: `docker-compose.hardworker.yml`,
  `docker-compose.softworker.yml`, `nginx.conf`, `tailscale-acl-example.json`
  (attach these to the repo under `hardworker/` and `softworker/` respectively).
- **Deviation, decided 2026-09-09 (see `docs/PROGRESS.md`):** the Softworker
  no longer runs its own Tailscale sidecar container. The Tailscale admin
  console's key-generation page produced auth keys the real control server
  rejected outright (root cause not found, worth reporting to Tailscale
  support); since the Softworker's physical host already had its own,
  separately-authenticated Tailscale connection, `softworker/docker-compose.yml`
  was changed to publish Odoo/orchestrator ports to the host instead of
  joining a dedicated sidecar identity. Consequence: `tailscale-acl-example.json`'s
  `tag:cbam-odoo-host`/`tag:cbam-llm-host` scheme does not apply to the
  Softworker as actually deployed — reachability depends on whatever ACLs
  apply to the host's own node. Revisit the sidecar approach once the admin
  console issue is understood; nothing about the Hardworker side changed.

## 5. Repo structure (monorepo, decided)

```
/hardworker/
    docker-compose.yml         (LLM + nginx gate)
    nginx.conf
    llm/                       (any custom Modelfile / prompts for the model)
/softworker/
    docker-compose.yml         (odoo + postgres + orchestrator)
    addons/cbam/               (the Odoo module itself)
    orchestrator/               (FastAPI agent-loop service, Dockerfile)
/shared/
    synthetic_data/            (generator script, already built)
    tool_schemas/              (JSON schemas for the agent's tools — must be
                                identical on both sides, hence "shared")
/docs/
    this file, architecture notes, decision log
```

## 6. Odoo data model (module `cbam`)

```
cbam.installation        name, country, sector, production_route_id
cbam.production.route    code (BF-BOF / EAF_scrap / EAF_DRI / primary_electrolysis /
                          secondary_recycled), sector
cbam.good                 cn_code, description, sector, is_complex_good
cbam.emission_factor      sector, production_route_id, country, direct_ef, indirect_ef,
                          markup_pct, source_document, valid_from, valid_to
                          -> VERSIONED. Calc engine looks up the record valid on the
                          declaration date. Never hardcode a factor in code.
cbam.declaration          declarant_id, reporting_year, status, submission_date
cbam.declaration.line     good_id, installation_id, quantity_tonnes, data_source
                          (actual/default), direct/indirect_emissions_actual,
                          emission_factor_id, carbon_price_paid_origin,
                          precursor_emissions, embedded_emissions_total (computed,
                          Python, deterministic), certificates_required (computed)
cbam.source_document      declaration_line_id, attachment, extraction_status,
                          raw_llm_output (json) — audit trail, keep the LLM's
                          extraction traceable
```

## 7. The agentic layer — this is the part that must be built correctly

**Not a hardcoded pipeline.** The orchestrator gives the LLM a fixed toolset
and a goal; the model decides which tool to call, in what order, in a loop,
until it has a complete answer or escalates. This is the actual "agentic AI"
contribution of the project — be precise about this distinction in any
write-up (workflow = predefined code path; agent = model directs its own
tool use).

Tools to expose to the model:
- `extract_field(document, field_name)` — LLM-powered extraction
- `lookup_default_value(sector, route, country)` — deterministic DB lookup
- `check_consistency(extracted_data)` — deterministic validation rules
- `request_missing_data(field_name)` — flags a gap back to a human/Odoo
- `flag_for_human_review(reason)` — escalation path
- `calculate_emissions(data)` — calls the deterministic calc engine; the
  model decides *when* to call this, never computes the number itself
- `write_declaration_line(data)` — single final write, called once, at the
  end of the loop

**Critical clarification — who decides what, exactly:**
The word "orchestrator" in this doc refers to a thin FastAPI service whose
only job is to run a loop and execute whatever tool the model names. It
contains **zero business logic about ordering**. There is no `if` statement
anywhere that says "call extract before calculate" or "check consistency
after extraction." The **LLM itself** is the decision-maker at every turn —
it sees the current state (conversation history + prior tool results) and
picks which tool to call next, including calling the same tool twice, calling
tools in an order nobody anticipated, or deciding it's done and returning a
final answer. This is the actual "full agent, not a pipeline" requirement —
build it exactly like this, not as a workflow with an LLM step bolted on:

```python
messages = [system_prompt, task_description]

for i in range(MAX_ITERATIONS):
    response = llm.chat(messages, tools=TOOL_SCHEMAS)

    if not response.tool_calls:
        break  # the MODEL decided it's done — not the loop, not a step counter

    for call in response.tool_calls:
        # execute_tool does NOT decide which tool runs or in what order —
        # it purely executes whatever the model named, with the args the
        # model provided. All decision-making happened inside llm.chat().
        result = execute_tool(call.name, call.args)
        messages.append(tool_result_message(call.id, result))

# response.content here is the model's final answer, reached via
# whatever tool sequence IT chose — not a sequence you wrote in code
```

If you (or Claude Code, later) end up writing something like
`if step == "extract": ... elif step == "validate": ...` anywhere in the
orchestrator, that's the anti-pattern — it means the ordering logic leaked
back into code instead of staying inside the model's decisions, and the
system has quietly turned back into a workflow.

Design constraints (non-negotiable, decided already):
- Hard iteration cap (8–10 loops) with fallback to human review if not
  converged — small local models (7–8B) don't always converge cleanly on
  tool-calling; this is a known, expected failure mode, plan for it.
- **Read-only** access to Odoo during the loop. **Single write** at the end,
  validated by Odoo before commit. Do not let the agent write mid-loop.
- Calculation stays deterministic Python regardless of what the agent decides.

## 8. Tech stack (all free/open-source — zero budget, consistent with academic scope)

- Odoo 17 Community + PostgreSQL 16
- Ollama or vLLM for local inference; candidate models: Qwen2.5-instruct or
  Llama 3.1/3.3-instruct, 7–8B, quantized (Q4) — test tool-calling
  reliability empirically before committing, don't trust the model card
- FastAPI for the orchestrator/agent-loop service
- Docker + Docker Compose, Tailscale for cross-machine networking
- Faker + numpy/pandas for synthetic data (already built)

## 9. Build order (dependency-driven, don't skip ahead)

1. M0 — networking (Tailscale, both machines can reach each other)
2. Synthetic data generator (already done)
3. Calc engine — build and unit-test standalone against synthetic data,
   **zero LLM involvement**, verify against a hand-calculated example first
4. Odoo module (models, views, report template) wired to the calc engine
5. LLM inference container (Hardworker) — get it running and reachable
6. Orchestrator agent loop — only once steps 3 and 5 both work independently
7. Versioned emission factor data load (real JRC/implementing act values)
8. Security hardening (ACLs, API keys, Odoo record rules)
9. Evaluation — measure extraction accuracy against known synthetic ground
   truth; this is a real academic contribution, most similar projects skip it

## 10. Full dependency & tooling list — install these

**System-level, both machines**
- Docker Engine + Docker Compose v2
- Git
- Tailscale client (`curl -fsSL https://tailscale.com/install.sh | sh`), or
  WireGuard tools if using Plan B

**Hardworker (LLM host)**
- Ollama — run as the `ollama/ollama` Docker image already in
  `docker-compose.hardworker.yml`, no separate native install needed
- If an NVIDIA GPU is present: NVIDIA drivers + `nvidia-container-toolkit`
  on the host, and uncomment the GPU block in the compose file. If no GPU,
  leave commented, expect CPU inference to be slow (unmeasured estimate:
  low single-digit to ~10 tokens/sec depending on CPU) — benchmark before
  assuming it's usable for a multi-step agent loop
- Pull at least two candidate models to benchmark tool-calling reliability
  before picking one, don't assume from the model card:
  - `ollama pull qwen2.5:7b-instruct`
  - `ollama pull llama3.1:8b-instruct`
- nginx — already the `nginx:latest` image in the compose file, no separate install

**Softworker (Odoo host)**
- Odoo 17 Community — `odoo:17` Docker image, already in
  `docker-compose.softworker.yml`
- PostgreSQL 16 — `postgres:16` Docker image, already in the compose file
- Orchestrator service — Python 3.11+, install via its own
  `requirements.txt`:
  ```
  fastapi
  uvicorn[standard]
  httpx
  pydantic>=2
  python-dotenv
  openai            # points at Ollama's OpenAI-compatible endpoint, not OpenAI's API
  tenacity          # retry/backoff for the agent loop
  odoorpc           # cleaner than raw xmlrpc.client for calling Odoo's API
  ```
- Odoo custom module (`addons/cbam`) — keep it dependency-free in
  `__manifest__.py` beyond Odoo's bundled libraries; no external Python
  packages should be required just to run the module

**Agent framework decision — explicit, don't second-guess this later**
Build the tool-use loop as plain Python using the `openai` client library
pointed at Ollama's `/v1`-compatible endpoint with JSON-mode/function-calling.
**Do not add LangChain, AutoGen, or CrewAI.** For a small, fixed toolset like
this, a framework adds indirection and an extra dependency surface without
real benefit, and it makes the deterministic-calculation boundary harder to
explain and audit in front of a jury. A ~150-line custom loop is more
defensible and easier to reason about than a framework's black-box agent
executor.

**Testing / dev tooling (not part of the runtime, but needed to build this)**
- `pytest` — unit tests for the calc engine (build these first, before any LLM code)
- `pytest-asyncio` — if the orchestrator uses async FastAPI routes
- `curl` or Postman — manual endpoint testing during development
- VS Code with the Docker extension, or any editor — no hard requirement
- pgAdmin or DBeaver (optional) — inspecting Postgres data directly during debugging

## 11. Open items — not yet decided, answer these before/while coding

- Exact hardware on Hardworker (GPU or not, VRAM) — determines model choice
- Whether any real (anonymized) supplier documents will be used for testing,
  or synthetic data only throughout

**Resolved since this doc was written:**
- Odoo version — confirmed 17 (`"version": "17.0.1.0.0"` in
  `softworker/addons/cbam/__manifest__.py`).
- Sync vs async call pattern — resolved as recommended: `POST /jobs` returns
  a `job_id` immediately, `GET /jobs/{job_id}/status` polls it, the agent
  loop itself runs in a `BackgroundTasks` task. Routes are plain `def`, not
  `async def` (FastAPI's threadpool handles that), so no `pytest-asyncio`
  dependency was needed.