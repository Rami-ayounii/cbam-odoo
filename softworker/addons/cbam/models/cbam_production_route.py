from odoo import api, fields, models

SECTOR_SELECTION = [
    ("steel", "Steel"),
    ("aluminium", "Aluminium"),
]

ROUTE_CODE_SELECTION = [
    ("BF-BOF", "Blast Furnace - Basic Oxygen Furnace"),
    ("EAF_scrap", "Electric Arc Furnace - Scrap"),
    ("EAF_DRI", "Electric Arc Furnace - DRI"),
    ("primary_electrolysis", "Primary Electrolysis"),
    ("secondary_recycled", "Secondary Recycled"),
]


class CbamProductionRoute(models.Model):
    _name = "cbam.production.route"
    _description = "CBAM Production Route"

    code = fields.Selection(ROUTE_CODE_SELECTION, required=True)
    sector = fields.Selection(SECTOR_SELECTION, required=True)
    name = fields.Char(compute="_compute_name", store=True)

    _sql_constraints = [
        (
            "code_sector_unique",
            "unique(code, sector)",
            "A production route code must be unique per sector.",
        ),
    ]

    @api.depends("code")
    def _compute_name(self):
        code_labels = dict(ROUTE_CODE_SELECTION)
        for route in self:
            route.name = code_labels.get(route.code, route.code)
