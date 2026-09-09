# scripts/run_m6_live_smoke_test.py
"""Drives one real synthetic document through the real orchestrator, real
local-dev Odoo, and real Ollama - the M6 live verification that has never
happened before (docs/PROGRESS.md's M6 section: "no live LLM or Odoo was
ever contacted"). Writes docs/m6-live-verification.md with the actual
job/line/trace evidence. Not a pytest file - this exercises real running
infra (docker-compose.local-dev.yml), nothing here is meaningfully
mockable without defeating the point.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "softworker" / "addons" / "cbam" / "utils"))
sys.path.insert(0, str(REPO_ROOT / "shared" / "data"))

import odoorpc  # noqa: E402

from dev_fixtures import (  # noqa: E402
    create_dev_declaration_line_with_document,
    seed_dev_fixtures_odoo,
)

SYNTHETIC_RECORD_PATH = (
    REPO_ROOT / "shared" / "synthetic_data" / "output" / "SYNTH-0000-B286B5.json"
)


def main():
    odoo_password = os.environ["ODOO_PASSWORD"]
    orchestrator_api_key = os.environ["ORCHESTRATOR_API_KEY"]

    odoo = odoorpc.ODOO("localhost", protocol="jsonrpc", port=8069)
    odoo.login(os.environ.get("ODOO_DB", "cbam"), os.environ.get("ODOO_USER", "admin"), odoo_password)

    fixtures = seed_dev_fixtures_odoo(odoo.env)

    record = json.loads(SYNTHETIC_RECORD_PATH.read_text(encoding="utf-8"))
    gt = record["ground_truth"]

    declaration_id, declaration_line_id = create_dev_declaration_line_with_document(
        odoo.env,
        declarant_partner_id=fixtures["declarant_partner_id"],
        reporting_year=2026,
        good_id=fixtures["good_ids"]["steel"],
        installation_id=fixtures["installation_ids"][("steel", "BF-BOF", "EG")],
        quantity_tonnes=gt["quantity_tonnes"],
        document_text=record["document_text"],
        filename=f"{record['record_id']}.txt",
    )

    job_request = {
        "declaration_id": declaration_id,
        "declaration_line_id": declaration_line_id,
        "reporting_year": 2026,
    }
    headers = {"X-Api-Key": orchestrator_api_key}
    create_resp = requests.post("http://localhost:8000/jobs", json=job_request, headers=headers, timeout=10)
    create_resp.raise_for_status()
    job_id = create_resp.json()["job_id"]

    POLL_TIMEOUT_SECONDS = 180
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    status_body = None
    timed_out = True
    while time.monotonic() < deadline:
        status_resp = requests.get(f"http://localhost:8000/jobs/{job_id}/status", headers=headers, timeout=10)
        status_resp.raise_for_status()
        status_body = status_resp.json()
        if status_body["status"] not in ("pending", "running"):
            timed_out = False
            break
        time.sleep(3)

    line_model = odoo.env["cbam.declaration.line"]
    final_line = line_model.browse(declaration_line_id)
    doc_model = odoo.env["cbam.source.document"]
    doc_ids = doc_model.search([("declaration_line_id", "=", declaration_line_id)])
    trace = doc_model.browse(doc_ids[0]).raw_llm_output if doc_ids else None

    report = [
        "# M6 Live Verification",
        "",
        f"Record used: `{record['record_id']}` (steel/BF-BOF/EG, ground truth quantity {gt['quantity_tonnes']}t)",
        "",
        "## Job request",
        f"```json\n{json.dumps(job_request, indent=2)}\n```",
        "",
        "## Final job status",
        (
            f"**TIMED OUT** - still `{status_body['status'] if status_body else 'unknown'}` "
            f"after {POLL_TIMEOUT_SECONDS}s, not a real outcome:"
            if timed_out
            else "Resolved for real:"
        ),
        f"```json\n{json.dumps(status_body, indent=2)}\n```",
        "",
        "## Resulting declaration line",
        "```",
        f"quantity_tonnes = {final_line.quantity_tonnes}",
        f"data_source = {final_line.data_source}",
        f"direct_emissions_actual = {final_line.direct_emissions_actual}",
        f"indirect_emissions_actual = {final_line.indirect_emissions_actual}",
        f"embedded_emissions_total = {final_line.embedded_emissions_total}",
        "```",
        "",
        "## Full tool-call trace (cbam.source.document.raw_llm_output)",
        f"```json\n{json.dumps(trace, indent=2)}\n```",
    ]
    out_path = REPO_ROOT / "docs" / "m6-live-verification.md"
    out_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(json.dumps(status_body, indent=2))
    if timed_out:
        print(f"TIMED OUT after {POLL_TIMEOUT_SECONDS}s - job never reached a terminal status", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
