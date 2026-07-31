"""Deterministic CBAM compliance calculations for steel and aluminium.

Zero LLM involvement by design: the agent orchestrator (M6) only decides
*when* to call these functions, never computes a compliance number itself.
Emission factors are never hardcoded here - callers must supply them,
sourced from the versioned `cbam.emission_factor` table (M7).
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

# Shared between cbam_source_document.py (rejects oversized uploads at
# write-time) and odoo_client.py (caps at read-time, independent of the
# addon's own validation - the orchestrator is the boundary that actually
# feeds this text into the LLM's prompt). 2 MB is generous for plain-text
# CBAM supplier documents (mill certificates, SAD forms) but well below
# anything that would blow an LLM's context window or the orchestrator's
# memory budget.
MAX_SOURCE_DOCUMENT_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class EmissionFactor:
    sector: str
    route: str
    country: str
    direct_ef: float  # t CO2e / t product
    indirect_ef: float  # t CO2e / t product (0 for steel & aluminium, Annex II)
    markup_pct: float
    source_document: str
    valid_from: date
    valid_to: Optional[date]  # None means still in effect
    # The cbam.emission.factor record id (Odoo primary key), when this
    # EmissionFactor was built from a real record via
    # emission_factor_from_record(). None for hand-built test fixtures.
    # Required so tools.py's lookup_default_value handler can hand the model
    # an emission_factor_id it can then pass to write_declaration_line -
    # write_declaration_line.json's own description promises this id "comes
    # from lookup_default_value's result", so it must actually be present
    # in that result.
    id: Optional[int] = None


def emission_factor_from_record(record) -> EmissionFactor:
    """Builds an EmissionFactor from any duck-typed cbam.emission.factor
    record - an odoorpc record (orchestrator, over RPC) or a real Odoo
    recordset (addon, in-process ORM) both expose the same field names, so
    this one mapping is shared instead of being duplicated per adapter.
    """
    return EmissionFactor(
        sector=record.sector,
        route=record.production_route_id.code,
        country=record.country,
        direct_ef=record.direct_ef,
        indirect_ef=record.indirect_ef,
        markup_pct=record.markup_pct,
        source_document=record.source_document,
        valid_from=record.valid_from,
        valid_to=record.valid_to or None,
        id=record.id,
    )


def is_exempt(total_annual_tonnes: float) -> bool:
    """True if the importer is below the 50 t/year CBAM exemption threshold."""
    return total_annual_tonnes < 50.0


def calculate_embedded_emissions(
    quantity_tonnes: float,
    direct_ef: float,
    indirect_ef: float,
    precursor_emissions: float,
    markup_pct: float = 0.0,
) -> float:
    """Total embedded emissions (t CO2e) for a declaration line.

    SEE = direct_ef * (1 + markup_pct). Per formula sheet section 1.2, iron &
    steel and aluminium are both listed in Annex II of Reg. (EU) 2023/956, so
    only DIRECT emissions are priced: "SEEg = SEE(direct,g) [indirect/
    electricity term = 0 for steel & aluminium]". This module covers steel
    and aluminium exclusively (projecthandoff.md section 3), so indirect_ef
    is deliberately excluded from the SEE sum - not merely expected to be
    0, actively ignored - so that a non-zero indirect_ef (e.g. a measured
    indirect_emissions_actual value entered for reporting/statistics only,
    per the formula sheet's note that electricity consumption is "tracked
    for reporting/statistics but is currently not charged") can never leak
    into the compliance number. The parameter stays in the signature purely
    so indirect data can still be threaded through/recorded by callers
    without an API break.
    markup_pct is the IR 2025/2621 yearly markup on CBAM default values (10%
    in 2026, rising through 2028) - callers must pass 0.0 (the default) for
    data_source = "actual", since the markup only applies when the EF itself
    is a looked-up default, not a measured value.
    precursor_emissions is already an absolute t CO2e figure carried over
    from upstream materials (formula sheet section 1.6), not a per-tonne EF,
    so it is added after the markup rather than being marked up itself.
    """
    see = direct_ef * (1 + markup_pct)
    return quantity_tonnes * see + precursor_emissions


def calculate_certificates_required(
    embedded_emissions_total: float,
    quantity_tonnes: float,
    benchmark: float,
    cbam_factor_year: float,
    carbon_price_paid_origin: float,
    reference_certificate_price: float,
) -> float:
    """CBAM certificates required, per Reg. (EU) 2023/956 Art. 9/31.

    N = [SEE_total - (benchmark * CBAMFactor_year * Q)]
    N_final = N * (1 - carbon_price_adjustment_fraction)

    carbon_price_adjustment_fraction is the verified carbon price already
    paid in the country of production, expressed as a fraction of the
    reference CBAM certificate price, clamped to [0.0, 1.0]: capped at 1.0
    (fully offset) so an overpayment can't push the result negative, and
    floored at 0.0 so a negative/erroneous carbon_price_paid_origin can't
    flip the adjustment into a surcharge that *increases* the certificate
    requirement above the raw benchmark-deducted total.
    Never negative: a free-allocation or price deduction cannot create a
    negative certificate requirement.
    """
    benchmark_deduction = benchmark * cbam_factor_year * quantity_tonnes
    n = max(embedded_emissions_total - benchmark_deduction, 0.0)

    if reference_certificate_price > 0:
        price_adjustment_fraction = min(
            max(carbon_price_paid_origin / reference_certificate_price, 0.0), 1.0
        )
    else:
        price_adjustment_fraction = 0.0

    n_final = n * (1 - price_adjustment_fraction)
    return max(n_final, 0.0)


def lookup_emission_factor(
    sector: str,
    route: str,
    country: str,
    declaration_date: date,
    db_session,
) -> EmissionFactor:
    """Pick the emission factor record valid on declaration_date.

    db_session must expose get_emission_factors(sector, route, country)
    returning candidate EmissionFactor records (an Odoo env or SQLAlchemy
    session adapter implements this; tests use a plain stub).
    """
    candidates = db_session.get_emission_factors(sector, route, country)
    matches = [
        record
        for record in candidates
        if record.valid_from <= declaration_date
        and (record.valid_to is None or declaration_date < record.valid_to)
    ]

    if len(matches) == 0:
        raise ValueError(
            f"No emission factor found for {sector}/{route}/{country} "
            f"valid on {declaration_date}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Overlapping emission factor records for {sector}/{route}/{country} "
            f"valid on {declaration_date}: versioned data must not overlap"
        )
    return matches[0]
