FROM python:3.11-slim

WORKDIR /app

# Build context is the repo root (see ../docker-compose.yml), not this
# directory, specifically so this COPY can reach calc_engine.py and
# shared/tool_schemas/ without them needing to be duplicated or published as
# their own package. calc_engine.py is copied in bare (not as part of the
# cbam package) so importing it here never triggers cbam/__init__.py ->
# models -> `import odoo`, which isn't installed in this image on purpose -
# the orchestrator is not an Odoo process, it talks to Odoo over RPC (see
# odoo_client.py).
COPY softworker/orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY softworker/orchestrator/*.py ./
COPY softworker/addons/cbam/utils/calc_engine.py ./calc_engine.py
COPY shared/tool_schemas/ ./shared/tool_schemas/

# Run as a non-root user. Nothing here needs root: pip installed system-wide
# above (before switching user), the app only listens on 8000 (unprivileged),
# and it has no need to write outside /app.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
