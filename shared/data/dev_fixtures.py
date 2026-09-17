"""Local-dev-only fake reference data - explicitly NOT real CBAM numbers.

Distinct from seed_emission_factors.py, which holds this project's real
(currently placeholder-until-verified) M7 data and refuses to write while
any placeholder remains. This file exists purely to exercise the M3/M6/M9
live-infra pipeline end to end against the disposable
docker-compose.local-dev.yml stack (seed_dev_fixtures_odoo) or an in-memory
session for M9's real-model run (build_emission_factor_session) - every
numeric value here is an arbitrary, clearly-labeled round number, never
written by seed_emission_factors.py and never presented as an authoritative
CBAM figure.

Covers every (sector, production_route, country) combination that appears
with data_source == "default" across the full 50-record dataset in
shared/synthetic_data/output/index.json (generated with --seed 42), so a
real M9 run over any subset of it can resolve every lookup_default_value
call, and Task 6's single live M6 job (steel/BF-BOF/EG) has a real
emission factor to find. Originally scoped to only the first 20 records -
widened after a live run over records 20-49 showed 7 of them correctly-
but-unhelpfully escalating on a genuine "no emission factor found" error,
purely because this table had never been extended (docs/PROGRESS.md's
"Default model switched to qwen2.5:14b-instruct" section).
"""

import base64
from dataclasses import dataclass
from datetime import date

from calc_engine import EmissionFactor

VALID_FROM = date(2026, 1, 1)
DEV_SOURCE_LABEL = "DEV FIXTURE - fake round numbers, NOT real CBAM data, local testing only"


@dataclass(frozen=True)
class _Fixture:
    id: int
    sector: str
    route: str
    country: str
    direct_ef: float
    indirect_ef: float
    markup_pct: float


DEV_EMISSION_FACTOR_FIXTURES = [
    _Fixture(1, "steel", "BF-BOF", "CN", 2.0, 0.0, 0.10),
    _Fixture(2, "steel", "BF-BOF", "EG", 2.1, 0.0, 0.10),
    _Fixture(3, "steel", "BF-BOF", "TR", 1.9, 0.0, 0.10),
    _Fixture(4, "steel", "EAF_scrap", "UA", 0.3, 0.0, 0.10),
    _Fixture(5, "aluminium", "primary_electrolysis", "IS", 12.0, 0.0, 0.10),
    _Fixture(6, "aluminium", "primary_electrolysis", "MA", 11.5, 0.0, 0.10),
    # Added to widen coverage from "the first 20 records" to "the full
    # 50-record dataset" (docs/PROGRESS.md's "Default model switched to
    # qwen2.5:14b-instruct" section) - a live run over records 20-49
    # showed 7 data_source="default" records correctly-but-unhelpfully
    # escalating on a genuine "no emission factor found" error, purely
    # because this table had never been extended past the original 20.
    # Round numbers in the same plausible range as generator.py's own
    # EMISSION_RANGES per route, same as every fixture above - still not
    # real CBAM data.
    _Fixture(7, "steel", "BF-BOF", "MA", 2.05, 0.0, 0.10),
    _Fixture(8, "steel", "EAF_scrap", "BR", 0.35, 0.0, 0.10),
    _Fixture(9, "steel", "EAF_scrap", "MA", 0.4, 0.0, 0.10),
    _Fixture(10, "steel", "EAF_scrap", "TR", 0.32, 0.0, 0.10),
    _Fixture(11, "aluminium", "secondary_recycled", "CA", 0.15, 0.0, 0.10),
    _Fixture(12, "aluminium", "secondary_recycled", "MA", 0.18, 0.0, 0.10),
    _Fixture(13, "aluminium", "secondary_recycled", "NO", 0.20, 0.0, 0.10),
]

DEV_GOOD_FIXTURES = [
    {"cn_code": "7208.00.00", "sector": "steel", "description": "DEV FIXTURE steel good"},
    {"cn_code": "7601.00.00", "sector": "aluminium", "description": "DEV FIXTURE aluminium good"},
]

# cbam.good.benchmark is route-specific (see cbam_declaration_line.py's
# good_benchmark_id) - one row per (sector, route) actually exercised by
# DEV_INSTALLATION_FIXTURES below, arbitrary round numbers same as the rest
# of this file.
DEV_GOOD_BENCHMARK_FIXTURES = [
    {"sector": "steel", "route": "BF-BOF", "benchmark": 1.0},
    {"sector": "steel", "route": "EAF_scrap", "benchmark": 0.3},
    {"sector": "aluminium", "route": "primary_electrolysis", "benchmark": 1.0},
]

DEV_INSTALLATION_FIXTURES = [
    {"name": "DEV FIXTURE Steel Mill CN", "country": "CN", "sector": "steel", "route": "BF-BOF"},
    {"name": "DEV FIXTURE Steel Mill EG", "country": "EG", "sector": "steel", "route": "BF-BOF"},
    {"name": "DEV FIXTURE Steel Mill TR", "country": "TR", "sector": "steel", "route": "BF-BOF"},
    {"name": "DEV FIXTURE Steel Mill UA", "country": "UA", "sector": "steel", "route": "EAF_scrap"},
    {"name": "DEV FIXTURE Aluminium Smelter IS", "country": "IS", "sector": "aluminium", "route": "primary_electrolysis"},
    {"name": "DEV FIXTURE Aluminium Smelter MA", "country": "MA", "sector": "aluminium", "route": "primary_electrolysis"},
]

DEV_YEAR_PARAMETER_FIXTURE = {
    "year": 2026,
    "cbam_factor_year": 0.025,
    "reference_certificate_price": 80.0,
    "source_document": DEV_SOURCE_LABEL,
}

DEV_DECLARANT_NAME = "DEV FIXTURE Declarant"


def build_emission_factor_session():
    """In-memory get_emission_factors(sector, route, country) duck-type (see
    calc_engine.lookup_emission_factor) for M9's real-model run, which never
    talks to a real Odoo instance (run_evaluation.py's FixtureOdooClient)."""
    records = [
        EmissionFactor(
            sector=f.sector,
            route=f.route,
            country=f.country,
            direct_ef=f.direct_ef,
            indirect_ef=f.indirect_ef,
            markup_pct=f.markup_pct,
            source_document=DEV_SOURCE_LABEL,
            valid_from=VALID_FROM,
            valid_to=None,
            # Without a real id, lookup_default_value's result always had
            # emission_factor_id=None, making a data_source="default"
            # write_declaration_line call structurally impossible in this
            # harness regardless of model quality - tool_args.py's
            # WriteDeclarationLineArgs requires a non-None emission_factor_id
            # whenever data_source is "default" (docs/PROGRESS.md's
            # MVP-focused follow-up section). Real Odoo assigns this on
            # create(); this fixture just needs a stable stand-in.
            id=f.id,
        )
        for f in DEV_EMISSION_FACTOR_FIXTURES
    ]

    class _Session:
        def get_emission_factors(self, sector, route, country):
            return [
                r for r in records
                if r.sector == sector and r.route == route and r.country == country
            ]

    return _Session()


def seed_dev_fixtures_odoo(env) -> dict:
    """Writes DEV_* fixtures into a real (disposable, local-dev) Odoo
    instance via odoorpc. Idempotent - safe to call more than once against
    the same database. Never call this against anything but
    docker-compose.local-dev.yml's throwaway Odoo."""
    route_ids = {}

    def _route_id(sector, route):
        key = (sector, route)
        if key not in route_ids:
            existing = env["cbam.production.route"].search(
                [("sector", "=", sector), ("code", "=", route)]
            )
            route_ids[key] = (
                existing[0] if existing
                else env["cbam.production.route"].create({"sector": sector, "code": route})
            )
        return route_ids[key]

    good_ids = {}
    for g in DEV_GOOD_FIXTURES:
        existing = env["cbam.good"].search(
            [("cn_code", "=", g["cn_code"]), ("sector", "=", g["sector"])]
        )
        good_ids[g["sector"]] = (
            existing[0] if existing
            else env["cbam.good"].create(
                {
                    "cn_code": g["cn_code"],
                    "sector": g["sector"],
                    "description": g["description"],
                }
            )
        )

    for b in DEV_GOOD_BENCHMARK_FIXTURES:
        route_id = _route_id(b["sector"], b["route"])
        good_id = good_ids[b["sector"]]
        existing = env["cbam.good.benchmark"].search(
            [
                ("good_id", "=", good_id),
                ("production_route_id", "=", route_id),
            ]
        )
        if not existing:
            env["cbam.good.benchmark"].create(
                {
                    "good_id": good_id,
                    "production_route_id": route_id,
                    "benchmark": b["benchmark"],
                    "source_document": DEV_SOURCE_LABEL,
                }
            )

    installation_ids = {}
    for i in DEV_INSTALLATION_FIXTURES:
        route_id = _route_id(i["sector"], i["route"])
        existing = env["cbam.installation"].search([("name", "=", i["name"])])
        installation_ids[(i["sector"], i["route"], i["country"])] = (
            existing[0] if existing
            else env["cbam.installation"].create(
                {
                    "name": i["name"],
                    "country": i["country"],
                    "sector": i["sector"],
                    "production_route_id": route_id,
                }
            )
        )

    for f in DEV_EMISSION_FACTOR_FIXTURES:
        route_id = _route_id(f.sector, f.route)
        existing = env["cbam.emission.factor"].search(
            [
                ("sector", "=", f.sector),
                ("production_route_id", "=", route_id),
                ("country", "=", f.country),
            ]
        )
        if not existing:
            env["cbam.emission.factor"].create(
                {
                    "sector": f.sector,
                    "production_route_id": route_id,
                    "country": f.country,
                    "direct_ef": f.direct_ef,
                    "indirect_ef": f.indirect_ef,
                    "markup_pct": f.markup_pct,
                    "source_document": DEV_SOURCE_LABEL,
                    # odoorpc's JSON-RPC transport can't serialize a raw
                    # datetime.date - Odoo's ORM accepts ISO date strings on
                    # the wire regardless, so isoformat() here (not
                    # VALID_FROM itself, which build_emission_factor_session
                    # still needs as a real date for calc_engine.EmissionFactor).
                    "valid_from": VALID_FROM.isoformat(),
                }
            )

    if not env["cbam.year.parameter"].search([("year", "=", DEV_YEAR_PARAMETER_FIXTURE["year"])]):
        env["cbam.year.parameter"].create(DEV_YEAR_PARAMETER_FIXTURE)

    existing_partner = env["res.partner"].search([("name", "=", DEV_DECLARANT_NAME)])
    declarant_partner_id = (
        existing_partner[0] if existing_partner
        else env["res.partner"].create({"name": DEV_DECLARANT_NAME})
    )

    return {
        "good_ids": good_ids,
        "installation_ids": installation_ids,
        "declarant_partner_id": declarant_partner_id,
    }


def create_dev_declaration_line_with_document(
    env,
    declarant_partner_id,
    reporting_year,
    good_id,
    installation_id,
    quantity_tonnes,
    document_text,
    filename="synthetic-doc.txt",
):
    """Creates one declaration + line + source document, ready for a live
    M6 job. data_source is set to "actual" (not the field's own "default")
    on purpose: cbam_declaration_line.py's _check_emission_factor_set_for_
    default_source constraint rejects data_source="default" without an
    emission_factor_id, which nothing has looked up yet at creation time -
    the agent loop's own write_declaration_line call is what later sets
    data_source and emission_factor_id together in one atomic write."""
    declaration_id = env["cbam.declaration"].create(
        {"declarant_id": declarant_partner_id, "reporting_year": reporting_year}
    )
    declaration_line_id = env["cbam.declaration.line"].create(
        {
            "declaration_id": declaration_id,
            "good_id": good_id,
            "installation_id": installation_id,
            "quantity_tonnes": quantity_tonnes,
            "data_source": "actual",
        }
    )
    env["cbam.source.document"].create(
        {
            "declaration_line_id": declaration_line_id,
            "attachment": base64.b64encode(document_text.encode("utf-8")).decode("ascii"),
            "attachment_filename": filename,
        }
    )
    return declaration_id, declaration_line_id
