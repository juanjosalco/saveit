"""Centralized configuration via Pydantic BaseSettings.

Reads from environment variables (and `.env` if present in CWD).
"""
from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_DATA_DIR = Path(os.environ.get("FINAPP_DB_DIR", str(Path.home() / ".finapp")))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "dev"  # "dev" | "prod"

    # Database. Defaults to local SQLite for backwards compatibility.
    database_url: str = f"sqlite:///{_DEFAULT_DATA_DIR / 'finapp.db'}"

    # PDF storage. If azure_storage_account is set, use Blob; otherwise local FS.
    pdf_dir: Path = _DEFAULT_DATA_DIR / "pdfs"
    azure_storage_account: str = ""
    azure_storage_container: str = "pdfs"

    # Azure Document Intelligence (Santander OCR)
    azure_di_endpoint: str = ""
    azure_di_key: str = ""

    # Auth (Phase 7+) — empty in dev means auth is disabled
    entra_tenant_id: str = ""
    entra_api_client_id: str = ""
    entra_api_audience: str = ""  # api://<client-id>
    admin_emails: str = ""        # comma-separated allowlist

    # Anti-abuse limits (Phase 10)
    limit_statements_per_day: int = 50
    limit_ocr_pages_per_day: int = 100
    limit_ai_messages_per_day: int = 50
    limit_max_pdf_mb: int = 10

    # CORS — defaults are dev-only; override in prod via env
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Misc
    serve_frontend: bool = False  # Set true in prod to serve frontend/dist as static

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


settings = Settings()
