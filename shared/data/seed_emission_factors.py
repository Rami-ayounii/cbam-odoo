"""M7: seed cbam.emission.factor / cbam.year.parameter / cbam.good.benchmark
with authoritative reference data.

STATUS (2026-09-08, Task 9 fixture redesign): an earlier same-day session
(Task 6) established the primary-source fetch path (`curl` + local
`pdftotext -raw`, bypassing WebFetch's 10 MB PDF cap) and found that 4 of
the 5 originally-guessed country/route pairings (BF-BOF/FR, EAF_scrap/FR,
EAF_DRI/TR, primary_electrolysis/NO) do not exist in the primary sources:
France and Norway are EU/EU-ETS members and out of CBAM's import scope
entirely, and the "(D) Carbon Steel based on DRI/EAF" route indicator is
defined in Commission Implementing Regulation (EU) 2025/2621's Annex I/IV
legend but is never actually attached to a single data row anywhere in the
~135,000-line regulation text for any country (re-confirmed this task:
`grep -cF "(D)"` = 2, both legend definitions). Task 6 also concluded the
5th pairing (secondary_recycled/TN) had no data - that specific conclusion
was wrong. This task re-fetched the same 41 MB regulation PDF (confirmed
byte-identical: 41,252,987 bytes, 135,102 extracted lines) and re-read
Tunisia's own country block in full: it *does* carry a CN 7601 row tagged
"(L) secondary Aluminium" (Task 6's search evidently missed it, most likely
an artifact of an anchored `^Tunisia$` grep against lines containing an
extraction-mangled non-ASCII byte - substring search finds it fine).

Replaced the 4 genuinely-unfixable pairings with real, populated, non-EU/
non-EEA country/route combinations IR 2025/2621 actually publishes CN 7208
(steel) / CN 7601 (aluminium) default values for:
  - steel BF-BOF: Turkiye (was France) - CN 7208 row tagged "(C)"
  - steel EAF_scrap: Azerbaijan (was France) - CN 7208 row tagged "(E)"
  - aluminium primary_electrolysis: Bahrain (was Norway) - CN 7601 row
    tagged "(K)"
  - aluminium secondary_recycled: Tunisia (unchanged - it was the right
    country all along; only Task 6's "no data" finding was wrong)
steel EAF_DRI remains genuinely unfillable: no country in this regulation
carries a "(D)"-tagged data row - this is not a per-country gap.
See docs/m7-source-verification.md for the full fetch record, exact
quotes, and citations (Task 6's original entries plus this task's
additions and the Tunisia correction).

The EU ETS benchmark values for hot metal (steel) and aluminium from
Commission Implementing Regulation (EU) 2026/1412's Annex, and the flat
10% 2026 markup rate from IR 2025/2621 (sector-wide, not country/route-
specific), were already verified by Task 6 and are unchanged here.

`YEAR_PARAMETER_SEEDS`'s `reference_certificate_price` for 2026 is now
filled in as the average of the two 2026 quarterly CBAM certificate prices
published so far (Q1 2026 = EUR 75.36, Q2 2026 = EUR 75.28 -> average
EUR 75.32), re-verified directly against the raw HTML of the European
Commission's official price page as of this session's date (2026-09-08);
Q3 2026 (due 5 October 2026) and Q4 2026 (due 4 January 2027) table cells
are still empty (`&nbsp;`) in the source, i.e. genuinely not published yet
- not a fetch failure.

UPDATE (Task 11, same day): `cbam_factor_year` is now filled in as `0.025`
for 2026. Task 6 found a real, quotable Directive 2003/87/EC Art. 10a(1a)
figure (the "CBAM factor" = 97.5% retained free allocation for 2026) that
runs in the opposite direction from this codebase's pre-existing
0.025-for-2026 convention, and left it as a `calc_engine.py`
formula-direction question outside a data-only task's mandate. That
question was already resolved before Task 9 started: commit db50c1f fixed
`calc_engine.py`'s formula to `benchmark * (1 - cbam_factor_year) *
quantity_tonnes`, which makes the pre-existing 0.025 convention (the
complement of the Directive's 97.5%) directionally correct again. Task 11
confirmed this (re-checked the Directive text and the current formula) and
filled in the value - see docs/m7-source-verification.md.

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
        country="TR",
        direct_ef=2.428,  # VERIFIED: Commission Implementing Regulation (EU)
        # 2025/2621, Annex I, Türkiye country block (extracted text line
        # 107584-110671 of the re-fetched 135,102-line PDF text), CN 7208
        # row: "7208 Flat-rolled products of iron or non-alloy steel, of a
        # width >= 600 mm, hot-rolled, not clad, plated or coated 2,428 N/A
        # 2,428 2,670 2,913 3,156 (C)" - direct default value 2.428 t
        # CO2e/t, route tag (C) = "Carbon Steel based on BF/BOF", matching
        # this record's route exactly. Replaces the earlier BF-BOF/FR
        # pairing (France is an EU member, never a CBAM import origin).
        indirect_ef=0.0,  # source row: indirect emissions default = "N/A"
        markup_pct=0.10,  # VERIFIED: Commission Implementing Regulation (EU)
        # 2025/2621, Annex I, "Iron and steel 10% mark-up 20% mark-up 30%
        # mark-up" header (2026/2027/2028-onwards columns) - confirmed
        # identical across every country block and in Annex IV; sector-wide,
        # not country- or route-specific.
        source_document="Commission Implementing Regulation (EU) 2025/2621, Annex I, Türkiye country block, CN 7208 row (direct default value 2.428, route indicator (C) BF/BOF); markup_pct from the same Annex's sector-wide 'Iron and steel 10% mark-up' 2026 header - see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="steel",
        route="EAF_scrap",
        country="AZ",
        direct_ef=0.140,  # VERIFIED: Commission Implementing Regulation (EU)
        # 2025/2621, Annex I, Azerbaijan country block (extracted text line
        # 10075-13719), CN 7208 row: "7208 Flat-rolled products of iron or
        # non-alloy steel, of a width >= 600 mm, hot-rolled, not clad,
        # plated or coated 0,140 N/A 0,140 0,154 0,168 0,182 (E)" - direct
        # default value 0.140 t CO2e/t, route tag (E) = "Carbon Steel based
        # on Scrap/EAF", matching this record's route exactly. Same CN code
        # (7208) as the BF-BOF/TR record above, for a clean apples-to-apples
        # comparison. Replaces the earlier EAF_scrap/FR pairing (same
        # out-of-scope reason as BF-BOF/FR).
        indirect_ef=0.0,  # source row: indirect emissions default = "N/A"
        markup_pct=0.10,  # VERIFIED: same IR 2025/2621 Annex I "Iron and
        # steel 10% mark-up" line as above.
        source_document="Commission Implementing Regulation (EU) 2025/2621, Annex I, Azerbaijan country block, CN 7208 row (direct default value 0.140, route indicator (E) Scrap/EAF); markup_pct from the same Annex's sector-wide 'Iron and steel 10% mark-up' 2026 header - see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="steel",
        route="EAF_DRI",
        country="TR",
        direct_ef=None,  # BLOCKED (re-confirmed, Task 9): IR 2025/2621's
        # Annex I legend defines a "(D) Carbon Steel based on DRI/EAF" route
        # indicator, but re-fetching and re-counting against this task's own
        # freshly-downloaded copy of the PDF (confirmed byte-identical to
        # Task 6's: 41,252,987 bytes, 135,102 extracted lines) found the
        # exact same result: `grep -cF "(D)"` across the whole document = 2,
        # both the legend definitions themselves (Annex I's intro, Annex
        # IV's copy) - never attached to a single actual data row, for
        # Turkiye or any other of the ~170 countries in the Annex. This is
        # not a per-country gap - no country's steel data anywhere in this
        # regulation carries a DRI/EAF route tag, so there is no country to
        # substitute in for this specific route. JRC134682 (checked by Task
        # 6 as a second source) likewise only gives Turkiye a single blended
        # per-CN-code value, not a route-decomposed one.
        indirect_ef=0.0,
        markup_pct=0.10,  # VERIFIED: IR 2025/2621 Annex I, "Iron and steel
        # 10% mark-up" line - confirmed for Turkiye's own country block too.
        source_document="BLOCKED: DRI/EAF route indicator (D) is defined in IR 2025/2621's legend but used in zero data rows anywhere in the regulation, for any country (re-confirmed Task 9 against a freshly re-fetched, byte-identical copy of the PDF); JRC134682 gives Turkiye only a blended (not route-specific) value - markup_pct verified from IR 2025/2621 Annex I; direct_ef still None, see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="aluminium",
        route="primary_electrolysis",
        country="BH",
        direct_ef=1.870,  # VERIFIED: Commission Implementing Regulation (EU)
        # 2025/2621, Annex I, Bahrain country block (extracted text line
        # 13720-13903), CN 7601 row: "7601 Unwrought aluminium 1,870 N/A
        # 1,870 2,057 2,244 2,431 (K)" - direct default value 1.870
        # t CO2e/t, route tag (K) = "primary Aluminium", matching this
        # record's route exactly. Bahrain is one of JRC134682's own named
        # 15-country aluminium scope (section 4.1) and a real-world major
        # primary-aluminium exporter (Aluminium Bahrain/Alba). Replaces the
        # earlier primary_electrolysis/NO pairing (Norway is an EU-ETS
        # member, out of CBAM's scope per JRC134682 section 4.1).
        indirect_ef=0.0,  # source row: indirect emissions default = "N/A"
        markup_pct=0.10,  # VERIFIED: IR 2025/2621 Annex I, "Aluminium 10%
        # mark-up" line - sector-wide, applies regardless of country/route.
        source_document="Commission Implementing Regulation (EU) 2025/2621, Annex I, Bahrain country block, CN 7601 row (direct default value 1.870, route indicator (K) primary Aluminium); markup_pct from the same Annex's sector-wide 'Aluminium 10% mark-up' 2026 header - see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
    EmissionFactorSeed(
        sector="aluminium",
        route="secondary_recycled",
        country="TN",
        direct_ef=0.360,  # VERIFIED (Task 9 correction of a Task 6 miss):
        # Commission Implementing Regulation (EU) 2025/2621, Annex I,
        # Tunisia's own country block (extracted text line 107001-107583)
        # *does* carry a CN 7601 row: "7601 Unwrought aluminium 0,360 N/A
        # 0,360 0,396 0,432 0,468 (L)" - direct default value 0.360
        # t CO2e/t, route tag (L) = "secondary Aluminium", matching this
        # record's route exactly. Task 6 had concluded Tunisia had no
        # aluminium entry at all (only fertiliser/cement); re-fetching and
        # re-reading Tunisia's block in full for this task found that
        # conclusion was wrong - the row was there, just missed. Tunisia
        # has no steel (CN 72xx) rows in this regulation at all, so the
        # steel side of Tunisia's absence (Task 6's other finding) still
        # stands; only the aluminium/secondary_recycled pairing changes.
        indirect_ef=0.0,  # source row: indirect emissions default = "N/A"
        markup_pct=0.10,  # VERIFIED: IR 2025/2621 Annex I, "Aluminium 10%
        # mark-up" line - same sector-wide rate, confirmed in Tunisia's own
        # country block too.
        source_document="Commission Implementing Regulation (EU) 2025/2621, Annex I, Tunisia country block, CN 7601 row (direct default value 0.360, route indicator (L) secondary Aluminium); markup_pct from the same Annex's sector-wide 'Aluminium 10% mark-up' 2026 header - see docs/m7-source-verification.md",
        valid_from=date(2026, 1, 1),
    ),
]

YEAR_PARAMETER_SEEDS: List[YearParameterSeed] = [
    YearParameterSeed(
        year=2026,
        cbam_factor_year=0.025,  # VERIFIED (Task 11, resolves the gap
        # Tasks 6/9 escalated): Directive 2003/87/EC Art. 10a(1a) (as
        # amended, consolidated text 02003L0087--EN--01.03.2024) reads:
        # "...shall be equal to 97,5 % in 2026, 95 % in 2027, 90 % in
        # 2028, 77,5 % in 2029, 51,5 % in 2030, 39 % in 2031, 26,5 % in
        # 2032 and 14 % in 2033. From 2034, no CBAM factor shall apply."
        # That "CBAM factor" is the fraction of free allocation STILL
        # RETAINED (97.5% in 2026, falling to 0% by 2034) - the codebase's
        # own field holds the COMPLEMENT of that figure (0.025 for 2026),
        # which is directionally correct now: commit db50c1f ("Fix
        # inverted cbam_factor_year direction in certificate calculation",
        # already on this branch before Task 9) changed
        # calc_engine.calculate_certificates_required's formula to
        # benchmark_deduction = benchmark * (1 - cbam_factor_year) *
        # quantity_tonnes, so a low early-year value now produces a large
        # deduction, matching the Directive's described gradual phase-in
        # (free allocation - and thus the deduction it funds - shrinks
        # toward zero by 2034 as cbam_factor_year rises toward 1.0). See
        # docs/m7-source-verification.md's Field 8 / Task 9 addendum
        # sections for the full derivation.
        reference_certificate_price=75.32,  # VERIFIED (Task 9, resolves the
        # gap Task 6 escalated): average of the 2026 quarterly CBAM
        # certificate prices published so far on the European Commission's
        # official page (taxation-customs.ec.europa.eu/carbon-border-
        # adjustment-mechanism/price-cbam-certificates_en), re-fetched and
        # re-checked directly against the page's raw HTML table cells for
        # this task (2026-09-08): Q1 2026 = EUR 75.36 (published 7 April
        # 2026, table cell "75,36"), Q2 2026 = EUR 75.28 (published 6 July
        # 2026, table cell "75,28"). Q3 2026 (due 5 October 2026) and Q4
        # 2026 (due 4 January 2027) table cells are still empty ("&nbsp;")
        # in the source - genuinely not published yet, not a fetch failure -
        # so this average uses only the 2 quarters currently published:
        # (75.36 + 75.28) / 2 = 75.32. This is an APPROXIMATION, not a
        # single official annual figure (there isn't one for 2026 - the
        # mechanism is explicitly quarterly this year) - re-average once Q3
        # and/or Q4 publish.
        source_document="reference_certificate_price: average of 2026 Q1 (EUR 75.36, published 7 April 2026) and Q2 (EUR 75.28, published 6 July 2026) CBAM certificate prices, the only 2026 quarters published as of 2026-09-08, per the European Commission's official price page (taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en); Q3/Q4 2026 not yet published - this is an average of published quarterly figures, not a single official annual price. cbam_factor_year: Directive 2003/87/EC Art. 10a(1a) (consolidated text 02003L0087--EN--01.03.2024) sets the 'CBAM factor' (fraction of free allocation retained) at 97.5% for 2026; this field stores the complement (0.025), matching calc_engine.py's benchmark * (1 - cbam_factor_year) formula (see docs/m7-source-verification.md)",
    ),
]

GOOD_BENCHMARK_SEEDS: List[GoodBenchmarkSeed] = [
    # KNOWN LIMITATION (documented, not a bug in the arithmetic): GoodBenchmarkSeed
    # keys only on (cn_code, sector), with no route dimension, so the single benchmark
    # below is applied uniformly to every EmissionFactorSeed record for this CN code
    # regardless of production route. For CN 7208 (steel) this benchmark represents
    # hot-metal BF-BOF production per its source citation below; applying it to a
    # scrap-EAF route record (e.g. the steel EAF_scrap/AZ record) understates the true
    # benchmark deduction for that route and will compute an artificially low (possibly
    # zero) certificate requirement. See docs/PROGRESS.md's M7 section and
    # docs/m7-source-verification.md for the concrete numeric consequence and why a real
    # fix needs a route dimension added to GoodBenchmarkSeed (a schema change, out of
    # scope for this plan).
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
    # KNOWN LIMITATION (documented, not a bug in the arithmetic): same no-route-dimension
    # gap as CN 7208 above. This CN 7601 benchmark specifically represents
    # PRIMARY/electrolytic aluminium production per its source citation below (the
    # Annex's "Aluminium" benchmark row). Applying it to the secondary_recycled route
    # (e.g. the aluminium secondary_recycled/TN record) is wrong: secondary/recycled
    # aluminium's real-world emissions intensity is far lower than primary, so this
    # benchmark overstates the free-allocation deduction and computes an artificially
    # low - here, exactly zero - certificate requirement for that record. A real fix
    # needs a route dimension added to GoodBenchmarkSeed (a schema change, out of scope
    # for this plan); see docs/PROGRESS.md's M7 section and
    # docs/m7-source-verification.md for the concrete numeric consequence.
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
