from odoo import fields, models

from .cbam_production_route import SECTOR_SELECTION


class CbamInstallation(models.Model):
    _name = "cbam.installation"
    _description = "CBAM Installation (exporting producer)"

    name = fields.Char(required=True)
    country = fields.Char(
        string="Country Code",
        size=2,
        required=True,
        help="ISO 3166-1 alpha-2 country code of the installation, e.g. FR, NO.",
    )
    sector = fields.Selection(SECTOR_SELECTION, required=True)
    production_route_id = fields.Many2one(
        "cbam.production.route",
        string="Production Route",
        required=True,
        ondelete="restrict",
    )
