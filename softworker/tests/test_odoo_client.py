from odoo_client import OdooClient


class _FakeGood:
    id = 5
    cn_code = "7213.10.00"
    sector = "steel"


class _FakeRoute:
    code = "BF-BOF"


class _FakeInstallation:
    id = 7
    name = "Ezz Steel Suez"
    country = "EG"
    production_route_id = _FakeRoute()


class _FakeDeclaration:
    id = 1
    reporting_year = 2026


class _FakeSourceDocument:
    id = 42
    attachment_filename = "mill-certificate.txt"


class _FakeLine:
    declaration_id = _FakeDeclaration()
    good_id = _FakeGood()
    installation_id = _FakeInstallation()
    quantity_tonnes = 41.88
    data_source = "actual"
    source_document_ids = [_FakeSourceDocument()]


class _FakeModel:
    def browse(self, line_id):
        assert line_id == 100
        return _FakeLine()


class _FakeOdoo:
    def __init__(self):
        self.env = {"cbam.declaration.line": _FakeModel()}


def test_get_declaration_line_context_reads_nested_fields():
    client = OdooClient.__new__(OdooClient)  # bypass odoorpc's real connection
    client._odoo = _FakeOdoo()

    context = client.get_declaration_line_context(100)

    assert context == {
        "declaration_id": 1,
        "reporting_year": 2026,
        "good_id": 5,
        "good_cn_code": "7213.10.00",
        "good_sector": "steel",
        "installation_id": 7,
        "installation_name": "Ezz Steel Suez",
        "installation_country": "EG",
        "production_route": "BF-BOF",
        "quantity_tonnes": 41.88,
        "data_source": "actual",
        "source_document_ids": [{"document_id": 42, "filename": "mill-certificate.txt"}],
    }
