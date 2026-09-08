from datetime import date

import pytest

from calc_engine import (
    EmissionFactor,
    calculate_certificates_required,
    calculate_embedded_emissions,
    is_exempt,
    lookup_emission_factor,
)


class FakeDbSession:
    """Minimal stand-in for an Odoo env / SQLAlchemy session, used only in tests."""

    def __init__(self, records):
        self._records = records

    def get_emission_factors(self, sector, route, country):
        return [
            r
            for r in self._records
            if r.sector == sector and r.route == route and r.country == country
        ]


# --- is_exempt: 50 t/year boundary ---


def test_is_exempt_below_threshold():
    assert is_exempt(49.9) is True


def test_is_exempt_at_threshold_is_not_exempt():
    assert is_exempt(50.0) is False


def test_is_exempt_above_threshold():
    assert is_exempt(50.1) is False


# --- calculate_embedded_emissions ---


def test_embedded_emissions_steel_bf_bof_direct_only():
    # Illustrative direct EF for BF-BOF route (t CO2e/t steel); indirect is 0
    # per Annex II for steel. Not an authoritative JRC134682 value - arithmetic
    # check only.
    result = calculate_embedded_emissions(
        quantity_tonnes=100.0,
        direct_ef=1.9,
        indirect_ef=0.0,
        precursor_emissions=0.0,
    )
    assert result == pytest.approx(190.0)


def test_embedded_emissions_adds_precursor_emissions():
    # Downstream good: its own process EF plus emissions already embedded in
    # the precursor material it consumed (section 1.6 of the formulas sheet).
    result = calculate_embedded_emissions(
        quantity_tonnes=10.0,
        direct_ef=0.05,
        indirect_ef=0.0,
        precursor_emissions=15.0,
    )
    assert result == pytest.approx(15.5)


def test_embedded_emissions_zero_quantity_returns_precursor_only():
    result = calculate_embedded_emissions(
        quantity_tonnes=0.0,
        direct_ef=1.9,
        indirect_ef=0.0,
        precursor_emissions=3.0,
    )
    assert result == pytest.approx(3.0)


def test_embedded_emissions_applies_markup_pct_to_ef_only_not_precursor():
    # 100 * (1.9 * 1.10) = 209, plus precursor carried over unmarked-up
    result = calculate_embedded_emissions(
        quantity_tonnes=100.0,
        direct_ef=1.9,
        indirect_ef=0.0,
        precursor_emissions=5.0,
        markup_pct=0.10,
    )
    assert result == pytest.approx(214.0)


def test_embedded_emissions_default_markup_pct_is_zero():
    result = calculate_embedded_emissions(
        quantity_tonnes=100.0,
        direct_ef=1.9,
        indirect_ef=0.0,
        precursor_emissions=0.0,
    )
    assert result == pytest.approx(190.0)


def test_embedded_emissions_ignores_indirect_ef_for_steel_and_aluminium():
    # Formula sheet section 1.2: iron & steel and aluminium are Annex II
    # goods, so SEEg = SEE(direct,g) only - indirect/electricity emissions
    # are tracked for reporting/statistics but never priced. A non-zero
    # indirect_ef (e.g. a measured indirect_emissions_actual value entered
    # for statistics) must not change the compliance number: result should
    # be identical to the indirect_ef=0.0 case above.
    result = calculate_embedded_emissions(
        quantity_tonnes=100.0,
        direct_ef=1.9,
        indirect_ef=0.6,
        precursor_emissions=0.0,
    )
    assert result == pytest.approx(190.0)


# --- calculate_certificates_required (full Art. 9/31 formula) ---


def test_certificates_no_benchmark_no_price_adjustment():
    result = calculate_certificates_required(
        embedded_emissions_total=200.0,
        quantity_tonnes=100.0,
        benchmark=0.0,
        cbam_factor_year=0.0,
        carbon_price_paid_origin=0.0,
        reference_certificate_price=80.0,
    )
    assert result == pytest.approx(200.0)


def test_certificates_benchmark_deduction_applied():
    # Under the corrected formula, benchmark_deduction = benchmark * (1 -
    # cbam_factor_year) * quantity. cbam_factor_year=0.3 -> 70% of the
    # benchmark-based free-allocation-equivalent still applies:
    # deduction = 1.0 * 0.7 * 100 = 70
    result = calculate_certificates_required(
        embedded_emissions_total=200.0,
        quantity_tonnes=100.0,
        benchmark=1.0,
        cbam_factor_year=0.3,
        carbon_price_paid_origin=0.0,
        reference_certificate_price=80.0,
    )
    assert result == pytest.approx(130.0)


def test_certificates_carbon_price_paid_reduces_result_proportionally():
    # price_adjustment_fraction = 40 / 80 = 0.5 -> half of N deducted
    result = calculate_certificates_required(
        embedded_emissions_total=200.0,
        quantity_tonnes=100.0,
        benchmark=0.0,
        cbam_factor_year=0.0,
        carbon_price_paid_origin=40.0,
        reference_certificate_price=80.0,
    )
    assert result == pytest.approx(100.0)


def test_certificates_price_adjustment_capped_at_full_deduction():
    # carbon price paid exceeds reference price -> fraction capped at 1.0
    result = calculate_certificates_required(
        embedded_emissions_total=200.0,
        quantity_tonnes=100.0,
        benchmark=0.0,
        cbam_factor_year=0.0,
        carbon_price_paid_origin=500.0,
        reference_certificate_price=80.0,
    )
    assert result == pytest.approx(0.0)


def test_certificates_never_negative_when_benchmark_deduction_exceeds_total():
    # cbam_factor_year=0.0 in the corrected formula means the FULL
    # benchmark-based free-allocation-equivalent still applies (deduction =
    # benchmark * 1.0 * quantity), which can exceed total embedded
    # emissions - result must floor at 0, never go negative.
    result = calculate_certificates_required(
        embedded_emissions_total=50.0,
        quantity_tonnes=100.0,
        benchmark=1.0,
        cbam_factor_year=0.0,
        carbon_price_paid_origin=0.0,
        reference_certificate_price=80.0,
    )
    assert result == pytest.approx(0.0)


def test_certificates_low_year_factor_means_gentle_phase_in_burden():
    # This is the fix's whole point: a LOW cbam_factor_year (early
    # transition years, e.g. 2.5% for 2026) must produce a LOWER
    # certificate burden than a HIGH cbam_factor_year (e.g. 100% by 2034)
    # for the same emissions/benchmark/quantity - the phase-in must get
    # more expensive over time, never less.
    early_transition = calculate_certificates_required(
        embedded_emissions_total=200.0,
        quantity_tonnes=100.0,
        benchmark=1.0,
        cbam_factor_year=0.025,
        carbon_price_paid_origin=0.0,
        reference_certificate_price=80.0,
    )
    full_phase_out = calculate_certificates_required(
        embedded_emissions_total=200.0,
        quantity_tonnes=100.0,
        benchmark=1.0,
        cbam_factor_year=1.0,
        carbon_price_paid_origin=0.0,
        reference_certificate_price=80.0,
    )
    assert early_transition == pytest.approx(102.5)
    assert full_phase_out == pytest.approx(200.0)
    assert early_transition < full_phase_out


def test_certificates_negative_carbon_price_paid_does_not_inflate_result():
    # A negative/erroneous carbon_price_paid_origin must not flip the price
    # adjustment into a surcharge - the fraction is floored at 0.0, so the
    # result is capped at N (the raw benchmark-deducted total), never above.
    result = calculate_certificates_required(
        embedded_emissions_total=200.0,
        quantity_tonnes=100.0,
        benchmark=0.0,
        cbam_factor_year=0.0,
        carbon_price_paid_origin=-40.0,
        reference_certificate_price=80.0,
    )
    assert result == pytest.approx(200.0)


# --- lookup_emission_factor: versioned date-ranged lookup ---


def _make_factor(valid_from, valid_to, direct_ef):
    return EmissionFactor(
        sector="steel",
        route="BF-BOF",
        country="FR",
        direct_ef=direct_ef,
        indirect_ef=0.0,
        markup_pct=0.10,
        source_document="test-fixture",
        valid_from=valid_from,
        valid_to=valid_to,
    )


def test_lookup_picks_record_valid_on_declaration_date():
    old = _make_factor(date(2024, 1, 1), date(2026, 1, 1), direct_ef=2.0)
    new = _make_factor(date(2026, 1, 1), None, direct_ef=1.9)
    db_session = FakeDbSession([old, new])

    result = lookup_emission_factor(
        sector="steel",
        route="BF-BOF",
        country="FR",
        declaration_date=date(2026, 6, 1),
        db_session=db_session,
    )

    assert result is new


def test_lookup_picks_earlier_record_when_date_before_transition():
    old = _make_factor(date(2024, 1, 1), date(2026, 1, 1), direct_ef=2.0)
    new = _make_factor(date(2026, 1, 1), None, direct_ef=1.9)
    db_session = FakeDbSession([old, new])

    result = lookup_emission_factor(
        sector="steel",
        route="BF-BOF",
        country="FR",
        declaration_date=date(2025, 6, 1),
        db_session=db_session,
    )

    assert result is old


def test_lookup_no_matching_record_raises_value_error():
    old = _make_factor(date(2024, 1, 1), date(2025, 1, 1), direct_ef=2.0)
    db_session = FakeDbSession([old])

    with pytest.raises(ValueError):
        lookup_emission_factor(
            sector="steel",
            route="BF-BOF",
            country="FR",
            declaration_date=date(2026, 6, 1),
            db_session=db_session,
        )


def test_lookup_overlapping_records_raises_value_error():
    # Data-integrity guard: two records both claiming the same date is bad
    # versioned data and must fail loudly rather than pick one silently.
    first = _make_factor(date(2024, 1, 1), date(2026, 6, 1), direct_ef=2.0)
    second = _make_factor(date(2026, 1, 1), None, direct_ef=1.9)
    db_session = FakeDbSession([first, second])

    with pytest.raises(ValueError):
        lookup_emission_factor(
            sector="steel",
            route="BF-BOF",
            country="FR",
            declaration_date=date(2026, 3, 1),
            db_session=db_session,
        )
