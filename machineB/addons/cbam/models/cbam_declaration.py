from odoo import api, fields, models

from ..utils.calc_engine import is_exempt as calc_is_exempt

STATUS_SELECTION = [
    ("draft", "Draft"),
    ("submitted", "Submitted"),
    ("accepted", "Accepted"),
]


class CbamDeclaration(models.Model):
    _name = "cbam.declaration"
    _description = "CBAM Annual Declaration"
    _order = "reporting_year desc, id desc"

    declarant_id = fields.Many2one("res.partner", string="Declarant", required=True)
    reporting_year = fields.Integer(required=True)
    status = fields.Selection(STATUS_SELECTION, default="draft", required=True)
    submission_date = fields.Date()
    line_ids = fields.One2many("cbam.declaration.line", "declaration_id", string="Lines")

    total_quantity_tonnes = fields.Float(
        compute="_compute_total_quantity_tonnes", store=True, digits=(16, 3)
    )
    is_exempt = fields.Boolean(
        compute="_compute_is_exempt",
        store=True,
        help="True if total_quantity_tonnes is below the 50 t/year CBAM exemption threshold.",
    )

    @api.depends("line_ids.quantity_tonnes")
    def _compute_total_quantity_tonnes(self):
        for declaration in self:
            declaration.total_quantity_tonnes = sum(
                declaration.line_ids.mapped("quantity_tonnes")
            )

    @api.depends("total_quantity_tonnes")
    def _compute_is_exempt(self):
        for declaration in self:
            declaration.is_exempt = calc_is_exempt(declaration.total_quantity_tonnes)
