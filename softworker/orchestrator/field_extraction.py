"""Deterministic regex pre-parse for extract_field, targeting the fixed
templates shared/synthetic_data/generator.py actually produces - "Direct
embedded emissions : 0.105 tCO2e/t" doesn't need an LLM to read correctly,
and a small model's own reading/recall reliability has been this project's
persistent ceiling on exactly these fields (docs/PROGRESS.md's
field-accuracy investigation).

Scope, deliberately narrow: this parses the harness's own known document
shapes (mill_certificate / carbon_intensity_report / customs_declaration),
not general-purpose document understanding - a real-world supplier document
in a different format will not match these patterns and falls back to the
model reading document_text itself, exactly as before this module existed.
"""

import re
from typing import Optional


def _first_match(document_text, patterns):
    for line in document_text.splitlines():
        for pattern in patterns:
            m = pattern.search(line)
            if m:
                return m, line.strip()
    return None, None


_DIRECT_EMISSIONS_PATTERNS = [
    # \b matters: "Direct embedded emissions" is a literal substring of
    # "Indirect embedded emissions" - without a word boundary before
    # "Direct", this pattern matched inside the indirect line too and
    # silently returned the wrong number (found live against the real
    # generated dataset, not hypothetical - see field_extraction tests).
    re.compile(r"\bDirect embedded emissions\s*:\s*([\d.]+)\s*tCO2e", re.IGNORECASE),
]
_INDIRECT_EMISSIONS_PATTERNS = [
    re.compile(r"Indirect embedded emissions\s*:\s*([\d.]+)\s*tCO2e", re.IGNORECASE),
]
# Matches both "Carbon price paid (origin) :" and "Carbon price paid at
# origin:" - the generator uses different label wording per document type
# (mill_certificate vs. carbon_intensity_report) for the same field.
_CARBON_PRICE_PATTERNS = [
    re.compile(r"Carbon price paid[^:\n]*:\s*([\d.]+)\s*EUR", re.IGNORECASE),
]
_QUANTITY_PATTERNS = [
    re.compile(r"Net mass\s*:\s*([\d.]+)\s*(kg|tonnes|t)\b", re.IGNORECASE),
    re.compile(r"Quantity covered\s*:\s*([\d.]+)\s*(kg|t)\b", re.IGNORECASE),
]
_CN_CODE_PATTERNS = [
    re.compile(r"CN Code\s*:\s*([\d.]+)"),
]


def regex_extract_field(document_text: str, field_name: str) -> Optional[dict]:
    """Returns {"value", "matched_line"} (plus "inferred_default": True for
    a value inferred from the field's absence, not a literal quote) when a
    deterministic pattern matches, else None - never fabricates a value for
    a field genuinely missing from the document (e.g. a "hard"-difficulty
    record with this field in missing_fields)."""
    if field_name in ("direct_emissions_actual", "indirect_emissions_actual"):
        patterns = (
            _DIRECT_EMISSIONS_PATTERNS
            if field_name == "direct_emissions_actual"
            else _INDIRECT_EMISSIONS_PATTERNS
        )
        m, line = _first_match(document_text, patterns)
        if m is None:
            return None
        return {"value": float(m.group(1)), "matched_line": line}

    if field_name == "carbon_price_paid_origin":
        m, line = _first_match(document_text, _CARBON_PRICE_PATTERNS)
        if m is not None:
            return {"value": float(m.group(1)), "matched_line": line}
        # The generator only emits this line at all in an emissions-
        # declaration section (mill_certificate's "CARBON INTENSITY
        # DECLARATION" block, carbon_intensity_report's "EMISSIONS DATA"
        # block), and only when the value is > 0 there - so its absence is
        # a real, structural signal of 0, but ONLY inside such a section.
        # A customs_declaration document never has one of these sections
        # regardless of the real carbon price paid (confirmed against the
        # full generated dataset: 2 records had a real nonzero
        # carbon_price_paid_origin ground truth on a customs_declaration
        # document, which this check correctly leaves unmatched instead of
        # wrongly defaulting to 0).
        if "CARBON INTENSITY DECLARATION" in document_text or "EMISSIONS DATA" in document_text:
            return {"value": 0.0, "matched_line": None, "inferred_default": True}
        return None

    if field_name == "quantity_tonnes":
        m, line = _first_match(document_text, _QUANTITY_PATTERNS)
        if m is None:
            return None
        value, unit = float(m.group(1)), m.group(2).lower()
        if unit == "kg":
            value = value / 1000.0
        return {"value": round(value, 6), "matched_line": line}

    if field_name == "cn_code":
        m, line = _first_match(document_text, _CN_CODE_PATTERNS)
        if m is None:
            return None
        return {"value": m.group(1), "matched_line": line}

    return None
