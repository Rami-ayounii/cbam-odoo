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

Covers exactly the (sector, production_route, country) combinations that
appear with data_source == "default" among the first 20 records of
shared/synthetic_data/output/index.json (generated with --seed 42), so a
real M9 run over the first 20 records can resolve every
lookup_default_value call, and Task 6's single live M6 job (steel/BF-BOF/EG)
has a real emission factor to find.
"""

import base64
from dataclasses import dataclass
from datetime import date

from calc_engine import EmissionFactor

VALID_FROM = date(2026, 1, 1)
DEV_SOURCE_LABEL = "DEV FIXTURE - fake round numbers, NOT real CBAM data, local testing only"


@dataclass(frozen=True)
class _Fixture:
    sector: str
    route: str
    country: str
    direct_ef: float
    indirect_ef: float
    markup_pct: float


DEV_EMISSION_FACTOR_FIXTURES = [
    _Fixture("steel", "BF-BOF", "CN", 2.0, 0.0, 0.10),
    _Fixture("steel", "BF-BOF", "EG", 2.1, 0.0, 0.10),
    _Fixture("steel", "BF-BOF", "TR", 1.9, 0.0, 0.10),
    _Fixture("steel", "EAF_scrap", "UA", 0.3, 0.0, 0.10),
    _Fixture("aluminium", "primary_electrolysis", "IS", 12.0, 0.0, 0.10),
    _Fixture("aluminium", "primary_electrolysis", "MA", 11.5, 0.0, 0.10),
]

DEV_GOOD_FIXTURES = [
    {"cn_code": "7208.00.00", "sector": "steel", "description": "DEV FIXTURE steel good", "benchmark": 1.0},
    {"cn_code": "7601.00.00", "sector": "aluminium", "description": "DEV FIXTURE aluminium good", "benchmark": 1.0},
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
                    "benchmark": g["benchmark"],
                }
            )
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
                    "valid_from": VALID_FROM,
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
