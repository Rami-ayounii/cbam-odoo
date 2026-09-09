from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .cbam_production_route import SECTOR_SELECTION


class CbamEmissionFactor(models.Model):
    _name = "cbam.emission.factor"
    _description = "CBAM Emission Factor (versioned)"

    sector = fields.Selection(SECTOR_SELECTION, required=True)
    production_route_id = fields.Many2one(
        "cbam.production.route",
        string="Production Route",
        required=True,
        ondelete="restrict",
    )
    country = fields.Char(
        string="Country Code",
        size=2,
        required=True,
        help="ISO 3166-1 alpha-2 exporting country code.",
    )
    direct_ef = fields.Float(
        string="Direct EF", digits=(16, 6), required=True,
        help="t CO2e per tonne of product.",
    )
    indirect_ef = fields.Float(
        string="Indirect EF", digits=(16, 6), default=0.0,
        help="t CO2e per tonne of product. 0 for steel & aluminium per Annex II.",
    )
    markup_pct = fields.Float(
        string="Markup %",
        help="Yearly markup applied to the default value (10% in 2026, rising through 2028).",
    )
    source_document = fields.Char(
        required=True,
        help="Citation, e.g. JRC134682 or EUR-Lex CELEX number. Never invent a value.",
    )
    valid_from = fields.Date(required=True)
    valid_to = fields.Date(
        help="Leave empty if this is the currently-in-effect record.",
    )

    @api.constrains("sector", "production_route_id", "country", "valid_from", "valid_to")
    def _check_no_overlap(self):
        for record in self:
            if record.valid_to and record.valid_to <= record.valid_from:
                raise ValidationError(
                    "valid_to must be strictly after valid_from."
                )

            siblings = self.search(
                [
                    ("id", "!=", record.id),
                    ("sector", "=", record.sector),
                    ("production_route_id", "=", record.production_route_id.id),
                    ("country", "=", record.country),
                ]
            )
            for sibling in siblings:
                record_end = record.valid_to or date.max
                sibling_end = sibling.valid_to or date.max
                if record.valid_from < sibling_end and sibling.valid_from < record_end:
                    raise ValidationError(
                        "Overlapping validity range for the same sector/route/"
                        "country: emission factors must never overlap "
                        f"(conflicts with record #{sibling.id})."
                    )
