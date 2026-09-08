from dev_fixtures import (
    DEV_EMISSION_FACTOR_FIXTURES,
    DEV_SOURCE_LABEL,
    build_emission_factor_session,
)
from datetime import date


def test_every_fixture_is_clearly_labeled_as_fake():
    assert "DEV FIXTURE" in DEV_SOURCE_LABEL
    assert "not real" in DEV_SOURCE_LABEL.lower() or "NOT real" in DEV_SOURCE_LABEL


def test_fixtures_cover_every_default_sourced_combo_in_first_20_synthetic_records():
    import json
    from pathlib import Path

    index_path = Path(__file__).resolve().parent.parent / "synthetic_data" / "output" / "index.json"
    records = json.loads(index_path.read_text(encoding="utf-8"))[:20]
    needed = {
        (r["sector"], r["production_route"], r["country"])
        for r in records
        if r["data_source"] == "default"
    }
    covered = {(f.sector, f.route, f.country) for f in DEV_EMISSION_FACTOR_FIXTURES}
    assert needed <= covered


def test_build_emission_factor_session_resolves_a_known_combo():
    session = build_emission_factor_session()

    results = session.get_emission_factors("steel", "BF-BOF", "EG")

    assert len(results) == 1
    factor = results[0]
    assert factor.direct_ef > 0
    assert factor.valid_from == date(2026, 1, 1)


def test_build_emission_factor_session_resolves_a_real_emission_factor_id():
    # Regression test: without a real id, lookup_default_value's result
    # always had emission_factor_id=None, making a data_source="default"
    # write_declaration_line call structurally impossible in this harness
    # (tool_args.py requires a non-None emission_factor_id in that case) -
    # a live trace confirmed this (docs/PROGRESS.md's MVP-focused
    # follow-up section).
    session = build_emission_factor_session()

    factor = session.get_emission_factors("steel", "BF-BOF", "EG")[0]

    assert factor.id is not None


def test_build_emission_factor_session_empty_for_unknown_combo():
    session = build_emission_factor_session()

    assert session.get_emission_factors("steel", "BF-BOF", "ZZ") == []
