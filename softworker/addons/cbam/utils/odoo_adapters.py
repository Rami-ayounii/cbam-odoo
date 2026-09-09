"""Odoo-ORM adapters for calc_engine.

Kept separate from calc_engine.py so the calc engine itself stays a plain,
Odoo-free Python module that softworker/tests/test_calc_engine.py can import
and unit-test without a running Odoo instance.
"""

from .calc_engine import emission_factor_from_record


class OdooEmissionFactorSession:
    """Implements the get_emission_factors(sector, route, country) duck-type
    that calc_engine.lookup_emission_factor expects, backed by the Odoo ORM.
    """

    def __init__(self, env):
        self.env = env

    def get_emission_factors(self, sector, route, country):
        records = self.env["cbam.emission.factor"].search(
            [
                ("sector", "=", sector),
                ("production_route_id.code", "=", route),
                ("country", "=", country),
            ]
        )
        return [emission_factor_from_record(record) for record in records]
