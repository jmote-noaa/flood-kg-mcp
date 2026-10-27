# syntax=docker/dockerfile:1
# Container image for remote (streamable-HTTP) deployment.
#
# Used by:
#   - IBM Code Engine (deploy/ibm/)
#   - cloud.gov (docker image path) and any other container host
#
# The server serves MCP over streamable-HTTP at :8080/mcp with a health check
# at :8080/health. app.py auto-selects HTTP because PORT is set below.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PORT=8080
ENV KG_DATA_PATH=/app/data/texas_flood2.ttl

WORKDIR /app

# Install uv. Package versions are pinned via uv.lock, so :latest is fine here.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv export --no-dev --frozen --no-emit-project --no-hashes -o requirements.lock && \
    uv pip install --system --no-cache -r requirements.lock && \
    uv pip install --system --no-cache --no-deps .

# Knowledge graph data loaded into pyoxigraph at startup.
COPY data ./data

EXPOSE 8080

# PORT=8080 (set above) makes app.py run HTTP on that port automatically.
CMD ["python", "-m", "flood_kg_mcp.app"]
