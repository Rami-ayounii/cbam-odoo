"""M7: seed cbam.emission.factor / cbam.year.parameter / cbam.good.benchmark
with authoritative reference data.

STATUS: every numeric value below is an unverified PLACEHOLDER (`None`),
not real data. The dev environment that built this script could not
reliably reach the primary sources: EUR-Lex page fetches came back empty,
and the JRC134682 PDF has no usable text layer here (no local `poppler`
to render it, and text extraction returned garbled output). Web search
summaries of secondary sources also disagreed with each other on the same
figures (EU ETS benchmarks, CBAM default values, and mill-level estimates
are different quantities and got conflated) - not something to build
compliance data on.

Each seed below carries a comment naming the exact primary source and
table/section to check. seed_odoo() refuses to write to a real Odoo
instance while any placeholder remains, specifically so nobody accidentally
seeds the one table this project is not allowed to guess at
(projecthandoff.md section 2: "Never hardcode these values in code" /
"do not invent numbers"). Fill in a value only after opening the actual
source document it cites - never from memory or a secondary-source guess.

Intended to run standalone against a real Odoo instance over odoorpc (the
same access pattern machineB/orchestrator uses), not from inside Odoo's own
process - see main() below.
"""

import argparse
import os
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from urllib.parse import urlparse


@dataclass
class EmissionFactorSeed:
    sector: str
    route: str
    country: str
    direct_ef: Optional[float]
    indirect_ef: Optional[float]
    markup_pct: Optional[float]
    source_document: str
    valid_from: date
    valid_to: Optional[date] = None


@dataclass
class YearParameterSeed:
    year: int
    cbam_factor_year: Optional[float]
    reference_certificate_price: Optional[float]
    source_document: str


@dataclass
class GoodBenchmarkSeed:
    cn_code: str
    sector: str
    benchmark: Optional[float]
    source_document: str


EMISSION_FACTOR_SEEDS: List[EmissionFactorSeed] = [
    EmissionFactorSeed(
        sector="steel",
        route="BF-BOF",
        country="FR",
        direct_ef=None,  # TODO: JRC134682 (DOI 10.2760/359533), steel results table, BF-BOF row for France
        indirect_ef=0.0,  # Annex II: indirect not priced for steel, but tracked
        markup_pct=None,  # TODO: IR 2025/2621 markup schedule (10% in 2026, rising through 2028) - confirm 2026 figure in the regulation text itself
        source_document="JRC134682 (steel, BF-BOF, FR) - PLACEHOLDER, not yet verified",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="steel",
        route="EAF_scrap",
        country="FR",
        direct_ef=None,  # TODO: JRC134682, EAF scrap route, France
        indirect_ef=0.0,
        markup_pct=None,  # TODO: see above
        source_document="JRC134682 (steel, EAF_scrap, FR) - PLACEHOLDER, not yet verified",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="steel",
        route="EAF_DRI",
        country="TR",
        direct_ef=None,  # TODO: JRC134682, EAF DRI route, Turkey (major EU steel exporter)
        indirect_ef=0.0,
        markup_pct=None,
        source_document="JRC134682 (steel, EAF_DRI, TR) - PLACEHOLDER, not yet verified",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="aluminium",
        route="primary_electrolysis",
        country="NO",
        direct_ef=None,  # TODO: JRC134682, primary electrolysis, Norway - include PFC CO2e per formulas sheet section 3.2
        indirect_ef=0.0,
        markup_pct=None,
        source_document="JRC134682 (aluminium, primary_electrolysis, NO) - PLACEHOLDER, not yet verified",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="aluminium",
        route="secondary_recycled",
        country="TN",
        direct_ef=None,  # TODO: JRC134682, secondary/recycled aluminium, Tunisia (project's stated regional relevance, projecthandoff.md section 3)
        indirect_ef=0.0,
        markup_pct=None,
        source_document="JRC134682 (aluminium, secondary_recycled, TN) - PLACEHOLDER, not yet verified",
        valid_from=date(2026, 1, 1),
    ),
]

YEAR_PARAMETER_SEEDS: List[YearParameterSeed] = [
    YearParameterSeed(
        year=2026,
        cbam_factor_year=None,  # TODO: Reg. (EU) 2023/956 Art. 31 phase-out schedule - CBAM_Formulas_Steel_Aluminium.md section 4 cites 2.5% for 2026 but explicitly flags that figure as not verified word-for-word against the primary text; confirm in the regulation before using
        reference_certificate_price=None,  # TODO: published average CBAM certificate price for 2026, taxation-customs.ec.europa.eu/cbam
        source_document="Reg. (EU) 2023/956 Art. 31 / taxation-customs.ec.europa.eu - PLACEHOLDER, not yet verified",
    ),
]

GOOD_BENCHMARK_SEEDS: List[GoodBenchmarkSeed] = [
    GoodBenchmarkSeed(
        cn_code="7208",
        sector="steel",
        benchmark=None,  # TODO: Commission Implementing Regulation (EU) 2026/1412 Annex, hot-rolled coil / hot metal benchmark
        source_document="Commission Implementing Regulation (EU) 2026/1412 - PLACEHOLDER, not yet verified",
    ),
    GoodBenchmarkSeed(
        cn_code="7601",
        sector="aluminium",
        benchmark=None,  # TODO: same regulation - aluminium may be on generic heat/fuel benchmarks rather than a dedicated product benchmark for 2026-2030; confirm the actual mechanism before filling this in
        source_document="Commission Implementing Regulation (EU) 2026/1412 - PLACEHOLDER, not yet verified",
    ),
]


def find_incomplete_seeds() -> List[str]:
    """Every seed record that still has a placeholder (None) value.
    These must never be written to a real Odoo instance."""
    incomplete = []
    for seed in EMISSION_FACTOR_SEEDS:
        label = f"emission_factor {seed.sector}/{seed.route}/{seed.country}"
        if seed.direct_ef is None:
            incomplete.append(f"{label}: direct_ef")
        if seed.markup_pct is None:
            incomplete.append(f"{label}: markup_pct")
    for seed in YEAR_PARAMETER_SEEDS:
        label = f"year_parameter {seed.year}"
        if seed.cbam_factor_year is None:
            incomplete.append(f"{label}: cbam_factor_year")
        if seed.reference_certificate_price is None:
            incomplete.append(f"{label}: reference_certificate_price")
    for seed in GOOD_BENCHMARK_SEEDS:
        if seed.benchmark is None:
            incomplete.append(f"good_benchmark {seed.cn_code}: benchmark")
    return incomplete


def _as_id(created):
    # odoorpc's create() returns a plain int id; kept as a single choke
    # point in case this script is ever adapted to run inside Odoo's own
    # ORM env instead, where create() returns a recordset.
    return created if isinstance(created, int) else created.id


def seed_odoo(env, allow_incomplete: bool = False) -> None:
    """env: anything supporting env["model.name"] -> object with
    search(domain)/create(vals)/write(ids, vals) - an odoorpc connection's
    .env satisfies this."""
    incomplete = find_incomplete_seeds()
    if incomplete and not allow_incomplete:
        raise ValueError(
            "Refusing to seed placeholder/unverified values into Odoo. "
            "Fill in these first (see inline TODO comments in "
            "seed_emission_factors.py for exactly which source to check):\n- "
            + "\n- ".join(incomplete)
        )

    route_ids = {}
    for seed in EMISSION_FACTOR_SEEDS:
        key = (seed.sector, seed.route)
        route_id = route_ids.get(key)
        if route_id is None:
            existing = env["cbam.production.route"].search(
                [("sector", "=", seed.sector), ("code", "=", seed.route)]
            )
            if existing:
                route_id = existing[0]
            else:
                route_id = _as_id(
                    env["cbam.production.route"].create(
                        {"sector": seed.sector, "code": seed.route}
                    )
                )
            route_ids[key] = route_id

        env["cbam.emission.factor"].create(
            {
                "sector": seed.sector,
                "production_route_id": route_id,
                "country": seed.country,
                "direct_ef": seed.direct_ef,
                "indirect_ef": seed.indirect_ef,
                "markup_pct": seed.markup_pct,
                "source_document": seed.source_document,
                "valid_from": seed.valid_from,
                "valid_to": seed.valid_to,
            }
        )

    for seed in YEAR_PARAMETER_SEEDS:
        env["cbam.year.parameter"].create(
            {
                "year": seed.year,
                "cbam_factor_year": seed.cbam_factor_year,
                "reference_certificate_price": seed.reference_certificate_price,
                "source_document": seed.source_document,
            }
        )

    for seed in GOOD_BENCHMARK_SEEDS:
        # cbam.good's own sql_constraint is unique(cn_code, sector), not
        # cn_code alone - the same CN code can legitimately exist under two
        # different sectors, so this must scope by both, or a steel seed's
        # benchmark could bleed into an aluminium good that happens to share
        # a cn_code (or vice versa).
        good_ids = env["cbam.good"].search(
            [("cn_code", "=", seed.cn_code), ("sector", "=", seed.sector)]
        )
        for good_id in good_ids:
            env["cbam.good"].write([good_id], {"benchmark": seed.benchmark})


def main():
    import odoorpc

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Write placeholder/unverified values anyway. Do not use against a real declaration.",
    )
    args = parser.parse_args()

    parsed = urlparse(os.environ["ODOO_URL"])
    protocol = "jsonrpc+ssl" if parsed.scheme == "https" else "jsonrpc"
    odoo = odoorpc.ODOO(
        parsed.hostname, protocol=protocol, port=parsed.port or 8069
    )
    odoo.login(os.environ["ODOO_DB"], os.environ["ODOO_USER"], os.environ["ODOO_PASSWORD"])

    seed_odoo(odoo.env, allow_incomplete=args.allow_incomplete)


if __name__ == "__main__":
    main()
