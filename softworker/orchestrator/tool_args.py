"""Pydantic argument models for each of the 7 tools, mirroring
shared/tool_schemas/*.json. A small local model (7-8B) will occasionally
return malformed tool-call arguments - wrong types, missing required
fields, invalid enum values. Validating here turns that into a clean
ValueError that agent_loop.py already feeds back to the model as a tool
error, instead of a raw TypeError crashing the dispatcher.
"""

from typing import Literal, Optional

from pydantic import BaseModel, model_validator

# Hard backstops on the one tool call that actually persists data, shared
# with tools.py's check_consistency (which uses the same bound, just as an
# advisory issue the model sees rather than an unconditional rejection).
# Document text is untrusted input fed straight into the LLM's context
# (see agent_loop.py / tools.py._extract_field) - a malicious or garbled
# supplier document could try to push an absurd value through as if it were
# a legitimate extraction, regardless of whatever check_consistency advised.
# These bounds make that impossible at the point of the real write, not
# just visible-but-ignorable in an advisory tool result.
MAX_QUANTITY_TONNES = 1_000_000.0
PLAUSIBLE_EF_MAX = 50.0

Sector = Literal["steel", "aluminium"]
Route = Literal["BF-BOF", "EAF_scrap", "EAF_DRI", "primary_electrolysis", "secondary_recycled"]
FieldName = Literal[
    "cn_code",
    "quantity_tonnes",
    "installation_name",
    "installation_country",
    "production_route",
    "direct_emissions_actual",
    "indirect_emissions_actual",
    "carbon_price_paid_origin",
]


class ExtractFieldArgs(BaseModel):
    document_id: str
    field_name: FieldName


class LookupDefaultValueArgs(BaseModel):
    sector: Sector
    route: Route
    country: str


class CheckConsistencyArgs(BaseModel):
    extracted_data: dict


class RequestMissingDataArgs(BaseModel):
    field_name: str
    reason: str


class FlagForHumanReviewArgs(BaseModel):
    reason: str


class CalculateEmissionsArgs(BaseModel):
    quantity_tonnes: float
    direct_ef: float
    indirect_ef: float = 0.0
    precursor_emissions: float = 0.0
    carbon_price_paid_origin: float = 0.0
    markup_pct: float = 0.0


class WriteDeclarationLineArgs(BaseModel):
    declaration_id: int
    good_id: int
    installation_id: int
    quantity_tonnes: float
    data_source: Literal["actual", "default"]
    direct_emissions_actual: float = 0.0
    indirect_emissions_actual: float = 0.0
    emission_factor_id: Optional[int] = None
    carbon_price_paid_origin: float = 0.0
    precursor_emissions: float = 0.0
    source_quote: Optional[str] = None

    @model_validator(mode="after")
    def _source_quote_required_for_actual_source(self):
        # Anti-hallucination gate for the two fields with the worst measured
        # accuracy (docs/PROGRESS.md's field-accuracy investigation:
        # direct_emissions_actual/indirect_emissions_actual at 7%, the only
        # fields needing genuine document-text reading rather than a
        # deterministic carried-over value). This only catches the cheap
        # case (missing/empty); tools.py._write_declaration_line does the
        # real check - is this actually a substring of document_text the
        # model was shown this session - which needs session state this
        # model has no access to.
        if self.data_source == "actual" and not (self.source_quote or "").strip():
            raise ValueError(
                "source_quote is required and must be non-empty when "
                "data_source is 'actual' - quote the exact sentence from "
                "extract_field's document_text that the emissions figure "
                "came from"
            )
        return self

    @model_validator(mode="after")
    def _emission_factor_required_for_default_source(self):
        # Without this, data_source="default" + no emission_factor_id writes
        # a line whose embedded_emissions_total silently computes to 0
        # (Odoo's empty-recordset field access), an invisible zero rather
        # than an error - see cbam_declaration_line.py's dependence on
        # emission_factor_id.direct_ef/indirect_ef.
        if self.data_source == "default" and self.emission_factor_id is None:
            raise ValueError(
                "emission_factor_id is required when data_source is 'default'"
            )
        # Mirrors write_declaration_line.json's own description ("Must be
        # omitted/null when data_source = actual") - without this the
        # schema and the actual validation disagreed: a model could supply
        # both data_source="actual" and an emission_factor_id, and it would
        # be silently accepted (then presumably ignored downstream) instead
        # of rejected per the documented contract.
        if self.data_source == "actual" and self.emission_factor_id is not None:
            raise ValueError(
                "emission_factor_id must be omitted/null when data_source is 'actual'"
            )
        return self

    @model_validator(mode="after")
    def _values_within_plausible_bounds(self):
        if not (0 < self.quantity_tonnes <= MAX_QUANTITY_TONNES):
            raise ValueError(
                f"quantity_tonnes must be > 0 and <= {MAX_QUANTITY_TONNES}"
            )
        for field_name in ("direct_emissions_actual", "indirect_emissions_actual"):
            value = getattr(self, field_name)
            if value < 0 or value > PLAUSIBLE_EF_MAX:
                raise ValueError(
                    f"{field_name}={value} is outside the plausible range "
                    f"(0-{PLAUSIBLE_EF_MAX} t CO2e/t)"
                )
        return self


TOOL_ARG_MODELS = {
    "extract_field": ExtractFieldArgs,
    "lookup_default_value": LookupDefaultValueArgs,
    "check_consistency": CheckConsistencyArgs,
    "request_missing_data": RequestMissingDataArgs,
    "flag_for_human_review": FlagForHumanReviewArgs,
    "calculate_emissions": CalculateEmissionsArgs,
    "write_declaration_line": WriteDeclarationLineArgs,
}
