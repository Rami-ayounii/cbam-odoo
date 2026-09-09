{
    "name": "CBAM Declarations",
    "version": "17.0.1.0.0",
    "summary": "CBAM declarations for steel and aluminium imports (academic project)",
    "description": """
CBAM (Carbon Border Adjustment Mechanism) declaration module for steel and
aluminium imports only. All compliance calculations are deterministic Python
(see utils/calc_engine.py) - this module never lets the ORM or any LLM
compute a compliance number, it only stores inputs and displays computed
outputs.
""",
    "category": "Accounting/Localizations",
    "author": "Academic project - stage 2eme",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/cbam_security_rules.xml",
        "views/cbam_declaration_views.xml",
        "views/cbam_declaration_line_views.xml",
        "views/cbam_source_document_views.xml",
        "views/cbam_menus.xml",
        "reports/cbam_declaration_report.xml",
    ],
    "installable": True,
    "application": True,
}
