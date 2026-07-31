from odoo import fields, models

from .cbam_production_route import SECTOR_SELECTION


class CbamGood(models.Model):
    _name = "cbam.good"
    _description = "CBAM Good (Annex I CN code)"

    cn_code = fields.Char(string="CN Code", required=True)
    description = fields.Char(required=True)
    sector = fields.Selection(SECTOR_SELECTION, required=True)
    is_complex_good = fields.Boolean(
        string="Complex/Downstream Good",
        help="True if this good has precursor materials whose embedded "
        "emissions carry through (formula sheet section 1.6).",
    )
    benchmark = fields.Float(
        string="EU ETS Benchmark",
        digits=(16, 6),
        help="EU ETS free-allocation benchmark for this good, t CO2e per "
        "tonne of product. Feeds calculate_certificates_required - never "
        "hardcode this in code, source it from the EU ETS benchmark "
        "decision in force for the reporting year.",
    )

    _sql_constraints = [
        (
            "cn_code_sector_unique",
            "unique(cn_code, sector)",
            "A CN code must be unique per sector.",
        ),
    ]
