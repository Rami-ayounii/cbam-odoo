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
    benchmark_ids = fields.One2many(
        "cbam.good.benchmark",
        "good_id",
        string="EU ETS Benchmarks",
        help="Per-production-route EU ETS free-allocation benchmarks. A "
        "single CN code can map to more than one route (e.g. steel via "
        "BF-BOF vs. EAF), and each route's real-world benchmark differs -"
        " see cbam.good.benchmark.",
    )

    _sql_constraints = [
        (
            "cn_code_sector_unique",
            "unique(cn_code, sector)",
            "A CN code must be unique per sector.",
        ),
    ]
