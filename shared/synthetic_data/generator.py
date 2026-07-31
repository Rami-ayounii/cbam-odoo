"""
Synthetic CBAM document generator.

Produces three document types per import record:
  - mill_certificate      : supplier quality/emissions document (EN 10204 Type 3.1 style)
  - carbon_intensity_report: installation-level CBAM emissions declaration
  - customs_declaration   : import entry summary (CN code, quantity, origin)

Each record is saved as JSON with a `document_text` field (what the LLM sees)
and a `ground_truth` field (for M9 evaluation).

Difficulty levels inject realistic extraction challenges:
  easy   – all fields explicitly present
  medium – unit conversions, field in non-obvious location, minor ambiguity
  hard   – one or more fields missing (triggers request_missing_data in agent loop)

Usage:
    python generator.py --count 50 --seed 42 --outdir output/
"""

import argparse
import json
import random
import textwrap
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from faker import Faker

fake = Faker()

# ---------------------------------------------------------------------------
# Reference data (domain-grounded, NOT the authoritative JRC values — those
# go in the versioned cbam.emission_factor table loaded in M7)
# ---------------------------------------------------------------------------

STEEL_CN_CODES = {
    "7206.10.00": "Iron and non-alloy steel in ingots",
    "7207.11.11": "Semi-finished products of iron, square cross-section",
    "7208.10.00": "Flat-rolled products of iron, hot-rolled coils",
    "7208.25.00": "Flat-rolled products of iron, hot-rolled, width ≥600mm",
    "7213.10.00": "Bars and rods, hot-rolled, in irregularly wound coils",
    "7214.20.00": "Other bars and rods of iron, forged",
    "7216.10.00": "Angles, shapes and sections of iron — L-sections",
    "7217.10.10": "Wire of iron or non-alloy steel, not plated",
    "7304.11.00": "Line pipe of a kind used for oil or gas pipelines (seamless)",
    "7306.30.41": "Welded tubes and pipes of circular cross-section, iron",
    "7308.90.99": "Structures and parts thereof (bridges, towers, masts)",
}

ALUMINIUM_CN_CODES = {
    "7601.10.00": "Unwrought aluminium, not alloyed",
    "7601.20.99": "Unwrought aluminium alloys",
    "7604.10.10": "Bars, rods and profiles of aluminium, not alloyed",
    "7604.29.10": "Hollow profiles of aluminium alloys",
    "7605.11.00": "Wire of aluminium, not alloyed, diameter > 7mm",
    "7606.11.10": "Plates, sheets of aluminium, not alloyed, thickness > 0.2mm",
    "7608.10.00": "Tubes and pipes of aluminium, not alloyed",
    "7610.10.00": "Doors, windows and their frames of aluminium",
}

PRODUCTION_ROUTES = {
    "steel": ["BF-BOF", "EAF_scrap", "EAF_DRI"],
    "aluminium": ["primary_electrolysis", "secondary_recycled"],
}

# Approximate emission ranges per route (tCO2e / tonne of product).
# Used ONLY for synthetic document generation — NOT for compliance calc.
# Real values come from JRC134682 and are loaded in M7.
EMISSION_RANGES = {
    "BF-BOF":               {"direct": (1.6, 2.2),  "indirect": (0.05, 0.15)},
    "EAF_scrap":            {"direct": (0.3, 0.6),  "indirect": (0.2,  0.5)},
    "EAF_DRI":              {"direct": (0.6, 1.0),  "indirect": (0.2,  0.4)},
    "primary_electrolysis": {"direct": (0.3, 0.7),  "indirect": (5.0,  12.0)},
    "secondary_recycled":   {"direct": (0.1, 0.25), "indirect": (0.2,  0.5)},
}

# Exporting countries and their carbon prices (EUR/tCO2e, approximate 2026)
EXPORTING_COUNTRIES = {
    "TR": {"name": "Turkey",  "carbon_price": 0.0},
    "IN": {"name": "India",   "carbon_price": 0.0},
    "CN": {"name": "China",   "carbon_price": 12.0},
    "UA": {"name": "Ukraine", "carbon_price": 0.0},
    "MA": {"name": "Morocco", "carbon_price": 0.0},
    "TN": {"name": "Tunisia", "carbon_price": 0.0},
    "BR": {"name": "Brazil",  "carbon_price": 0.0},
    "EG": {"name": "Egypt",   "carbon_price": 0.0},
    "NO": {"name": "Norway",  "carbon_price": 58.0},
    "IS": {"name": "Iceland", "carbon_price": 58.0},
    "CA": {"name": "Canada",  "carbon_price": 65.0},
    "AE": {"name": "UAE",     "carbon_price": 0.0},
}

STEEL_INSTALLATIONS = [
    ("Eregli Iron and Steel Works",    "TR"),
    ("Kardemir Integrated Iron",       "TR"),
    ("Tata Steel Jamshedpur",          "IN"),
    ("JSW Steel Vijayanagar",          "IN"),
    ("Shougang Jingtang Steel",        "CN"),
    ("Baowu Baosteel Shanghai",        "CN"),
    ("ArcelorMittal Kryvyi Rih",       "UA"),
    ("Metinvest Azovstal",             "UA"),
    ("Companhia Siderurgica Nacional", "BR"),
    ("Gerdau Ouro Branco",             "BR"),
    ("Ezz Steel Suez",                 "EG"),
    ("SIMETAL Morocco Casablanca",     "MA"),
]

ALUMINIUM_INSTALLATIONS = [
    ("Hydro Husnes Aluminium",         "NO"),
    ("Hydro Sunndalsora",              "NO"),
    ("ISAL Aluminium Iceland",         "IS"),
    ("Emirates Global Aluminium",      "AE"),
    ("Hindalco Renukoot",              "IN"),
    ("Vedanta Jharsuguda",             "IN"),
    ("Aluminium of Morocco",           "MA"),
    ("ALCOM Tunisia Tunis",            "TN"),
    ("Rio Tinto Alma",                 "CA"),
    ("Chalco Guizhou",                 "CN"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GroundTruth:
    cn_code: str
    description: str
    sector: str
    quantity_tonnes: float
    installation_name: str
    installation_country: str
    production_route: str
    data_source: str                         # "actual" | "default"
    direct_emissions_actual: Optional[float]
    indirect_emissions_actual: Optional[float]
    carbon_price_paid_origin: float
    precursor_emissions: float
    is_complex_good: bool
    missing_fields: list = field(default_factory=list)  # fields the LLM won't find


@dataclass
class SyntheticRecord:
    record_id: str
    document_type: str
    difficulty: str
    document_text: str
    ground_truth: GroundTruth


# ---------------------------------------------------------------------------
# Emission value helpers
# ---------------------------------------------------------------------------

def _rand_emission(route: str, component: str, rng: np.random.Generator) -> float:
    lo, hi = EMISSION_RANGES[route][component]
    return round(float(rng.uniform(lo, hi)), 3)


# ---------------------------------------------------------------------------
# Document text builders
# ---------------------------------------------------------------------------

def _mill_certificate(
    gt: GroundTruth,
    difficulty: str,
    cert_no: str,
    heat_no: str,
    rng: np.random.Generator,
) -> str:
    """Produce a realistic EN 10204 Type 3.1-style mill certificate as plain text."""
    country_name = EXPORTING_COUNTRIES[gt.installation_country]["name"]
    qty_display = gt.quantity_tonnes
    if difficulty == "medium":
        # quantity shown in kg instead of tonnes
        qty_display = round(gt.quantity_tonnes * 1000, 1)
        qty_unit = "kg"
    else:
        qty_unit = "t"

    # Each line is gated independently on its own missing_fields entry - a
    # record with only direct_emissions_actual flagged missing must still
    # show indirect_emissions_actual / carbon_price_paid_origin when those
    # are NOT in missing_fields. (Previously this whole block was gated on
    # direct_emissions_actual alone, silently hiding indirect emissions and
    # carbon price too whenever direct was the missing one - inconsistent
    # with ground_truth.missing_fields, which named only the fields actually
    # meant to be unextractable.)
    emission_section = ""
    if gt.data_source == "actual":
        header_needed = (
            "direct_emissions_actual" not in gt.missing_fields
            or "indirect_emissions_actual" not in gt.missing_fields
            or gt.carbon_price_paid_origin > 0
        )
        if header_needed:
            emission_section = (
                "\nCARBON INTENSITY DECLARATION (CBAM Annex III)\n"
                f"Production route          : {gt.production_route}\n"
            )
            if "direct_emissions_actual" not in gt.missing_fields:
                emission_section += (
                    f"Direct embedded emissions : {gt.direct_emissions_actual} tCO2e/t\n"
                )
            if "indirect_emissions_actual" not in gt.missing_fields:
                emission_section += f"Indirect embedded emissions: {gt.indirect_emissions_actual} tCO2e/t\n"
            if gt.carbon_price_paid_origin > 0:
                emission_section += (
                    f"Carbon price paid (origin) : {gt.carbon_price_paid_origin} EUR/tCO2e\n"
                )

    return textwrap.dedent(f"""
    ══════════════════════════════════════════════════════════════════
    MILL TEST CERTIFICATE — EN 10204 TYPE 3.1
    Certificate No : {cert_no}
    Date           : {fake.date_between(start_date="-6m", end_date="today")}
    ══════════════════════════════════════════════════════════════════

    MANUFACTURER
    Name     : {gt.installation_name}
    Country  : {country_name} ({gt.installation_country})
    Address  : {fake.address().replace(chr(10), ', ')}

    PRODUCT IDENTIFICATION
    CN Code      : {gt.cn_code}
    Description  : {gt.description}
    Heat / Batch : {heat_no}
    Grade        : {"S355JR" if gt.sector == "steel" else "EN AW-6060"}
    Standard     : {"EN 10025-2:2019" if gt.sector == "steel" else "EN 573-3:2019"}

    QUANTITY
    Net mass : {qty_display} {qty_unit}

    CHEMICAL COMPOSITION (% by mass, ladle analysis)
    {"C: 0.18  Mn: 1.42  Si: 0.38  P: 0.018  S: 0.012  N: 0.006" if gt.sector == "steel" else "Si: 0.45  Mg: 0.52  Fe: 0.21  Cu: 0.08  Mn: 0.06  Cr: 0.04"}

    MECHANICAL PROPERTIES
    {"Yield strength (ReH): 382 MPa   Tensile strength (Rm): 541 MPa   Elongation (A5): 26%" if gt.sector == "steel" else "0.2% proof stress: 195 MPa   Tensile strength: 225 MPa   Elongation: 11%"}
    {emission_section}
    ══════════════════════════════════════════════════════════════════
    Authorised Signatory: {fake.name()}
    This certificate is issued in accordance with EN 10204:2004.
    ══════════════════════════════════════════════════════════════════
    """).strip()


def _carbon_intensity_report(
    gt: GroundTruth,
    difficulty: str,
    report_no: str,
    rng: np.random.Generator,
) -> str:
    """Produce a CBAM carbon intensity report (standalone supplier declaration)."""
    country_name = EXPORTING_COUNTRIES[gt.installation_country]["name"]

    # ground_truth.quantity_tonnes is never null (unlike the emissions
    # fields, it has no missing_fields mechanism), so it must always be
    # extractable from whichever document type gets generated - this report
    # previously never mentioned quantity at all, making it silently
    # unextractable for ~30% of records without that being flagged anywhere.
    if difficulty == "medium":
        quantity_line = f"Quantity covered   : {round(gt.quantity_tonnes * 1000, 1)} kg"
    else:
        quantity_line = f"Quantity covered   : {gt.quantity_tonnes} t"

    direct_line = ""
    indirect_line = ""
    if "direct_emissions_actual" not in gt.missing_fields and gt.direct_emissions_actual is not None:
        direct_line = f"Direct embedded emissions  : {gt.direct_emissions_actual} tCO2e / tonne of product"
    if "indirect_emissions_actual" not in gt.missing_fields and gt.indirect_emissions_actual is not None:
        indirect_line = f"Indirect embedded emissions: {gt.indirect_emissions_actual} tCO2e / tonne of product"

    monitoring_approach = (
        "Calculation approach based on activity data and emission factors (Annex III, Reg 2023/956)"
        if difficulty != "hard"
        else "Third-party verified monitoring plan — see annex"  # vague, to test LLM
    )

    price_line = ""
    if gt.carbon_price_paid_origin > 0:
        price_line = f"Carbon price paid at origin: {gt.carbon_price_paid_origin} EUR/tCO2e (ETS compliance)"

    return textwrap.dedent(f"""
    ══════════════════════════════════════════════════════════════════
    CBAM CARBON INTENSITY REPORT
    Report No      : {report_no}
    Reporting year : 2026
    ══════════════════════════════════════════════════════════════════

    INSTALLATION
    Name     : {gt.installation_name}
    Country  : {country_name} ({gt.installation_country})
    Sector   : {gt.sector.capitalize()}
    Production route: {gt.production_route}
    {quantity_line}

    EMISSIONS DATA
    {direct_line}
    {indirect_line}
    {price_line}
    Monitoring approach: {monitoring_approach}
    Verification status: Third-party verified

    DECLARATION
    I, the undersigned, declare that the information provided above is
    accurate and complete to the best of my knowledge.

    Signed: {fake.name()}
    Date  : {fake.date_between(start_date="-3m", end_date="today")}
    ══════════════════════════════════════════════════════════════════
    """).strip()


def _customs_declaration(
    gt: GroundTruth,
    difficulty: str,
    declaration_no: str,
    rng: np.random.Generator,
) -> str:
    """Produce a customs import entry summary."""
    country_name = EXPORTING_COUNTRIES[gt.installation_country]["name"]
    value_eur = round(gt.quantity_tonnes * float(rng.uniform(400, 1800)), 2)

    cn_line = (
        f"CN Code     : {gt.cn_code}"
        if difficulty != "medium"
        else f"Tariff heading : {gt.cn_code.replace('.', '')}  (combined nomenclature)"
    )

    return textwrap.dedent(f"""
    ══════════════════════════════════════════════════════════════════
    SINGLE ADMINISTRATIVE DOCUMENT — IMPORT ENTRY SUMMARY
    Declaration No : {declaration_no}
    Date of acceptance: {fake.date_between(start_date="-6m", end_date="today")}
    ══════════════════════════════════════════════════════════════════

    IMPORTER
    Name    : {fake.company()} SRL
    Address : {fake.address().replace(chr(10), ', ')}
    EORI    : {fake.bothify(text="EU##############")}

    GOODS
    {cn_line}
    Description : {gt.description}
    Net mass    : {gt.quantity_tonnes} tonnes
    Customs value: EUR {value_eur:,.2f}

    ORIGIN
    Country of origin : {country_name} ({gt.installation_country})
    Exporter / Manufacturer: {gt.installation_name}

    PROCEDURE: 40 00 — Release for free circulation
    ══════════════════════════════════════════════════════════════════
    """).strip()


# ---------------------------------------------------------------------------
# Record factory
# ---------------------------------------------------------------------------

def _pick_difficulty(rng: np.random.Generator) -> str:
    return rng.choice(["easy", "medium", "hard"], p=[0.5, 0.3, 0.2])


def generate_record(
    index: int,
    rng: np.random.Generator,
    force_difficulty: Optional[str] = None,
) -> SyntheticRecord:
    difficulty = force_difficulty or _pick_difficulty(rng)

    # Pick sector and CN code
    sector = rng.choice(["steel", "aluminium"], p=[0.65, 0.35])
    cn_codes = STEEL_CN_CODES if sector == "steel" else ALUMINIUM_CN_CODES
    cn_code = rng.choice(list(cn_codes.keys()))
    description = cn_codes[cn_code]

    # Pick installation
    pool = STEEL_INSTALLATIONS if sector == "steel" else ALUMINIUM_INSTALLATIONS
    inst_name, country_code = pool[int(rng.integers(0, len(pool)))]
    country_info = EXPORTING_COUNTRIES[country_code]

    # Production route
    route = rng.choice(PRODUCTION_ROUTES[sector])

    # Quantity — sprinkle some records near the 50t exemption boundary
    if index % 8 == 0:
        quantity = round(float(rng.uniform(40, 60)), 2)   # boundary case
    else:
        quantity = round(float(rng.uniform(5, 500)), 2)

    # Decide data_source: "actual" most of the time, "default" occasionally
    data_source = "actual" if rng.random() < 0.75 else "default"

    # Emission values (only for actual; default means lookup from reference table)
    direct_ef = _rand_emission(route, "direct", rng) if data_source == "actual" else None
    indirect_ef = _rand_emission(route, "indirect", rng) if data_source == "actual" else None

    # Carbon price
    carbon_price = country_info["carbon_price"]
    if carbon_price > 0:
        # Add small random variation
        carbon_price = round(carbon_price * float(rng.uniform(0.9, 1.1)), 2)

    # Precursor emissions (only relevant for complex goods; keep 0 for now)
    precursor_emissions = 0.0
    is_complex_good = False

    # Missing fields for hard difficulty
    missing_fields: list[str] = []
    if difficulty == "hard" and data_source == "actual":
        candidates = ["direct_emissions_actual", "indirect_emissions_actual"]
        n_missing = int(rng.integers(1, len(candidates) + 1))
        missing_fields = list(rng.choice(candidates, size=n_missing, replace=False))

    gt = GroundTruth(
        cn_code=cn_code,
        description=description,
        sector=sector,
        quantity_tonnes=quantity,
        installation_name=inst_name,
        installation_country=country_code,
        production_route=route,
        data_source=data_source,
        direct_emissions_actual=direct_ef,
        indirect_emissions_actual=indirect_ef,
        carbon_price_paid_origin=carbon_price,
        precursor_emissions=precursor_emissions,
        is_complex_good=is_complex_good,
        missing_fields=missing_fields,
    )

    # Pick document type
    doc_type = rng.choice(
        ["mill_certificate", "carbon_intensity_report", "customs_declaration"],
        p=[0.5, 0.3, 0.2],
    )

    # customs_declaration (SAD-style import entry summary) never carries
    # CBAM emissions data in real life or in _customs_declaration()'s text
    # below - so when this doc type is picked and data_source == "actual",
    # direct/indirect_emissions_actual are structurally unextractable from
    # the one document this record hands the agent, independent of
    # `difficulty`. Without this, ground truth claimed those fields were
    # extractable (non-null, not in missing_fields) when they never appear
    # in the text - an internal-consistency bug that would silently fail
    # any model's extraction regardless of quality.
    if doc_type == "customs_declaration" and gt.data_source == "actual":
        for absent_field in ("direct_emissions_actual", "indirect_emissions_actual"):
            if absent_field not in gt.missing_fields:
                gt.missing_fields.append(absent_field)

    # Derived from the seeded rng (not uuid.uuid4(), which ignores --seed
    # entirely) so that re-running the same --count/--seed reproduces the
    # exact same record_ids and overwrites the previous output in place,
    # instead of silently accumulating a second copy of every record under
    # new random filenames on every run.
    record_id = f"SYNTH-{index:04d}-{rng.integers(0, 0xFFFFFF):06X}"
    cert_no = fake.bothify(text="CERT-####-???").upper()
    heat_no = fake.bothify(text="H-######").upper()
    report_no = fake.bothify(text="CIR-####-??").upper()
    decl_no = fake.bothify(text="IM-####-######")

    if doc_type == "mill_certificate":
        text = _mill_certificate(gt, difficulty, cert_no, heat_no, rng)
    elif doc_type == "carbon_intensity_report":
        text = _carbon_intensity_report(gt, difficulty, report_no, rng)
    else:
        text = _customs_declaration(gt, difficulty, decl_no, rng)

    return SyntheticRecord(
        record_id=record_id,
        document_type=doc_type,
        difficulty=difficulty,
        document_text=text,
        ground_truth=gt,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_dataset(
    count: int,
    seed: int,
    outdir: Path,
) -> None:
    rng = np.random.default_rng(seed)
    random.seed(seed)
    Faker.seed(seed)

    outdir.mkdir(parents=True, exist_ok=True)

    records = []
    for i in range(count):
        rec = generate_record(index=i, rng=rng)
        records.append(rec)

        # Save individual file
        payload = {
            "record_id": rec.record_id,
            "document_type": rec.document_type,
            "difficulty": rec.difficulty,
            "document_text": rec.document_text,
            "ground_truth": asdict(rec.ground_truth),
        }
        out_path = outdir / f"{rec.record_id}.json"
        # Explicit utf-8: document_text contains box-drawing characters
        # (═, written via ensure_ascii=False so they're readable in the
        # file, not \u escaped). Without an explicit encoding, write_text()
        # falls back to the platform's locale encoding - cp1252 on Windows -
        # which cannot represent those characters and crashes every run.
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # Summary index
    summary = [
        {
            "record_id": r.record_id,
            "document_type": r.document_type,
            "difficulty": r.difficulty,
            "sector": r.ground_truth.sector,
            "country": r.ground_truth.installation_country,
            "quantity_tonnes": r.ground_truth.quantity_tonnes,
            "production_route": r.ground_truth.production_route,
            "data_source": r.ground_truth.data_source,
            "missing_fields": r.ground_truth.missing_fields,
        }
        for r in records
    ]
    (outdir / "index.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Stats
    difficulties = [r.difficulty for r in records]
    sectors = [r.ground_truth.sector for r in records]
    doc_types = [r.document_type for r in records]
    print(f"Generated {count} records -> {outdir}")
    print(f"  Difficulties : easy={difficulties.count('easy')}  medium={difficulties.count('medium')}  hard={difficulties.count('hard')}")
    print(f"  Sectors      : steel={sectors.count('steel')}  aluminium={sectors.count('aluminium')}")
    print(f"  Doc types    : mill_cert={doc_types.count('mill_certificate')}  cir={doc_types.count('carbon_intensity_report')}  customs={doc_types.count('customs_declaration')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CBAM synthetic document generator")
    parser.add_argument("--count",  type=int, default=50,       help="Number of records to generate")
    parser.add_argument("--seed",   type=int, default=42,        help="Random seed for reproducibility")
    parser.add_argument("--outdir", type=str, default="output",  help="Output directory")
    args = parser.parse_args()

    generate_dataset(
        count=args.count,
        seed=args.seed,
        outdir=Path(args.outdir),
    )
