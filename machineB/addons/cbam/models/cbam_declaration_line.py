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


class CbamDeclarationLine(models.Model):
    _name = "cbam.declaration.line"
    _description = "CBAM Declaration Line"

    declaration_id = fields.Many2one(
        "cbam.declaration", string="Declaration", required=True, ondelete="cascade"
    )
    good_id = fields.Many2one("cbam.good", string="Good", required=True)
    installation_id = fields.Many2one(
        "cbam.installation", string="Installation", required=True
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
    certificates_required = fields.Float(
        compute="_compute_certificates_required", store=True, digits=(16, 3)
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

    @api.depends(
        "embedded_emissions_total",
        "quantity_tonnes",
        "good_id.benchmark",
        "carbon_price_paid_origin",
        "declaration_id.reporting_year",
        "declaration_id.is_exempt",
    )
    def _compute_certificates_required(self):
        for line in self:
            if line.declaration_id.is_exempt:
                # 50 t/year exemption (docs/PROGRESS.md constraint): an
                # exempt declaration owes no certificates regardless of
                # embedded emissions, so this must short-circuit before the
                # year-parameter lookup below.
                line.certificates_required = 0.0
                continue

            year_parameter = line._get_year_parameter()
            if not year_parameter:
                # No versioned year parameter seeded yet for this reporting
                # year (M7) - can't produce a compliant number, so leave at
                # 0 rather than guess. The line stays visibly incomplete.
                line.certificates_required = 0.0
                continue

            line.certificates_required = calculate_certificates_required(
                embedded_emissions_total=line.embedded_emissions_total,
                quantity_tonnes=line.quantity_tonnes,
                benchmark=line.good_id.benchmark,
                cbam_factor_year=year_parameter.cbam_factor_year,
                carbon_price_paid_origin=line.carbon_price_paid_origin,
                reference_certificate_price=year_parameter.reference_certificate_price,
            )

    @api.constrains("data_source", "emission_factor_id")
    def _check_emission_factor_set_for_default_source(self):
        # Without this, an unset emission_factor_id on a data_source =
        # "default" line makes emission_factor_id.direct_ef/indirect_ef
        # silently evaluate to 0.0 (Odoo's empty-recordset field access),
        # producing a complete-looking line with zero embedded emissions
        # instead of a visible error.
        for line in self:
            if line.data_source == "default" and not line.emission_factor_id:
                raise ValidationError(
                    "Emission Factor (default) is required when Data Source "
                    "is 'Default'."
                )

    def _get_year_parameter(self):
        self.ensure_one()
        if not self.declaration_id.reporting_year:
            return self.env["cbam.year.parameter"]
        return self.env["cbam.year.parameter"].search(
            [("year", "=", self.declaration_id.reporting_year)], limit=1
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
                # Same guard as _get_year_parameter(): nothing to look up
                # yet without a reporting year (e.g. a new/unsaved
                # declaration), so skip rather than build an invalid date
                # string like "0-01-01" or "False-01-01".
                continue

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
