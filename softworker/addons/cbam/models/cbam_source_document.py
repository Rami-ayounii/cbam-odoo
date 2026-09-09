import base64

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils.calc_engine import MAX_SOURCE_DOCUMENT_BYTES

EXTRACTION_STATUS_SELECTION = [
    ("pending", "Pending"),
    ("extracted", "Extracted"),
    ("needs_review", "Needs Review"),
    ("failed", "Failed"),
]


class CbamSourceDocument(models.Model):
    _name = "cbam.source.document"
    _description = "CBAM Source Document (supplier document + LLM extraction audit trail)"

    declaration_line_id = fields.Many2one(
        "cbam.declaration.line", string="Declaration Line", required=True, ondelete="cascade"
    )
    attachment = fields.Binary(string="Document", required=True, attachment=True)
    attachment_filename = fields.Char(string="Filename")
    extraction_status = fields.Selection(
        EXTRACTION_STATUS_SELECTION, default="pending", required=True
    )
    raw_llm_output = fields.Json(
        string="Raw LLM Output",
        help="Full tool-call trace from the orchestrator agent loop for this "
        "document - audit trail, never edited by hand.",
    )

    @api.constrains("attachment")
    def _check_attachment_size(self):
        # These are meant to be plain-text CBAM supplier documents that get
        # decoded whole and fed straight into the LLM's prompt
        # (odoo_client.get_source_document_text) - nothing about that flow
        # is designed to handle an arbitrarily large binary, so reject one
        # at upload time rather than let it reach the orchestrator.
        for record in self:
            if not record.attachment:
                continue
            decoded_size = len(base64.b64decode(record.attachment))
            if decoded_size > MAX_SOURCE_DOCUMENT_BYTES:
                raise ValidationError(
                    f"Attachment is {decoded_size} bytes, exceeding the "
                    f"{MAX_SOURCE_DOCUMENT_BYTES}-byte cap for CBAM source "
                    "documents."
                )
