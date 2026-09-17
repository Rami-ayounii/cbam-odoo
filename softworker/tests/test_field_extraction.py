"""Tests for field_extraction.py's deterministic regex pre-parse - the
punch list's "Add #1" item (docs/PROGRESS.md): M1's synthetic generator
produces fixed-template documents, so a templated numeric field like
"Direct embedded emissions : 0.105 tCO2e/t" doesn't need an LLM to read it
correctly. Real-world documents won't match these exact templates - this
targets the harness's own document shapes, not general-purpose OCR/NLP.
"""

from field_extraction import regex_extract_field


MILL_CERT_TEXT = """
MILL TEST CERTIFICATE — EN 10204 TYPE 3.1
CN Code      : 7605.11.00
Description  : Wire of aluminium, not alloyed, diameter > 7mm

QUANTITY
Net mass : 281810.0 kg

CARBON INTENSITY DECLARATION (CBAM Annex III)
Production route          : secondary_recycled
Direct embedded emissions : 0.105 tCO2e/t
Indirect embedded emissions: 0.331 tCO2e/t
Carbon price paid (origin) : 12.04 EUR/tCO2e
""".strip()

CARBON_INTENSITY_TEXT = """
CBAM CARBON INTENSITY REPORT
INSTALLATION
Quantity covered   : 45.63 t

EMISSIONS DATA
Direct embedded emissions  : 0.199 tCO2e / tonne of product
Indirect embedded emissions: 0.367 tCO2e / tonne of product
Carbon price paid at origin: 0.0 EUR/tCO2e (ETS compliance)
""".strip()

CUSTOMS_TEXT = """
SINGLE ADMINISTRATIVE DOCUMENT — IMPORT ENTRY SUMMARY
GOODS
CN Code     : 7208.10.00
Net mass    : 405.08 tonnes
""".strip()

NO_CARBON_PRICE_TEXT = """
CARBON INTENSITY DECLARATION (CBAM Annex III)
Direct embedded emissions : 1.9 tCO2e/t
Indirect embedded emissions: 0.1 tCO2e/t
""".strip()


def test_extracts_direct_emissions_from_mill_certificate_format():
    result = regex_extract_field(MILL_CERT_TEXT, "direct_emissions_actual")
    assert result["value"] == 0.105
    assert "0.105" in result["matched_line"]


def test_extracts_indirect_emissions_no_space_before_colon():
    result = regex_extract_field(MILL_CERT_TEXT, "indirect_emissions_actual")
    assert result["value"] == 0.331


def test_extracts_emissions_from_carbon_intensity_report_format():
    result = regex_extract_field(CARBON_INTENSITY_TEXT, "direct_emissions_actual")
    assert result["value"] == 0.199
    result2 = regex_extract_field(CARBON_INTENSITY_TEXT, "indirect_emissions_actual")
    assert result2["value"] == 0.367


def test_extracts_carbon_price_paid_origin_style_label():
    result = regex_extract_field(MILL_CERT_TEXT, "carbon_price_paid_origin")
    assert result["value"] == 12.04


def test_extracts_carbon_price_paid_at_origin_style_label():
    result = regex_extract_field(CARBON_INTENSITY_TEXT, "carbon_price_paid_origin")
    assert result["value"] == 0.0


def test_carbon_price_absent_defaults_to_zero_not_none():
    # The generator only ever emits a carbon-price line when the value is
    # > 0 - absence is a real, structural signal that it's 0, not a parse
    # failure. Flagged as an inferred default, not a literal quote.
    result = regex_extract_field(NO_CARBON_PRICE_TEXT, "carbon_price_paid_origin")
    assert result["value"] == 0.0
    assert result["matched_line"] is None
    assert result["inferred_default"] is True


def test_extracts_quantity_converting_kg_to_tonnes():
    result = regex_extract_field(MILL_CERT_TEXT, "quantity_tonnes")
    assert result["value"] == 281.81


def test_extracts_quantity_already_in_tonnes():
    result = regex_extract_field(CARBON_INTENSITY_TEXT, "quantity_tonnes")
    assert result["value"] == 45.63


def test_extracts_quantity_from_customs_declaration_tonnes_label():
    result = regex_extract_field(CUSTOMS_TEXT, "quantity_tonnes")
    assert result["value"] == 405.08


def test_extracts_cn_code():
    result = regex_extract_field(CUSTOMS_TEXT, "cn_code")
    assert result["value"] == "7208.10.00"


def test_returns_none_when_field_genuinely_absent():
    # e.g. a "hard"-difficulty record where the field is in missing_fields -
    # must not fabricate a value.
    text = "MILL TEST CERTIFICATE\nCN Code : 7208.10.00\n"
    assert regex_extract_field(text, "direct_emissions_actual") is None


def test_returns_none_for_a_field_name_with_no_pattern():
    assert regex_extract_field(MILL_CERT_TEXT, "installation_name") is None


def test_direct_emissions_not_confused_with_indirect_line():
    # Real bug found live against the actual generated dataset:
    # "Direct embedded emissions" is a literal substring of "Indirect
    # embedded emissions", so a pattern without a word boundary matched the
    # indirect line's number when direct_emissions_actual was genuinely
    # absent (in missing_fields) and only the indirect line was present.
    text = (
        "EMISSIONS DATA\n"
        "Indirect embedded emissions: 5.829 tCO2e / tonne of product\n"
    )
    assert regex_extract_field(text, "direct_emissions_actual") is None
    result = regex_extract_field(text, "indirect_emissions_actual")
    assert result["value"] == 5.829


def test_carbon_price_not_inferred_for_customs_declaration_without_emissions_section():
    # Real bug found live: customs_declaration documents never state
    # carbon price at all, regardless of the real ground-truth value - the
    # zero-default inference must not fire outside an emissions-declaration
    # section, or it silently overwrites a real nonzero value with 0.
    text = (
        "SINGLE ADMINISTRATIVE DOCUMENT — IMPORT ENTRY SUMMARY\n"
        "CN Code     : 7208.10.00\n"
        "Net mass    : 405.08 tonnes\n"
    )
    assert regex_extract_field(text, "carbon_price_paid_origin") is None
