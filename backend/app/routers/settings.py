from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..services.settings import (
    AZURE_ENDPOINT_KEY, AZURE_KEY_KEY, azure_di_config, set_setting,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class AzureSettingsIn(BaseModel):
    endpoint: str = ""
    key: str = ""


def _mask(s: str) -> str:
    if not s:
        return ""
    if len(s) <= 8:
        return "•" * len(s)
    return s[:4] + "•" * (len(s) - 8) + s[-4:]


@router.get("/azure")
def get_azure(db: Session = Depends(get_db)):
    endpoint, key = azure_di_config(db)
    return {
        "endpoint": endpoint,
        "key_masked": _mask(key),
        "configured": bool(endpoint and key),
    }


@router.put("/azure")
def put_azure(payload: AzureSettingsIn, db: Session = Depends(get_db)):
    set_setting(db, AZURE_ENDPOINT_KEY, payload.endpoint.strip())
    if payload.key and payload.key.strip() and "•" not in payload.key:
        set_setting(db, AZURE_KEY_KEY, payload.key.strip())
    endpoint, key = azure_di_config(db)
    return {"endpoint": endpoint, "key_masked": _mask(key), "configured": bool(endpoint and key)}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    endpoint, key = azure_di_config(db)
    return {
        "azure_di": {
            "configured": bool(endpoint and key),
            "endpoint_set": bool(endpoint),
            "key_set": bool(key),
        }
    }
