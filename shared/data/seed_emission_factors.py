"""M7: seed cbam.emission.factor / cbam.year.parameter / cbam.good.benchmark
with authoritative reference data.

STATUS (2026-09-08 re-attempt): a prior session could not reach the primary
sources at all (empty EUR-Lex fetches, a garbled JRC134682 text layer, no
local `poppler`). This session had `pdftotext` (poppler/xpdf) available and
fetched the actual regulation/report PDFs directly (bypassing WebFetch's
10 MB cap with `curl` + local `pdftotext -raw` extraction). That produced
clean, directly-quotable primary text - and, reading it carefully, revealed
that most of the *specific* country/route pairings this file originally
guessed at (BF-BOF/FR, EAF_scrap/FR, EAF_DRI/TR, primary_electrolysis/NO,
secondary_recycled/TN) do not actually exist in the primary sources as
distinct figures:
  - France never appears as a country in either source's steel tables:
    CBAM default values only cover non-EU countries of origin (France is
    an EU member, so no French import ever needs a CBAM default value).
  - Commission Implementing Regulation (EU) 2025/2621's Annex I/IV define
    a "(D) Carbon Steel based on DRI/EAF" route indicator in their legend,
    but across the entire ~170-country, ~2,400-page Annex I that indicator
    is never actually attached to a single data row (confirmed by an
    exhaustive count) - Turkiye's own CN 7208 entry, and every other
    country's, is tagged "(C) BF/BOF". There is no DRI/EAF-route CBAM
    default value in this regulation for any country.
  - Norway is not listed in IR 2025/2621's Annex I at all, and JRC134682
    states outright that "Norway and Iceland form part of the EU ETS and
    are therefore not affected by the CBAM" (section 4.1) - Norway is
    legally out of CBAM's scope, not merely missing data.
  - Tunisia is absent from both sources' steel/aluminium per-country
    tables (it falls under IR 2025/2621's Annex I "Other Countries and
    Territories" catch-all, which for CN 7601 is tagged "(K) primary
    Aluminium", not "(L) secondary" - so it cannot honestly stand in for
    a "secondary_recycled" figure either).
See docs/m7-source-verification.md for the full fetch-by-fetch record,
exact quotes and citations.

What *did* come back clean and get filled in below: the EU ETS benchmark
values for hot metal (steel) and aluminium from Commission Implementing
Regulation (EU) 2026/1412's Annex, and the flat 10% 2026 markup rate from
IR 2025/2621 (which is sector-wide, not country/route-specific, so it is
now filled in on every EmissionFactorSeed even though direct_ef on most of
them is still None). The two YearParameterSeed fields remain None: real,
quotable numbers exist for both (Directive 2003/87/EC Art. 10a(1a)'s CBAM
factor, and two of 2026's four quarterly CBAM certificate prices), but
using them raises questions outside this task's data-only scope (see
docs/m7-source-verification.md) rather than a fetch failure, so they are
left as documented placeholders pending a human decision.

Each still-`None` value below carries a comment explaining exactly why.
seed_odoo() refuses to write to a real Odoo instance while any placeholder
remains, specifically so nobody accidentally seeds the one table this
project is not allowed to guess at (projecthandoff.md section 2: "Never
hardcode these values in code" / "do not invent numbers"). Fill in a value
only after opening the actual source document it cites - never from memory
or a secondary-source guess.

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
        direct_ef=None,  # BLOCKED: France is not a listed country in either
        # source's steel tables (confirmed by exhaustive search of both the
        # extracted JRC134682 text and IR 2025/2621's Annex I - "France"
        # never appears except in an unrelated citation). CBAM default
        # values only exist for non-EU countries of origin; France, as an
        # EU member, never needs one. See docs/m7-source-verification.md
        # for detail.
        indirect_ef=0.0,  # Annex II: indirect not priced for steel, but tracked
        markup_pct=0.10,  # VERIFIED: Commission Implementing Regulation (EU)
        # 2025/2621, Annex I, "Iron and steel 10% mark-up 20% mark-up 30%
        # mark-up" header (2026/2027/2028-onwards columns) - confirmed
        # identical across every country block and in Annex IV; sector-wide,
        # not country- or route-specific.
        source_document="BLOCKED: no France entry in JRC134682 or IR 2025/2621 Annex I (EU member, out of CBAM scope) - markup_pct verified from IR 2025/2621 Annex I; direct_ef still None, see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="steel",
        route="EAF_scrap",
        country="FR",
        direct_ef=None,  # BLOCKED: same reason as BF-BOF/FR above - France
        # is not a listed country in either primary source.
        indirect_ef=0.0,
        markup_pct=0.10,  # VERIFIED: same IR 2025/2621 Annex I "Iron and
        # steel 10% mark-up" line as above.
        source_document="BLOCKED: no France entry in JRC134682 or IR 2025/2621 Annex I (EU member, out of CBAM scope) - markup_pct verified from IR 2025/2621 Annex I; direct_ef still None, see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="steel",
        route="EAF_DRI",
        country="TR",
        direct_ef=None,  # BLOCKED: IR 2025/2621's Annex I legend defines a
        # "(D) Carbon Steel based on DRI/EAF" route indicator, but an
        # exhaustive count across the entire ~2,400-page Annex I found it
        # attached to zero actual data rows for any country - Turkiye's own
        # CN 7208 entry (2,428 direct) and every other steel CN code for
        # Turkiye is tagged "(C) BF/BOF" instead. JRC134682 only gives
        # Turkiye one blended per-CN-code value (its Step 3 methodology
        # explicitly says route-decomposed values exist only for the
        # "weighted average" of out-of-scope countries, not named
        # countries like Turkiye). No clean DRI/EAF-route figure exists
        # for Turkiye in either source.
        indirect_ef=0.0,
        markup_pct=0.10,  # VERIFIED: IR 2025/2621 Annex I, "Iron and steel
        # 10% mark-up" line - confirmed for Turkiye's own country block too.
        source_document="BLOCKED: DRI/EAF route indicator (D) is defined in IR 2025/2621's legend but used in zero data rows anywhere in the regulation; JRC134682 gives Turkiye only a blended (not route-specific) value - markup_pct verified from IR 2025/2621 Annex I; direct_ef still None, see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="aluminium",
        route="primary_electrolysis",
        country="NO",
        direct_ef=None,  # BLOCKED: Norway is not listed in IR 2025/2621's
        # Annex I at all, and JRC134682 states outright (section 4.1):
        # "Norway and Iceland form part of the EU ETS and are therefore
        # not affected by the CBAM" - Norway is legally out of CBAM's
        # scope, not merely missing data. (JRC134682's own Annex 2 table
        # does list a blended Norway/CN 7601 figure - Direct 1.84, Indirect
        # 0.13, Total 1.97 tCO2e/t - but using it would misattribute a
        # country-blended number as a pure "primary electrolysis route"
        # figure from a country the report itself says CBAM doesn't cover.)
        indirect_ef=0.0,
        markup_pct=0.10,  # VERIFIED: IR 2025/2621 Annex I, "Aluminium 10%
        # mark-up" line - sector-wide, applies regardless of country/route.
        source_document="BLOCKED: Norway is out of CBAM's scope entirely (EU ETS member per JRC134682 section 4.1), not listed in IR 2025/2621 Annex I - markup_pct verified from IR 2025/2621 Annex I; direct_ef still None, see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="aluminium",
        route="secondary_recycled",
        country="TN",
        direct_ef=None,  # BLOCKED: Tunisia does not appear in either
        # source's aluminium per-country tables (JRC134682's 15-country
        # aluminium scope requires >=1% EU import share; IR 2025/2621's
        # Annex I never names Tunisia for steel/aluminium either - only in
        # its fertiliser/cement sections and in Annex II/III's electricity
        # grid tables, which are for indirect emissions, not needed here).
        # Tunisia's applicable default, per IR 2025/2621's own Annex I rule,
        # would be its "Other Countries and Territories" catch-all - found
        # and checked (CN 7601: direct 2.203 tCO2/t) - but that row is
        # tagged "(K) primary Aluminium", not "(L) secondary", so it cannot
        # honestly stand in for a secondary_recycled figure.
        indirect_ef=0.0,
        markup_pct=0.10,  # VERIFIED: IR 2025/2621 Annex I, "Aluminium 10%
        # mark-up" line - same sector-wide rate, confirmed in the "Other
        # Countries and Territories" table too.
        source_document="BLOCKED: Tunisia absent from both sources' aluminium tables; IR 2025/2621's 'Other Countries and Territories' fallback for CN 7601 is tagged primary (K), not secondary (L) - markup_pct verified from IR 2025/2621 Annex I; direct_ef still None, see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
]

YEAR_PARAMETER_SEEDS: List[YearParameterSeed] = [
    YearParameterSeed(
        year=2026,
        cbam_factor_year=None,  # BLOCKED (not a fetch failure - a found
        # number with an unresolved unit/direction question): Directive
        # 2003/87/EC Art. 10a(1a) (as amended, consolidated text
        # 02003L0087--EN--01.03.2024) reads: "...shall be equal to 97,5 %
        # in 2026, 95 % in 2027, 90 % in 2028, 77,5 % in 2029, 51,5 % in
        # 2030, 39 % in 2031, 26,5 % in 2032 and 14 % in 2033. From 2034,
        # no CBAM factor shall apply." That "CBAM factor" is the fraction
        # of free allocation STILL RETAINED (97.5% in 2026, falling to 0%
        # by 2034). But this codebase's existing cbam_factor_year usage
        # (shared/data/dev_fixtures.py, docs/PROGRESS.md, the M4 plan) is
        # 0.025 for 2026 with the comment "phase-out factor (2.5% 2026 ->
        # 100% 2034)" - the COMPLEMENT of the Directive's figure, rising
        # the opposite direction. calc_engine.calculate_certificates_required
        # computes benchmark_deduction = benchmark * cbam_factor_year *
        # quantity_tonnes; plugging in 0.025 for 2026 makes that deduction
        # tiny, so importers would owe certificates for nearly their full
        # embedded emissions from year one - the opposite of the gradual
        # phase-in the Directive describes. Whether the field should hold
        # 0.975 (the Directive's literal figure) or 0.025 (matching the
        # pre-existing convention/tests) is a formula-direction question
        # outside this task's data-only scope ("do not touch the
        # mechanism") - escalated in docs/m7-source-verification.md rather than guessed.
        reference_certificate_price=None,  # BLOCKED (partial - real numbers
        # exist but don't reduce to one 2026 figure): the European
        # Commission's official page (taxation-customs.ec.europa.eu/
        # carbon-border-adjustment-mechanism/price-cbam-certificates_en)
        # states "In 2026, the Commission will calculate and publish four
        # quarterly prices, one for each calendar quarter" and gives, as of
        # this session's date (2026-09-08): Q1 2026 = EUR 75,36 (published
        # 7 April 2026), Q2 2026 = EUR 75,28 (published 6 July 2026); Q3
        # 2026 (due 5 October 2026) and Q4 2026 (due 4 January 2027) are
        # not yet published. The cbam.year.parameter model holds one
        # reference_certificate_price per year (unique-constrained on
        # year, per docs/PROGRESS.md), which cannot represent a value that
        # is genuinely quarterly (and still incomplete) for 2026 without
        # picking one quarter or an average - a modelling decision, not a
        # data lookup, so left for the human partner (see docs/m7-source-verification.md).
        source_document="BLOCKED: real primary figures found (Dir. 2003/87/EC Art. 10a(1a) CBAM factor; EC quarterly CBAM certificate prices) but each raises a scope question outside this task's data-only mandate - see docs/m7-source-verification.md",
    ),
]

GOOD_BENCHMARK_SEEDS: List[GoodBenchmarkSeed] = [
    GoodBenchmarkSeed(
        cn_code="7208",
        sector="steel",
        benchmark=1.248,  # VERIFIED: Commission Implementing Regulation
        # (EU) 2026/1412 of 26 June 2026, Annex "BENCHMARKS", Section 1
        # ("Product benchmarks without collection of data on electricity
        # consumption"), "Hot metal" row: "Benchmark value (allowances/t)
        # for 2026-2030" = 1,248 t CO2e/t (average of the 10% most
        # efficient installations in 2021/2022 = 1,360). Confirmed the
        # regulation number itself from the fetched EUR-Lex PDF text
        # ("COMMISSION IMPLEMENTING REGULATION (EU) 2026/1412 of 26 June
        # 2026 determining revised benchmark values for free allocation of
        # emission allowances for the period from 2026 to 2030..."), and
        # cross-checked the figure against an independent secondary-source
        # mention ("hot metal falls to 1.248 tCO2e per tonne").
        source_document="Commission Implementing Regulation (EU) 2026/1412, Annex 'BENCHMARKS', Section 1, 'Hot metal' row, benchmark value (allowances/t) for 2026-2030",
    ),
    GoodBenchmarkSeed(
        cn_code="7601",
        sector="aluminium",
        benchmark=1.423,  # VERIFIED: same regulation and Annex section,
        # "Aluminium" row: benchmark value (allowances/t) for 2026-2030 =
        # 1,423 t CO2e/t (average of top 10% = 1,489). This resolves the
        # earlier session's flagged uncertainty ("aluminium may be on
        # generic heat/fuel benchmarks rather than a dedicated product
        # benchmark") - the regulation text confirms a DEDICATED
        # "Aluminium" product benchmark exists for 2026-2030, distinct
        # from the heat/fuel fallback benchmarks in Section 3.
        source_document="Commission Implementing Regulation (EU) 2026/1412, Annex 'BENCHMARKS', Section 1, 'Aluminium' row, benchmark value (allowances/t) for 2026-2030",
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
            "Fill in these first (see inline BLOCKED comments in "
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
