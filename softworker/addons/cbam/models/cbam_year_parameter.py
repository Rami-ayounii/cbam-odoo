from odoo import fields, models


class CbamYearParameter(models.Model):
    _name = "cbam.year.parameter"
    _description = "CBAM Year Parameters (phase-out factor and reference certificate price)"

    year = fields.Integer(required=True)
    cbam_factor_year = fields.Float(
        string="CBAM Phase-Out Factor",
        required=True,
        help="Free-allocation phase-out factor for this reporting year "
        "(e.g. 0.025 for 2026, rising to 1.0 by 2034). Reg. (EU) 2023/956 Art. 31.",
    )
    reference_certificate_price = fields.Float(
        string="Reference Certificate Price (EUR/t CO2e)",
        required=True,
        help="Published average CBAM certificate price for this year, used "
        "to convert a carbon price already paid abroad into an equivalent "
        "certificate deduction. Never hardcode - update yearly from the "
        "official publication.",
    )
    source_document = fields.Char(required=True)

    _sql_constraints = [
        ("year_unique", "unique(year)", "Only one parameter record per year."),
    ]
