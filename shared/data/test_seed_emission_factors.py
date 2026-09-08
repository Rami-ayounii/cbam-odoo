import pytest

from seed_emission_factors import (
    EMISSION_FACTOR_SEEDS,
    GOOD_BENCHMARK_SEEDS,
    YEAR_PARAMETER_SEEDS,
    find_incomplete_seeds,
    seed_odoo,
)


class FakeModelProxy:
    def __init__(self, store, name):
        self.store = store
        self.name = name

    def search(self, domain):
        records = self.store.setdefault(self.name, [])
        return [
            i
            for i, rec in enumerate(records)
            if all(rec.get(field) == value for field, _, value in domain)
        ]

    def create(self, vals):
        records = self.store.setdefault(self.name, [])
        records.append(dict(vals))
        return len(records) - 1

    def write(self, ids, vals):
        records = self.store[self.name]
        for i in ids:
            records[i].update(vals)


class FakeEnv:
    def __init__(self):
        self.store = {}

    def __getitem__(self, name):
        return FakeModelProxy(self.store, name)


def test_every_seed_has_a_source_document_citation():
    for seed in EMISSION_FACTOR_SEEDS + YEAR_PARAMETER_SEEDS + GOOD_BENCHMARK_SEEDS:
        assert seed.source_document, f"{seed} has no source_document citation"


def test_find_incomplete_seeds_flags_exactly_the_still_blocked_fields():
    # M7 (2026-09-08 re-attempt): the two GoodBenchmarkSeed records (steel
    # CN 7208, aluminium CN 7601) and markup_pct on every EmissionFactorSeed
    # got real, cited values (Commission Implementing Regulation (EU)
    # 2026/1412's benchmarks; IR 2025/2621's flat 10% 2026 markup rate) -
    # see docs/m7-source-verification.md. direct_ef on all five EmissionFactorSeed
    # records, and both YearParameterSeed fields, are still genuinely
    # blocked (not merely unattempted - each has a documented, cited reason
    # in seed_emission_factors.py). This test names exactly those and will
    # start failing (usefully) the moment any of them is filled in, or if a
    # regression drops something that was already verified.
    incomplete = find_incomplete_seeds()
    assert incomplete == [
        "emission_factor steel/BF-BOF/FR: direct_ef",
        "emission_factor steel/EAF_scrap/FR: direct_ef",
        "emission_factor steel/EAF_DRI/TR: direct_ef",
        "emission_factor aluminium/primary_electrolysis/NO: direct_ef",
        "emission_factor aluminium/secondary_recycled/TN: direct_ef",
        "year_parameter 2026: cbam_factor_year",
        "year_parameter 2026: reference_certificate_price",
    ]


def test_seed_odoo_refuses_to_write_incomplete_data_by_default():
    env = FakeEnv()

    with pytest.raises(ValueError):
        seed_odoo(env, allow_incomplete=False)

    assert env.store == {}


def test_seed_odoo_writes_when_allow_incomplete_is_true():
    env = FakeEnv()

    seed_odoo(env, allow_incomplete=True)

    assert len(env.store.get("cbam.emission.factor", [])) == len(EMISSION_FACTOR_SEEDS)
    assert len(env.store.get("cbam.year.parameter", [])) == len(YEAR_PARAMETER_SEEDS)
    assert len(env.store.get("cbam.production.route", [])) > 0


def test_seed_odoo_reuses_existing_production_route_instead_of_duplicating():
    env = FakeEnv()

    seed_odoo(env, allow_incomplete=True)
    routes_after_first_run = len(env.store["cbam.production.route"])

    seed_odoo(env, allow_incomplete=True)
    routes_after_second_run = len(env.store["cbam.production.route"])

    assert routes_after_second_run == routes_after_first_run
