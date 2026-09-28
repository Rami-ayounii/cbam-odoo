# Internship Journal

| | |
|---|---|
| **Intern** | Rami AYOUNI |
| **Host organisation** | ninety. Startup House — Rte Mahdia KM 1.5, El Bosten, Sfax, Tunisia |
| **Supervisor** | _(to fill in)_ |
| **Period** | 06/07/2026 → 29/08/2026 (8 weeks, Monday to Friday) |
| **Subject** | Agentic AI for automated EU CBAM compliance declarations in Odoo 17 |

---

## Overview

| Week | Dates | Main theme |
|---|---|---|
| 1 | 06/07 → 10/07 | Onboarding, CBAM regulation study, Odoo discovery |
| 2 | 13/07 → 17/07 | State of the art, requirements analysis, system design |
| 3 | 20/07 → 24/07 | Infrastructure scaffold, synthetic document generator |
| 4 | 27/07 → 31/07 | Calculation engine, Odoo `cbam` module, tool schemas, agent loop |
| 5 | 03/08 → 07/08 | Evaluation harness, model benchmark, first live end-to-end run |
| 6 | 10/08 → 14/08 | Debugging the agentic pipeline, real regulatory reference data |
| 7 | 17/08 → 21/08 | Field-accuracy improvements, model comparison, deployment |
| 8 | 24/08 → 28/08 | Final model, hybrid extraction, 50-record validation, report |

---

## Week 1 — Onboarding and domain study (06/07 → 10/07)

### Monday 06/07/2026
- Welcome at ninety. Startup House: introduction to the team, the workspace and the internal rules.
- Presentation of the internship subject: automating CBAM (Carbon Border Adjustment Mechanism) declarations for steel and aluminium imports with an AI agent integrated into Odoo.
- Set up the development environment: Git, Python, Docker Desktop, WSL2.

### Tuesday 07/07/2026
- Studied Regulation (EU) 2023/956 which establishes CBAM: its purpose, the goods it covers (Annex I), and its scope for steel and aluminium (CN codes).
- Learned the difference between the transitional phase (2023–2025) and the definitive phase that started on 1 January 2026 (annual declarations, 50-tonne exemption).

### Wednesday 08/07/2026
- Studied how the reference data is published: default emission values per country and production route, the yearly markup, the Commission Implementing Regulations 2025/2621 and 2026/1412.
- Read the JRC134682 report, the scientific basis for the default values.
- Studied the phase-out of free allocation (Directive 2003/87/EC, Art. 10a) and the EU ETS benchmarks.

### Thursday 09/07/2026
- Worked out the calculation formulas for steel and aluminium: embedded emissions (actual or default values), precursor emissions, benchmark deduction, number of CBAM certificates, carbon price already paid in the country of origin.
- Wrote the formulas document (`CBAM_Formulas_Steel_Aluminium`).

### Friday 10/07/2026
- Discovered Odoo 17: installed a local instance, explored the module structure, the ORM, models, views and access rights.
- Tested Odoo's external API (XML-RPC / `odoorpc`) to read and write records from a Python script.

---

## Week 2 — State of the art, analysis and design (13/07 → 17/07)

### Monday 13/07/2026
- Literature review on LLM-based agents: the ReAct paradigm (reasoning + acting), native function calling / tool use, multi-step planning.
- Read about LLM hallucination risks and why they matter for numeric compliance work.

### Tuesday 14/07/2026
- Reviewed existing approaches to compliance document automation (manual processing, rule-based extraction, fixed LLM pipelines) and their limits.
- Wrote the critique of the state of the art and the problem statement.

### Wednesday 15/07/2026
- Requirements specification: functional requirements (document extraction, lookup of default values, calculation, declaration writing, escalation to a human) and non-functional ones (privacy with a local LLM, security, traceability).
- Identified the actors and drew the use case diagram.

### Thursday 16/07/2026
- Designed the architecture on two machines: **hardworker** (LLM host, Ollama behind an nginx API-key gate) and **softworker** (Odoo 17 + PostgreSQL + orchestrator), connected through a private Tailscale network.
- Key design decision: the compliance numbers are always computed by a deterministic Python engine, never by the LLM. The LLM only reads documents and decides which tool to call next.
- Wrote the project handoff document (`projecthandoff.md`).

### Friday 17/07/2026
- Designed the data model: declarations, declaration lines, versioned emission factors, goods benchmarks, installations.
- Drew the sequence diagram of an agent job (document → tool calls → Odoo write).
- Split the project into milestones M0 → M9.

---

## Week 3 — Infrastructure and synthetic data (20/07 → 24/07)

### Monday 20/07/2026
- **M0 — repository scaffold:** created the repository structure (`hardworker/`, `softworker/`, `shared/`, `docs/`).
- Wrote the Docker Compose files: Ollama + nginx on hardworker; Odoo 17 + PostgreSQL 16 + orchestrator on softworker.

### Tuesday 21/07/2026
- Configured nginx as a security gate: `X-Api-Key` header check, rate limiting (10 req/s), streaming without buffering; the API key is injected from `.env` at startup.
- Wrote the Tailscale ACL (softworker → hardworker:8443 only), the `.env.example` files, `.gitignore` and `.gitattributes`.

### Wednesday 22/07/2026
- **M1 — synthetic data generator:** since real supplier documents are confidential, designed a generator for realistic CBAM documents (mill certificates, emission reports, supplier declarations).
- Defined difficulty levels (easy / medium / hard with missing or ambiguous fields).

### Thursday 23/07/2026
- Generated a 50-record dataset with its ground truth (expected values for every field) to be used for evaluation later.
- Wrote unit tests for the generator.

### Friday 24/07/2026
- **M2 — calculation engine:** started the deterministic calc engine: embedded emissions from actual vs default values, default values with markup.
- Wrote the first pytest tests.

---

## Week 4 — Odoo module and agent loop (27/07 → 31/07)

### Monday 27/07/2026
- Finished the calculation engine: certificate calculation, benchmark deduction with the `cbam_factor_year`, carbon price paid at origin, 50-tonne exemption.
- Full unit-test coverage of the formulas.

### Tuesday 28/07/2026
- **M3 — Odoo module `cbam`:** created the models (declaration, declaration line, emission factor, good benchmark, installation) with versioned emission factors (never hardcoded).
- Plugged the calculation engine into the module.

### Wednesday 29/07/2026
- Created the Odoo views (form, list), menus and the declaration workflow.
- **M8 — security hardening:** security groups, access rights (`ir.model.access`), record rules, dedicated API user for the orchestrator.

### Thursday 30/07/2026
- **M5 — tool schemas:** defined the tools the agent can call (`extract_field`, `lookup_default_value`, `check_consistency`, `write_declaration_line`, `escalate`…) as JSON schemas, with Pydantic validation of every argument.

### Friday 31/07/2026
- **M6 — orchestrator:** implemented the FastAPI service and the agent loop as a plain Python tool-use loop (no LangChain / AutoGen / CrewAI). The loop contains no business logic: the model decides the order of the tool calls.
- Job statuses (completed, escalated, exhausted) and iteration limit.

---

## Week 5 — Evaluation and first live run (03/08 → 07/08)

### Monday 03/08/2026
- **M9 — evaluation harness:** script that runs the agent on the synthetic records and scores each field against the ground truth.
- Full review of the code base; fixed several bugs found in the compliance rules, the orchestrator, the infrastructure and the data generator.

### Tuesday 04/08/2026
- Wrote a design spec and an implementation plan for the live verification phase (real Odoo, real LLM, real evaluation).

### Wednesday 05/08/2026
- **M4 — model selection:** wrote a real tool-calling benchmark and compared four local models (`llama3.1:8b`, `qwen2.5:7b-instruct`, `qwen3:8b`, `qwen2.5:14b-instruct`) on an RTX 5070 GPU.
- First ranking: `llama3.1:8b` had the best valid tool-call rate (50%); fixed a bug in the benchmark script.

### Thursday 06/08/2026
- Built a single-machine Docker stack (`docker-compose.local-dev.yml`) to test everything locally.
- Installed the `cbam` module in a real Odoo 17 instance; found and fixed a real bug (`odoorpc` could not serialize `datetime.date`).
- Added development fixtures (emission factors, benchmarks) to fill Odoo.

### Friday 07/08/2026
- Wrote a live smoke test script and ran the first real end-to-end job: document → LLM → tools → Odoo.
- Fixed the `X-Api-Key` header issue discovered live.
- Ran the first real evaluation: **0% field accuracy** — documented honestly in `docs/evaluation.md` as the starting point.

---

## Week 6 — Debugging the pipeline and real reference data (10/08 → 14/08)

### Monday 10/08/2026
- Analysed the 0% result: the agent often stopped without ever writing the declaration line. Added a new `no_write` status instead of reporting these jobs as "completed".
- Fixed the smoke test that returned success on a timeout; added regression tests.

### Tuesday 11/08/2026
- Improved the system prompt and the description of `write_declaration_line` to push the model towards completing the task.
- Re-ran the live tests and recorded before/after numbers.

### Wednesday 12/08/2026
- **M7 — real reference data:** researched and loaded real, cited values: EU ETS benchmarks and the 2026 markup rate.
- Found and fixed an inverted `cbam_factor_year` direction in the certificate calculation.
- Wrote the source verification document (`docs/m7-source-verification.md`).

### Thursday 13/08/2026
- Continued M7: selected countries/routes that actually have published default values (Türkiye BF-BOF, Azerbaijan EAF scrap, Bahrain primary electrolysis, Tunisia secondary recycling).
- Computed the 2026 reference certificate price from the published quarterly prices; filled in the real `cbam_factor_year` (0.025). Result: 9 of 10 reference fields now real.

### Friday 14/08/2026
- Pinned dependency versions, wrote the root README, documented assumptions.
- Audit follow-up: added a production-route dimension to benchmarks, `certificates_status` field, fixed drift between tool arguments and schemas.

---

## Week 7 — Accuracy improvements and model comparison (17/08 → 21/08)

### Monday 17/08/2026
- Field-accuracy investigation: fixed context grounding and harness fidelity bugs, reduced the tool schemas to only what the model really has to decide.
- Fixed value carryover, the constraint blocking default-sourced data, and the temperature setting → **first fully correct real write** in Odoo.

### Tuesday 18/08/2026
- Improved how extracted actual-emission values are carried into the final write.
- Ran an honest check on an unselected batch of records (0/5) to avoid over-trusting hand-picked results; found and fixed a WSL2 memory limit that was killing evaluation runs.

### Wednesday 19/08/2026
- Full 20-record evaluation after the fixes: field accuracy went from 0% to 15–20% on the reachable fields.
- Resolved the steel EAF-scrap benchmark (0.142) from the official source.

### Thursday 20/08/2026
- Model comparison on the fixed harness: `qwen2.5:7b-instruct` scored 0/10, while `qwen3:8b` tied `llama3.1:8b` — the first benchmark had under-rated it.
- Renamed the machines to hardworker / softworker and made the first real deployment on softworker.

### Friday 21/08/2026
- Required a verbatim `source_quote` from the document for every actual-sourced emission value (anti-hallucination gate).
- Added observability counters (tool calls vs reasoning turns); audited the handoff document against the code.

---

## Week 8 — Final tuning, validation and report (24/08 → 28/08)

### Monday 24/08/2026
- Re-tested `qwen2.5:14b-instruct` on the fixed harness: strongest result so far.
- Implemented hybrid regex / LLM extraction (deterministic pre-parse for fixed document formats, LLM as fallback): 86% on the hardest fields.

### Tuesday 25/08/2026
- Switched the default model to `qwen2.5:14b-instruct` and validated it on the full 50-record dataset.
- Extended the development fixtures to cover all 13 country/route combinations → final accuracy: **86%** (quantity / data source / precursors), **81%** direct emissions, **76%** indirect emissions, **64%** carbon price paid.

### Wednesday 26/08/2026
- Tested self-consistency voting: rejected (0/15 disagreements, no gain); fixed two systematic failures instead.
- Grounded `check_consistency` against the real extracted text.

### Thursday 27/08/2026
- Fixed the Tailscale sidecar configuration on hardworker; tried a few-shot prompt and rejected it after measurement.
- Updated `docs/PROGRESS.md` and all evaluation documents.

### Friday 28/08/2026
- Wrote the internship report (LaTeX) and prepared the presentation.
- Final demo to the supervisor and handover of the project.

---

## Skills and tools used

- **Languages / frameworks:** Python, FastAPI, Pydantic, Odoo 17 (ORM, XML views, security), PostgreSQL
- **AI:** Ollama, local open-weight LLMs (Llama 3.1, Qwen 2.5, Qwen 3), function calling, ReAct-style agent loop, prompt engineering, evaluation methodology
- **Infrastructure:** Docker / Docker Compose, nginx, Tailscale, WSL2, GPU inference
- **Practices:** Git, test-driven development (pytest), code review, technical documentation
- **Domain:** EU CBAM regulation, EU ETS benchmarks, embedded-emissions calculation
