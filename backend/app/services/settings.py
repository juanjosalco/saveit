"""Helpers for reading config from the `settings` table, with env-var override."""
from __future__ import annotations
import os
from sqlalchemy.orm import Session
from ..models import Setting

AZURE_ENDPOINT_KEY = "azure_di_endpoint"
AZURE_KEY_KEY = "azure_di_key"


def get_setting(db: Session, key: str, default: str = "") -> str:
    """Env vars win over DB. Env names: FINAPP_<KEY_UPPER>."""
    env_name = f"FINAPP_{key.upper()}"
    if os.environ.get(env_name):
        return os.environ[env_name]
    row = db.get(Setting, key)
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value
    db.commit()


def azure_di_config(db: Session) -> tuple[str, str]:
    return (
        get_setting(db, AZURE_ENDPOINT_KEY).strip(),
        get_setting(db, AZURE_KEY_KEY).strip(),
    )
