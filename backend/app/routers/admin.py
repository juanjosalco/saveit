from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..admin import wipe_data

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
def reset_all(db: Session = Depends(get_db), preserve_config: bool = True):
    """Wipe all transactional data + archived PDFs.

    Categories and Rules are preserved by default.
    """
    return wipe_data(db, preserve_config=preserve_config)
