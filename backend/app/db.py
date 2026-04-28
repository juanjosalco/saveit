import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

# Filesystem locations (kept for backwards compat & local PDF storage fallback)
DB_DIR = Path(os.environ.get("FINAPP_DB_DIR", Path.home() / ".finapp"))
DB_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR = settings.pdf_dir
PDF_DIR.mkdir(parents=True, exist_ok=True)
RESET_MARKER = DB_DIR / ".wiped_v1_6"

DATABASE_URL = settings.database_url

_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_column(conn, table: str, column: str, ddl: str) -> None:
    """Lightweight ad-hoc migration. SQLite-only; on Postgres we use Alembic."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    cols = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db():
    """Initialize the DB.

    On SQLite (local dev) we still use create_all + ad-hoc column migrations
    so the local UX has zero friction. On Postgres we expect Alembic to have
    run migrations already (via the container entrypoint).
    """
    from . import models  # noqa: F401  ensure models registered

    if DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            _ensure_column(conn, "statements", "pdf_path", "pdf_path VARCHAR(512)")
            _ensure_column(
                conn, "accounts", "base_currency",
                "base_currency VARCHAR(8) NOT NULL DEFAULT 'USD'",
            )

    from .seed import seed_defaults
    with SessionLocal() as s:
        seed_defaults(s)

    # One-time wipe: SQLite-only legacy hook for Phase 1.6. No-op on Postgres.
    if DATABASE_URL.startswith("sqlite") and not RESET_MARKER.exists():
        from .admin import wipe_data
        with SessionLocal() as s:
            wipe_data(s, preserve_config=True)
        RESET_MARKER.write_text("1")
