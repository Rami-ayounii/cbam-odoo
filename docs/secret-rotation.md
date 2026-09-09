# Secret Rotation Procedure

All secrets live in `hardworker/.env` and `softworker/.env` (gitignored via the
root `.gitignore`'s `*.env` pattern - confirmed with `git check-ignore -v`).
Never commit either file; only `.env.example` (with placeholder values) is
tracked.

## Secrets and how to rotate each

| Secret | File | Rotation steps |
|---|---|---|
| `OLLAMA_API_KEY` | `hardworker/.env` and `softworker/.env` (must match on both) | 1. Generate a new value: `openssl rand -hex 32`. 2. Update it in both `.env` files. 3. `docker compose up -d --force-recreate nginx` on Hardworker, then `docker compose up -d --force-recreate orchestrator` on Softworker. Old key stops working the moment nginx reloads - there is no overlap window, so do this during a maintenance gap. |
| `TS_AUTHKEY` | `hardworker/.env`, `softworker/.env` | Tailscale auth keys are typically ephemeral/single-use per the M0 setup; generate a fresh one at https://login.tailscale.com/admin/settings/keys before any container recreate that would re-trigger `tailscale up`. Revoke the old key in the Tailscale admin console once the new one is confirmed working. |
| `POSTGRES_PASSWORD` | `softworker/.env` | Requires an in-place Postgres password change, not just an env var swap (Postgres doesn't re-read `POSTGRES_PASSWORD` after first init). Run `ALTER USER odoo WITH PASSWORD 'new-password';` inside the `db` container, then update `.env` and recreate the `odoo` and `orchestrator` containers so they pick up the new value. |
| `ODOO_PASSWORD` | `softworker/.env` | Change the admin password from the Odoo UI (Settings > Users) or via `odoo-bin shell`, then update `.env` to match and recreate the `orchestrator` container (it authenticates via `odoorpc` using this password). |
| `ORCHESTRATOR_API_KEY` | `softworker/.env` (and wherever Odoo-side code calls the orchestrator) | 1. Generate a new value: `openssl rand -hex 32`. 2. Update it in `softworker/.env` and in the Odoo-side caller's config. 3. `docker compose up -d --force-recreate orchestrator`. Old key stops working immediately - no overlap window, same as `OLLAMA_API_KEY`. |

## General rule

Rotate `OLLAMA_API_KEY` and `ODOO_PASSWORD` immediately if either `.env`
file is ever accidentally committed, shared, or exposed in a log/screenshot
- even though `.gitignore` prevents normal commits, `git add -f` or a copy
into another file wouldn't be caught. Check with `git log --all --full-history -- '*.env'`
periodically to confirm no `.env` file was ever force-added.
