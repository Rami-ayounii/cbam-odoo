from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils.calc_engine import (
    calculate_certificates_required,
    calculate_embedded_emissions,
    lookup_emission_factor,
)
from ..utils.odoo_adapters import OdooEmissionFactorSession

DATA_SOURCE_SELECTION = [
    ("actual", "Actual"),
    ("default", "Default"),
]

CERTIFICATES_STATUS_SELECTION = [
    ("computed", "Computed"),
    ("exempt", "Exempt (< 50 t/year)"),
    ("incomplete", "Incomplete - missing reference data"),
]


class CbamDeclarationLine(models.Model):
    _name = "cbam.declaration.line"
    _description = "CBAM Declaration Line"

    declaration_id = fields.Many2one(
        "cbam.declaration", string="Declaration", required=True, ondelete="cascade"
    )
    good_id = fields.Many2one(
        "cbam.good", string="Good", required=True, ondelete="restrict"
    )
    installation_id = fields.Many2one(
        "cbam.installation", string="Installation", required=True, ondelete="restrict"
    )
    quantity_tonnes = fields.Float(required=True, digits=(16, 3))
    data_source = fields.Selection(
        DATA_SOURCE_SELECTION, required=True, default="default"
    )

    direct_emissions_actual = fields.Float(
        string="Direct EF (actual)",
        digits=(16, 6),
        help="Only used when data_source = actual.",
    )
    indirect_emissions_actual = fields.Float(
        string="Indirect EF (actual)",
        digits=(16, 6),
        help="Only used when data_source = actual.",
    )
    emission_factor_id = fields.Many2one(
        "cbam.emission.factor",
        string="Emission Factor (default)",
        help="Only used when data_source = default. Populate via "
        "'Lookup Default Emission Factor'.",
    )
    carbon_price_paid_origin = fields.Float(
        string="Carbon Price Paid (Origin)",
        digits=(16, 2),
        help="EUR/t CO2e already paid in the exporting country.",
    )
    precursor_emissions = fields.Float(
        string="Precursor Emissions",
        digits=(16, 3),
        help="t CO2e already embedded in precursor materials (complex/downstream goods only).",
    )

    embedded_emissions_total = fields.Float(
        compute="_compute_embedded_emissions_total", store=True, digits=(16, 3)
    )
    year_parameter_id = fields.Many2one(
        "cbam.year.parameter",
        string="Year Parameter",
        compute="_compute_year_parameter_id",
        store=True,
        help="Resolved cbam.year.parameter record for the declaration's "
        "reporting year. Stored as a real relation (not just looked up "
        "inline inside _compute_certificates_required) so that editing an "
        "existing cbam.year.parameter's cbam_factor_year or "
        "reference_certificate_price correctly triggers a recompute of "
        "certificates_required via @api.depends - a plain search() call "
        "inside the compute method would not be tracked as a dependency.",
    )
    good_benchmark_id = fields.Many2one(
        "cbam.good.benchmark",
        string="EU ETS Benchmark",
        compute="_compute_good_benchmark_id",
        store=True,
        help="Resolved cbam.good.benchmark record for this line's good "
        "AND production route. EU ETS benchmarks are route-specific (the "
        "'Hot metal' benchmark applies to BF-BOF, not to scrap-EAF, for "
        "example) - looking this up by good_id alone, as an earlier "
        "version of this module did, silently applied the wrong route's "
        "benchmark. Stored as a real relation for the same @api.depends "
        "tracking reason as year_parameter_id above.",
    )
    certificates_required = fields.Float(
        compute="_compute_certificates_required", store=True, digits=(16, 3)
    )
    certificates_status = fields.Selection(
        CERTIFICATES_STATUS_SELECTION,
        compute="_compute_certificates_required",
        store=True,
        help="Distinguishes WHY certificates_required is 0.0: a genuinely "
        "exempt line vs. one that's 0.0 only because a year parameter or "
        "route-specific EU ETS benchmark hasn't been seeded yet (M7). "
        "Without this the two cases were visually identical in the UI - "
        "an incomplete line looked exactly like a compliant, exempt one.",
    )

    source_document_ids = fields.One2many(
        "cbam.source.document", "declaration_line_id", string="Source Documents"
    )

    @api.depends(
        "quantity_tonnes",
        "data_source",
        "direct_emissions_actual",
        "indirect_emissions_actual",
        "emission_factor_id.direct_ef",
        "emission_factor_id.indirect_ef",
        "emission_factor_id.markup_pct",
        "precursor_emissions",
    )
    def _compute_embedded_emissions_total(self):
        for line in self:
            if line.data_source == "actual":
                direct_ef = line.direct_emissions_actual
                indirect_ef = line.indirect_emissions_actual
                markup_pct = 0.0
            else:
                direct_ef = line.emission_factor_id.direct_ef
                indirect_ef = line.emission_factor_id.indirect_ef
                markup_pct = line.emission_factor_id.markup_pct

            line.embedded_emissions_total = calculate_embedded_emissions(
                quantity_tonnes=line.quantity_tonnes,
                direct_ef=direct_ef,
                indirect_ef=indirect_ef,
                precursor_emissions=line.precursor_emissions,
                markup_pct=markup_pct,
            )

    @api.depends("good_id", "installation_id.production_route_id")
    def _compute_good_benchmark_id(self):
        for line in self:
            if not line.good_id or not line.installation_id.production_route_id:
                line.good_benchmark_id = False
                continue
            line.good_benchmark_id = self.env["cbam.good.benchmark"].search(
                [
                    ("good_id", "=", line.good_id.id),
                    (
                        "production_route_id",
                        "=",
                        line.installation_id.production_route_id.id,
                    ),
                ],
                limit=1,
            )

    @api.depends(
        "embedded_emissions_total",
        "quantity_tonnes",
        "good_benchmark_id.benchmark",
        "carbon_price_paid_origin",
        "declaration_id.is_exempt",
        "year_parameter_id.cbam_factor_year",
        "year_parameter_id.reference_certificate_price",
    )
    def _compute_certificates_required(self):
        for line in self:
            if line.declaration_id.is_exempt:
                # 50 t/year exemption (docs/PROGRESS.md constraint): an
                # exempt declaration owes no certificates regardless of
                # embedded emissions, so this must short-circuit before the
                # year-parameter check below.
                line.certificates_required = 0.0
                line.certificates_status = "exempt"
                continue

            if line.data_source == "default" and not line.emission_factor_id:
                # A "default"-sourced line legitimately exists in this state
                # before the agent loop has run (write_declaration_line sets
                # emission_factor_id and data_source together in one atomic
                # write - see tools.py) - there is no ORM-level constraint
                # blocking it (a prior version of this module had one, which
                # made the agentic workflow itself impossible: no line could
                # ever start as data_source="default" without already having
                # the very emission factor the agent's job is to find).
                # Without this check, emission_factor_id.direct_ef/
                # indirect_ef silently evaluate to 0.0 (Odoo's empty-
                # recordset field access) and embedded_emissions_total looks
                # like a real, complete zero rather than an unresolved one -
                # this makes that visible instead.
                line.certificates_required = 0.0
                line.certificates_status = "incomplete"
                continue

            year_parameter = line.year_parameter_id
            if not year_parameter:
                # No versioned year parameter seeded yet for this reporting
                # year (M7) - can't produce a compliant number, so leave at
                # 0 rather than guess. The line stays visibly incomplete.
                line.certificates_required = 0.0
                line.certificates_status = "incomplete"
                continue

            if not line.good_benchmark_id:
                # No EU ETS benchmark seeded yet for this good's specific
                # production route (M7's "no route dimension" gap, now
                # fixed at the schema level - but real benchmark values for
                # non-primary routes like scrap-EAF steel or secondary
                # aluminium may still be genuinely unresolved against the
                # primary source, see shared/data/seed_emission_factors.py).
                # Leave at 0 rather than silently borrow another route's
                # benchmark. The line stays visibly incomplete.
                line.certificates_required = 0.0
                line.certificates_status = "incomplete"
                continue

            line.certificates_required = calculate_certificates_required(
                embedded_emissions_total=line.embedded_emissions_total,
                quantity_tonnes=line.quantity_tonnes,
                benchmark=line.good_benchmark_id.benchmark,
                cbam_factor_year=year_parameter.cbam_factor_year,
                carbon_price_paid_origin=line.carbon_price_paid_origin,
                reference_certificate_price=year_parameter.reference_certificate_price,
            )
            line.certificates_status = "computed"

    @api.constrains("good_id", "installation_id")
    def _check_sector_consistency(self):
        # Nothing in the ORM stops a line from pairing a steel good with an
        # aluminium installation (or an installation whose production route
        # is itself a different sector than the installation record claims -
        # possible via direct writes even though the UI wouldn't normally
        # allow it) - each sector lives on its own Selection field with no
        # relation between them. Silently mixing sectors would corrupt the
        # emission-factor lookup (which is keyed on good_id.sector) without
        # raising anything.
        for line in self:
            if not line.good_id or not line.installation_id:
                continue
            sectors = {line.good_id.sector, line.installation_id.sector}
            if line.installation_id.production_route_id:
                sectors.add(line.installation_id.production_route_id.sector)
            if len(sectors) > 1:
                raise ValidationError(
                    "Good, Installation, and Installation's Production "
                    "Route must all belong to the same sector "
                    f"(found: {', '.join(sorted(sectors))})."
                )

    @api.depends("declaration_id.reporting_year")
    def _compute_year_parameter_id(self):
        for line in self:
            if not line.declaration_id.reporting_year:
                line.year_parameter_id = False
                continue
            line.year_parameter_id = self.env["cbam.year.parameter"].search(
                [("year", "=", line.declaration_id.reporting_year)], limit=1
            )

    def action_lookup_emission_factor(self):
        """Populate emission_factor_id from the versioned reference table
        for lines using data_source = default. Read-only lookup: selects the
        applicable record, never writes an emission factor value itself.
        """
        for line in self:
            if line.data_source != "default":
                continue
            if not line.declaration_id.reporting_year:
                # Same guard as _compute_year_parameter_id(): nothing to
                # look up yet without a reporting year (e.g. a new/unsaved
                # declaration), so skip rather than build an invalid date
                # string like "0-01-01" or "False-01-01".
                continue

            # Always Jan 1 of the reporting year, never the line's actual
            # submission date: CBAM declarations are annual (one filing per
            # calendar year, projecthandoff.md §2), so any valid_from/valid_to
            # emission-factor transition that falls mid-year can never be
            # selected for that year's declaration. Revisit if a future
            # regulatory change moves CBAM back to sub-annual filing.
            declaration_date = fields.Date.from_string(
                f"{line.declaration_id.reporting_year}-01-01"
            )
            resolved = lookup_emission_factor(
                sector=line.good_id.sector,
                route=line.installation_id.production_route_id.code,
                country=line.installation_id.country,
                declaration_date=declaration_date,
                db_session=OdooEmissionFactorSession(line.env),
            )
            line.emission_factor_id = self.env["cbam.emission.factor"].search(
                [
                    ("sector", "=", resolved.sector),
                    ("production_route_id.code", "=", resolved.route),
                    ("country", "=", resolved.country),
                    ("valid_from", "=", resolved.valid_from),
                ],
                limit=1,
            )
