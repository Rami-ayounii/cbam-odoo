# CBAM Odoo — Agentic Declaration Assistant

Academic project (no commercial/production use). An Odoo 17 module that
calculates EU CBAM (Carbon Border Adjustment Mechanism) declarations for
steel and aluminium imports, paired with a genuine agentic LLM loop —
running on a separate machine, connected over Tailscale — that extracts
data from supplier documents and decides its own tool-call order. The
compliance math itself is always deterministic Python, never the LLM.

Full context: [`projecthandoff.md`](projecthandoff.md) (architecture,
scope, regulatory grounding). Build history and current status, milestone
by milestone: [`docs/PROGRESS.md`](docs/PROGRESS.md).

## Layout

```
machineA/       LLM host: Ollama + nginx API-key gate, Tailscale sidecar
machineB/       Odoo host: Odoo 17 + Postgres + orchestrator (agent loop)
  addons/cbam/  the Odoo module — models, views, security, calc engine
  orchestrator/ FastAPI agent-loop service (tool dispatch, LLM client)
  tests/        pytest suite for the calc engine and orchestrator
shared/         tool schemas, synthetic data generator, evaluation harness
docs/           milestone progress, evaluation runs, source verification
```

## Running the tests

```
pip install -r machineB/orchestrator/requirements.txt -r machineB/requirements-dev.txt -r shared/synthetic_data/requirements.txt
python -m pytest machineB/tests/ shared/ -q
```

## Running the stack locally (single machine, no Tailscale)

```
docker compose -f docker-compose.local-dev.yml --env-file .env.local-dev up -d
```

See [`docker-compose.local-dev.yml`](docker-compose.local-dev.yml)'s header
comment for how this differs from the real two-machine topology
(`machineA/docker-compose.yml` + `machineB/docker-compose.yml`), which is
the target deployment shape but has not yet been verified over a live
Tailscale mesh.

## Key constraints (see `docs/PROGRESS.md` for the full list)

- No LangChain/AutoGen/CrewAI — a plain Python tool-use loop
- Zero business logic in the orchestrator; the LLM decides all tool ordering
- Deterministic calc engine, zero LLM involvement in the compliance number
- Versioned emission factors — never hardcoded
