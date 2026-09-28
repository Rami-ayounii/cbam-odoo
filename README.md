# CBAM Odoo — Agentic Declaration Assistant

Academic project by Rami Ayouni (no commercial/production use). An Odoo 17
module that calculates EU CBAM (Carbon Border Adjustment Mechanism)
declarations for steel and aluminium imports, paired with a genuine agentic
LLM loop — running on a separate machine, connected over Tailscale — that
extracts data from supplier documents and decides its own tool-call order.
The compliance math itself is always deterministic Python, never the LLM.

Full context: [`projecthandoff.md`](projecthandoff.md) (architecture,
scope, regulatory grounding). Build history and current status, milestone
by milestone: [`docs/PROGRESS.md`](docs/PROGRESS.md).

## Current status

- All milestones (M0–M9) built; the Odoo module and orchestrator have been
  live-verified end to end, including real declaration writes via the Odoo API.
- Default model: `qwen2.5:14b-instruct` (served by Ollama on hardworker),
  chosen after comparing `llama3.1:8b`, `qwen2.5:7b-instruct` and `qwen3:8b`
  on the same harness — see [`docs/model-benchmark.md`](docs/model-benchmark.md)
  and the `docs/evaluation-*.md` run reports.
- Latest full 50-record synthetic evaluation
  ([`docs/evaluation-qwen25-14b-full50-fixture-fix-2026-09-18.md`](docs/evaluation-qwen25-14b-full50-fixture-fix-2026-09-18.md)):
  86% on quantity / data source / precursor emissions, 81% on direct and 76%
  on indirect actual emissions, 64% on carbon price paid at origin.
- Anti-hallucination safeguards: actual-sourced emissions require a verbatim
  `source_quote`, and `check_consistency` checks claimed values against the
  document text actually extracted; hybrid regex/LLM extraction handles the
  hardest fields.
- Test suite: 175 passing.
- Softworker has run on real hardware; the full two-machine run over a live
  Tailscale mesh (softworker ↔ hardworker) is still pending.

## Layout

```
hardworker/     LLM host: Ollama + nginx API-key gate (host-native Tailscale)
softworker/     Odoo host: Odoo 17 + Postgres + orchestrator (agent loop)
  addons/cbam/  the Odoo module — models, views, security, calc engine
  orchestrator/ FastAPI agent-loop service (tool dispatch, LLM client,
                hybrid field extraction)
  tests/        pytest suite for the calc engine and orchestrator
shared/         tool schemas, synthetic data generator, dev fixtures,
                evaluation harness
scripts/        Odoo init/seed script, live smoke test
docs/           milestone progress, evaluation runs, source verification
```

## Running the tests

```
pip install -r softworker/orchestrator/requirements.txt -r softworker/requirements-dev.txt -r shared/synthetic_data/requirements.txt
python -m pytest softworker/tests/ shared/ -q
```

## Running the stack locally (single machine)

```
docker compose -f docker-compose.local-dev.yml --env-file .env.local-dev up -d
python scripts/init_local_dev_odoo.py
```

The init script creates the `cbam` database, installs the module and seeds
the dev fixtures. See [`docker-compose.local-dev.yml`](docker-compose.local-dev.yml)'s
header comment for how this differs from the real two-machine topology
(`hardworker/docker-compose.yml` + `softworker/docker-compose.yml`).

## Two-machine deployment

Each host runs its own native Tailscale client; the containers publish their
ports to the host instead of using a Tailscale sidecar (the admin console's
generated auth keys were rejected by the control server — see the compose
file headers and `docs/PROGRESS.md`). Copy each directory's `.env.example`
to `.env`, set `OLLAMA_BASE_URL` on softworker to hardworker's tailnet
address, then `docker compose up -d` in `hardworker/` and `softworker/`.

## Key constraints (see `docs/PROGRESS.md` for the full list)

- No LangChain/AutoGen/CrewAI — a plain Python tool-use loop
- Zero business logic in the orchestrator; the LLM decides all tool ordering
- Deterministic calc engine, zero LLM involvement in the compliance number
- Versioned emission factors — never hardcoded
- Steel & aluminium: direct emissions only; 50 t/year exemption checked first
