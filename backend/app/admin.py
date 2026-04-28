from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import delete
from .db import PDF_DIR
from .models import Transaction, Statement, Account


def wipe_data(db: Session, *, preserve_config: bool = True) -> dict:
    """Delete all transactional data and archived PDFs.

    When preserve_config is True (default), Categories and Rules are kept.
    Returns counts of deleted rows.
    """
    txn_n = db.execute(delete(Transaction)).rowcount or 0
    stmt_n = db.execute(delete(Statement)).rowcount or 0
    acct_n = db.execute(delete(Account)).rowcount or 0
    db.commit()

    pdf_n = 0
    if PDF_DIR.exists():
        for p in PDF_DIR.glob("*.pdf"):
            try:
                p.unlink()
                pdf_n += 1
            except OSError:
                pass

    return {
        "transactions_deleted": txn_n,
        "statements_deleted": stmt_n,
        "accounts_deleted": acct_n,
        "pdfs_deleted": pdf_n,
        "config_preserved": preserve_config,
    }
