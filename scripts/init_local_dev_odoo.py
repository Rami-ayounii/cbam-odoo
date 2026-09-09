"""One-time bring-up for docker-compose.local-dev.yml's Odoo instance:
creates the database (Odoo's HTTP database-manager endpoint), installs the
cbam module, and seeds shared/data/dev_fixtures.py's fake reference data.
Not part of the test suite - this is a live-infra bring-up script, nothing
here is unit-testable without a real Odoo instance to talk to.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "softworker" / "addons" / "cbam" / "utils"))
sys.path.insert(0, str(REPO_ROOT / "shared" / "data"))

import odoorpc  # noqa: E402

from dev_fixtures import seed_dev_fixtures_odoo  # noqa: E402


def wait_for_odoo(host, port, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if requests.get(f"http://{host}:{port}/web/login", timeout=3).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise TimeoutError(f"Odoo did not become reachable at {host}:{port} within {timeout}s")


def create_database(host, port, db, admin_login, admin_password, master_pwd="admin"):
    resp = requests.post(
        f"http://{host}:{port}/web/database/create",
        data={
            "master_pwd": master_pwd,
            "name": db,
            "login": admin_login,
            "password": admin_password,
            "lang": "en_US",
            "country_code": "",
            "phone": "",
        },
        timeout=120,
    )
    resp.raise_for_status()


def install_module(host, port, db, login, password, module_name="cbam"):
    odoo = odoorpc.ODOO(host, protocol="jsonrpc", port=port)
    odoo.login(db, login, password)
    module_ids = odoo.env["ir.module.module"].search([("name", "=", module_name)])
    if not module_ids:
        raise RuntimeError(f"module '{module_name}' not found in ir.module.module - check the addons mount")
    odoo.env["ir.module.module"].browse(module_ids).button_immediate_install()
    return odoo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8069)
    parser.add_argument("--db", default=os.environ.get("ODOO_DB", "cbam"))
    parser.add_argument("--admin-login", default=os.environ.get("ODOO_USER", "admin"))
    parser.add_argument("--admin-password", default=os.environ["ODOO_PASSWORD"])
    args = parser.parse_args()

    wait_for_odoo(args.host, args.port)
    create_database(args.host, args.port, args.db, args.admin_login, args.admin_password)
    odoo = install_module(args.host, args.port, args.db, args.admin_login, args.admin_password)
    fixture_ids = seed_dev_fixtures_odoo(odoo.env)
    print(f"Database '{args.db}' created, cbam module installed, dev fixtures seeded: {fixture_ids}")


if __name__ == "__main__":
    main()
