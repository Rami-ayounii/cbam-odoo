import json
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).resolve().parent

EXPECTED_SCHEMAS = {
    "extract_field": {"document_id", "field_name"},
    "lookup_default_value": {"sector", "route", "country"},
    "check_consistency": {"extracted_data"},
    "request_missing_data": {"field_name", "reason"},
    "flag_for_human_review": {"reason"},
    "calculate_emissions": {"quantity_tonnes", "direct_ef"},
    "write_declaration_line": {
        "declaration_id",
        "good_id",
        "installation_id",
        "quantity_tonnes",
        "data_source",
    },
}


def _load(name):
    path = SCHEMA_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("name", sorted(EXPECTED_SCHEMAS))
def test_schema_file_exists_and_is_valid_json(name):
    schema = _load(name)
    assert schema["name"] == name


@pytest.mark.parametrize("name", sorted(EXPECTED_SCHEMAS))
def test_schema_has_name_description_parameters(name):
    schema = _load(name)
    assert isinstance(schema["name"], str) and schema["name"]
    assert isinstance(schema["description"], str) and schema["description"]
    assert schema["parameters"]["type"] == "object"
    assert "properties" in schema["parameters"]


@pytest.mark.parametrize("name", sorted(EXPECTED_SCHEMAS))
def test_schema_required_fields_are_declared_as_properties(name):
    schema = _load(name)
    properties = set(schema["parameters"]["properties"].keys())
    required = set(schema["parameters"].get("required", []))
    # every required field must actually exist as a property
    assert required.issubset(properties)
    # every field the orchestrator's dispatcher expects must be required
    assert EXPECTED_SCHEMAS[name].issubset(required)


def test_write_declaration_line_description_states_it_is_the_completion_signal():
    schema = _load("write_declaration_line")
    assert "not considered done" in schema["description"]


def test_no_duplicate_tool_names_across_all_schemas():
    names = [json.loads(p.read_text(encoding="utf-8"))["name"] for p in SCHEMA_DIR.glob("*.json")]
    assert len(names) == len(set(names))


def test_all_seven_tools_present():
    files = {p.stem for p in SCHEMA_DIR.glob("*.json")}
    assert files == set(EXPECTED_SCHEMAS)
