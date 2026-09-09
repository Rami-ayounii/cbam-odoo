# M4 / M3-live / M6-live / M9-real — Bringing the agent loop up against real infra

*Date: 2026-09-06*

## Context

Per `docs/PROGRESS.md`, M0-M9 were all "built" in a prior dev sandbox with no
Docker, no GPU, and no Ollama — so M4 (LLM container), the live-Odoo half of
M3, the live half of M6, M7 (real emission-factor numbers), and the real run
of M9 were all blocked. 108 tests pass against mocked/fake Odoo and LLM
boundaries; nothing has run against real infra yet.

The current machine is different from that sandbox: it has Docker Desktop
(daemon not yet started), the `ollama` CLI installed natively, and an NVIDIA
RTX 5070 (12GB VRAM). This machine will act as **Hardworker** (GPU / LLM
host), matching the GPU placement. A second Windows machine exists as the
intended **Softworker** (Odoo host) but is not reachable this session.

M7 (pinning down real JRC134682 / EUR-Lex emission-factor and benchmark
numbers) is explicitly **out of scope** for this pass — it's a primary-source
research task, not an infra task, and deserves its own focused session per
the project's own "never invent a number" rule.

## Goal

Get real, non-mocked evidence for:
- **M4** — a real Ollama container running on Hardworker, a tool-calling model
  chosen by actual benchmarking (not the model card), nginx API-key gate
  verified for real.
- **M3 (live half)** — the `cbam` Odoo module actually installs and loads in
  a real Odoo 17 instance, not just `py_compile`/XML-parse clean.
- **M6 (live half)** — the orchestrator's agent loop actually drives a real
  local model through a real tool-use loop against a real (disposable) Odoo
  instance, ending in a real declaration-line write.
- **M9 (real run)** — `run_evaluation.py` executed for real against the
  synthetic corpus with the chosen model, producing genuine accuracy numbers
  in `docs/evaluation.md` (this repo currently has none — good, that was the
  right call last time; now it's time to actually produce them).

## Non-goals

- M7's real emission-factor/benchmark numbers — separate session.
- Standing up the real cross-machine Tailscale mesh against Softworker — not
  reachable. The real `hardworker/docker-compose.yml` / `softworker/docker-compose.yml`
  Tailscale topology stays as-is, unmodified, for when Softworker is available.
- Any change to the decided architecture (no LangChain, zero orchestrator
  business logic, deterministic calc engine, etc.) — those constraints hold.

## Approach

### 1. Hardworker bring-up (M4)

Benchmark candidates natively via the already-installed `ollama` CLI
(`ollama serve`), not by pulling every candidate into a Docker volume too —
same inference engine, and pulling 3 models twice (~5-9GB each) wastes
bandwidth/disk for no extra signal.

Candidates (all fit the 12GB VRAM budget comfortably):
- `qwen2.5:7b-instruct`
- `qwen2.5:14b-instruct`
- `llama3.1:8b-instruct`

For each: run 10 tool-calling attempts against the real
`shared/tool_schemas/*.json` schemas with a realistic CBAM extraction prompt
(reuse one of the synthetic documents). Score valid-JSON-tool-call rate and
latency. Write the winner + methodology to `docs/model-benchmark.md`.

Once a winner is picked: bring up the **actual**
`hardworker/docker-compose.yml` (Ollama + nginx sidecar) unmodified, pull only
the winning model into it, and verify the nginx API-key gate for real:
`curl` with a bad `X-Api-Key` → 401, correct key → reaches Ollama. This
satisfies M4 step 5 without re-benchmarking inside Docker.

### 2. Temporary local Odoo stack (M3 live verification)

New file: `docker-compose.local-dev.yml` at repo root — a **committed**,
clearly-labeled dev-only stack combining Odoo 17 + Postgres 16 + the
orchestrator, wired to reach the Hardworker Ollama/nginx container over
`localhost`, with no Tailscale sidecar (plain Docker bridge network,
ports exposed on localhost only). Header comment makes explicit this is
**not** the deployment topology — see `hardworker/docker-compose.yml` /
`softworker/docker-compose.yml` for the real two-machine setup.

Bring it up, install the `cbam` module, and fix whatever the ORM registry
actually complains about (per M3's own caveat that this was never done).
Add minimal, clearly-fake, round-number reference data (one production
route, one good, one emission factor, one year parameter) purely to
exercise the flow — never presented as real CBAM numbers, kept in a
separate `shared/data/dev_fixtures.py`-style file (or inline in a setup
script), distinct from M7's real-data seed file
(`shared/data/seed_emission_factors.py`), which keeps refusing to write
while placeholders remain.

### 3. Real M6 run

Run the orchestrator directly via `uvicorn` (not containerized, for fast
iteration/debugging) pointed at the real local Odoo (via `odoorpc`) and the
real Ollama-through-nginx endpoint. Feed it one synthetic document from
`shared/synthetic_data/output/`, `POST /jobs`, poll `GET /jobs/{id}/status`
to completion, confirm the model drives a real tool-use loop and a
declaration line actually gets written. Capture the full tool-call trace
(already stored via `cbam_source_document.raw_llm_output`) as evidence.

### 4. Real M9 evaluation

Run `shared/evaluation/run_evaluation.py` for real (real `LLMClient`, real
model, real tool dispatch — not the injected-script LLM the current smoke
test uses) over synthetic records (target: the ~20 the original plan called
for, capped by what's actually feasible time-wise against a local model).
Write results to `docs/evaluation.md`.

### 5. Wrap-up

Update `docs/PROGRESS.md`: M3 → live-verified, M4 → done, M6 → live-verified,
M9 → real numbers recorded. M7 stays open. Commit.

## Testing / verification plan

- Existing 108 tests must still pass unchanged (`pytest softworker/tests/ shared/ -q`).
- Model benchmark: raw pass/fail counts per candidate recorded in
  `docs/model-benchmark.md`, not just a verdict.
- nginx gate: actual `curl` output (401 / 200) pasted as evidence, not
  described.
- Odoo module install: actual Odoo startup log showing no traceback,
  module listed as installed.
- M6 live run: actual job status JSON showing `status: completed` (or
  `escalated`, if the model doesn't converge — a legitimate, documented
  outcome per the iteration-cap design) and the resulting declaration line's
  field values.
- M9: `docs/evaluation.md` numbers must come from an actual
  `run_evaluation()` execution, not estimated.

## Open risk

Small local models (7-8B, quantized) may not converge reliably on
tool-calling — this is explicitly anticipated in `projecthandoff.md` §7 as a
known failure mode, not a sign something is broken. If all three candidates
benchmark poorly, the fallback is to document the failure rate honestly and
still exercise the iteration-cap → `flag_for_human_review` escalation path
as a legitimate M6 verification outcome.
