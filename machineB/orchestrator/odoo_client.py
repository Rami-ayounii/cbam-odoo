"""odoorpc-based Odoo access for the orchestrator.

NOT RUNTIME-VERIFIED: no live Odoo instance is available in this dev
environment (no Docker/odoorpc target to connect to). This has only been
statically checked (py_compile), matching the same caveat as M3.

Read-only everywhere except write_declaration_line - the loop's single
validated write at the end (projecthandoff.md section 7: "Read-only access
to Odoo during the loop. Single write at the end.").

Imports calc_engine as a bare module (not `cbam.utils.calc_engine`) for the
same reason as tools.py: this process has no Odoo package installed.
"""

import base64

import odoorpc

from calc_engine import MAX_SOURCE_DOCUMENT_BYTES, emission_factor_from_record


class OdoorpcEmissionFactorSession:
    """get_emission_factors(...) duck-type for calc_engine.lookup_emission_factor,
    backed by an odoorpc connection - the orchestrator talks to Odoo over
    RPC, it is not an Odoo addon running inside the same process as M3's
    OdooEmissionFactorSession (which uses the in-process ORM env)."""

    def __init__(self, odoo):
        self._odoo = odoo

    def get_emission_factors(self, sector, route, country):
        model = self._odoo.env["cbam.emission.factor"]
        ids = model.search(
            [
                ("sector", "=", sector),
                ("production_route_id.code", "=", route),
                ("country", "=", country),
            ]
        )
        return [emission_factor_from_record(record) for record in model.browse(ids)]


class OdooClient:
    def __init__(self, host, port, db, login, password, protocol="jsonrpc+ssl"):
        self._odoo = odoorpc.ODOO(host, protocol=protocol, port=port)
        self._odoo.login(db, login, password)

    def get_source_document_text(self, document_id, expected_declaration_line_id):
        # Synthetic data (M1) is plain text, so a direct utf-8 decode of the
        # attachment is correct for current scope. Real scanned/image
        # documents would need OCR/PDF text-layer extraction added here -
        # out of scope until real (non-synthetic) documents are in play.
        model = self._odoo.env["cbam.source.document"]
        record = model.browse(int(document_id))
        # Ownership check: this RPC session authenticates as a single
        # privileged Odoo user (ODOO_USER), so it is never subject to the
        # declarant-scoped ir.rule records - this is the only thing
        # preventing an LLM-supplied document_id from leaking another
        # declarant's document text into this job's context.
        if record.declaration_line_id.id != expected_declaration_line_id:
            raise ValueError(
                f"document {document_id} does not belong to this job's "
                "declaration line"
            )
        if not record.attachment:
            return ""
        raw = base64.b64decode(record.attachment)
        # Independent of cbam_source_document.py's own upload-time
        # constraint - this is the actual boundary that feeds the decoded
        # text into the LLM's prompt, so it caps regardless of whether the
        # record got here via the addon's validated create/write path.
        if len(raw) > MAX_SOURCE_DOCUMENT_BYTES:
            raise ValueError(
                f"document {document_id} attachment is {len(raw)} bytes, "
                f"exceeding the {MAX_SOURCE_DOCUMENT_BYTES}-byte cap - "
                "refusing to feed this into the LLM's context"
            )
        return raw.decode("utf-8", errors="replace")

    def get_emission_factor_session(self):
        return OdoorpcEmissionFactorSession(self._odoo)

    def get_declaration_line_context(self, declaration_line_id):
        """Read-only snapshot of the fields already set on this line before
        the job starts (good/installation/quantity - see main.py's
        docstring on why the model needs this, since no tool exists to look
        up a good's CN code or an installation's country from scratch).

        source_document_ids is included for the same reason: extract_field
        requires a document_id argument, but no tool exists to list a
        line's source documents - without their ids surfaced here, the
        model has no legal way to ever call extract_field at all. A real
        live trace (docs/PROGRESS.md's audit follow-up section) showed
        exactly this: extract_field called with a missing document_id,
        because none was ever given, and the model never retried it.
        """
        model = self._odoo.env["cbam.declaration.line"]
        record = model.browse(int(declaration_line_id))
        return {
            "declaration_id": record.declaration_id.id,
            "reporting_year": record.declaration_id.reporting_year,
            "good_id": record.good_id.id,
            "good_cn_code": record.good_id.cn_code,
            "good_sector": record.good_id.sector,
            "installation_id": record.installation_id.id,
            "installation_name": record.installation_id.name,
            "installation_country": record.installation_id.country,
            "production_route": record.installation_id.production_route_id.code,
            "quantity_tonnes": record.quantity_tonnes,
            "data_source": record.data_source,
            "source_document_ids": [
                {"document_id": doc.id, "filename": doc.attachment_filename}
                for doc in record.source_document_ids
            ],
        }

    def write_declaration_line(self, declaration_line_id, **data):
        # Updates the existing job-scoped line (the one the source document
        # is attached to and the one Odoo's UI is polling/displaying - see
        # docs/PROGRESS.md's data flow step 6: "Odoo polls -> sees completed
        # -> reloads the declaration line record", singular, the same
        # record). This used to call model.create(data), which created a
        # brand-new, disconnected cbam.declaration.line under the right
        # declaration but with no link back to the source document or to
        # the declaration_line_id the job/UI was actually tracking - the
        # line the user was looking at would stay empty forever while an
        # orphan record silently held the real data. declaration_line_id is
        # supplied by the job's own scope (tools.py), never by the LLM, for
        # the same reason declaration_id is checked there: the write target
        # must not be something an LLM tool call gets to pick.
        model = self._odoo.env["cbam.declaration.line"]
        model.write([declaration_line_id], data)
        return declaration_line_id

    def write_llm_trace(self, declaration_line_id, messages, extraction_status):
        # The intended audit trail (cbam_source_document.raw_llm_output) was
        # defined but never written to anywhere - without this, there is no
        # way to reconstruct what tool calls the LLM actually made for a
        # given job after the fact.
        model = self._odoo.env["cbam.source.document"]
        ids = model.search([("declaration_line_id", "=", declaration_line_id)])
        if ids:
            model.write(
                ids, {"raw_llm_output": messages, "extraction_status": extraction_status}
            )
