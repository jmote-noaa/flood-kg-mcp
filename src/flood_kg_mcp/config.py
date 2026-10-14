"""Server configuration loaded from environment variables or a .env file.

Every field can be overridden by an environment variable of the same name
(upper- or lower-case). Copy `.env.example` to `.env` for local development.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MCP server settings. Override any field via environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Transport ─────────────────────────────────────────────────────────────
    # "stdio"           — local subprocess (Claude Desktop / Claude Code / Zed)
    # "streamable-http" — remote HTTP server (containers, cloud deploys)
    #
    # NOTE: app.py also auto-selects HTTP when a platform injects DATABRICKS_APP_PORT
    # or PORT, so you usually do NOT need to set this on a cloud host.
    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    # Path to the Turtle (.ttl) file loaded into pyoxigraph at startup.
    kg_data_path: str = "data/texas_flood2.ttl"
    # Path to the YAML schema / query-guidance file served as kg://schema.
    kg_schema_path: str = "data/schema_prototype2.yml"
    # Path to the YAML analyst prompt-guidelines file served as kg://query-guidelines
    # and returned by the flood_kg_analyst prompt.
    kg_guidelines_path: str = "data/prompt_guidelines2.yml"


settings = Settings()
