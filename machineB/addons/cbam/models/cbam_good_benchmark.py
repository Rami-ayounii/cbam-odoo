from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CbamGoodBenchmark(models.Model):
    _name = "cbam.good.benchmark"
    _description = "CBAM EU ETS Benchmark (per good, per production route)"

    good_id = fields.Many2one(
        "cbam.good", string="Good", required=True, ondelete="cascade"
    )
    production_route_id = fields.Many2one(
        "cbam.production.route",
        string="Production Route",
        required=True,
        ondelete="restrict",
    )
    benchmark = fields.Float(
        string="EU ETS Benchmark",
        digits=(16, 6),
        help="EU ETS free-allocation benchmark, t CO2e per tonne of "
        "product, for this good under this specific production route. "
        "Feeds calculate_certificates_required - never hardcode this in "
        "code, source it from the EU ETS benchmark decision in force for "
        "the reporting year.",
    )
    source_document = fields.Char(
        required=True,
        help="Citation for the benchmark value. Never invent a value.",
    )

    _sql_constraints = [
        (
            "good_route_unique",
            "unique(good_id, production_route_id)",
            "A benchmark must be unique per good and production route.",
        ),
    ]

    @api.constrains("good_id", "production_route_id")
    def _check_sector_consistency(self):
        # A single EU ETS product benchmark (e.g. "Hot metal" for CN 7208)
        # is specific to one production route (docs/PROGRESS.md's M7
        # section: applying the BF-BOF hot-metal benchmark to a scrap-EAF
        # route silently understated the certificate requirement to zero).
        # This only catches the good/route sector mismatch case (steel good
        # with an aluminium route, or vice versa) - it can't catch "right
        # sector, wrong route" since that's exactly what this model exists
        # to let differ per route.
        for record in self:
            if record.good_id.sector != record.production_route_id.sector:
                raise ValidationError(
                    "Good and Production Route must belong to the same "
                    f"sector (found: {record.good_id.sector} good, "
                    f"{record.production_route_id.sector} route)."
                )
