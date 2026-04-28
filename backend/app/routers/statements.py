import hashlib
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from ..db import get_db, PDF_DIR
from ..models import Account, Statement, Transaction
from ..parsers import detect_parser
from ..categorize import categorize_one, clean_description
from ..schemas import UploadResult

router = APIRouter(prefix="/statements", tags=["statements"])


def _statement_to_dict(db: Session, s: Statement) -> dict:
    agg = db.query(
        func.count(Transaction.id),
        func.coalesce(func.sum(
            case((Transaction.amount > 0, Transaction.amount), else_=0)
        ), 0.0),
    ).filter(Transaction.statement_id == s.id).first()
    txn_count, total_amount = (agg or (0, 0.0))
    return {
        "id": s.id,
        "account_id": s.account_id,
        "account": {
            "id": s.account.id,
            "issuer": s.account.issuer,
            "last4": s.account.last4,
            "base_currency": s.account.base_currency,
        },
        "period_start": s.period_start,
        "period_end": s.period_end,
        "uploaded_at": s.uploaded_at,
        "source_filename": s.source_filename,
        "has_pdf": bool(s.pdf_path) and Path(s.pdf_path).exists(),
        "transaction_count": int(txn_count or 0),
        "total_amount": round(float(total_amount or 0.0), 2),
    }


@router.post("/upload", response_model=UploadResult)
async def upload_statement(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty file")
    sha = hashlib.sha256(raw).hexdigest()

    existing = db.scalar(select(Statement).where(Statement.sha256 == sha))
    if existing:
        if not (existing.pdf_path and Path(existing.pdf_path).exists()):
            pdf_path = PDF_DIR / f"{sha}.pdf"
            pdf_path.write_bytes(raw)
            existing.pdf_path = str(pdf_path)
            db.commit()
        return UploadResult(
            statement_id=existing.id, account_id=existing.account_id,
            issuer=existing.account.issuer, last4=existing.account.last4,
            period_start=existing.period_start, period_end=existing.period_end,
            transactions_added=0, transactions_skipped=len(existing.transactions),
            duplicate=True,
        )

    try:
        parser = detect_parser(raw, db=db)
        parsed = parser.parse(raw)
    except Exception as e:
        raise HTTPException(400, f"Parse failed: {e}")

    account = db.scalar(
        select(Account).where(Account.issuer == parsed.issuer, Account.last4 == parsed.last4)
    )
    if not account:
        # Currency for the account: derive from the first txn (Santander → MXN), default USD
        currency = next(
            (t.currency for t in parsed.transactions if t.currency),
            "MXN" if parsed.issuer == "santander" else "USD",
        )
        account = Account(issuer=parsed.issuer, last4=parsed.last4, base_currency=currency)
        db.add(account); db.flush()

    statement = Statement(
        account_id=account.id, period_start=parsed.period_start,
        period_end=parsed.period_end, source_filename=file.filename or "statement.pdf",
        sha256=sha,
    )
    db.add(statement); db.flush()

    added = 0
    skipped = 0
    for t in parsed.transactions:
        clean = clean_description(t.description)
        dedup = f"{account.id}:{t.txn_date.isoformat()}:{t.amount:.2f}:{clean[:48]}"
        dup = db.scalar(
            select(Transaction).where(
                Transaction.account_id == account.id,
                Transaction.dedup_key == dedup,
            )
        )
        if dup:
            skipped += 1
            continue
        cat_id = categorize_one(db, clean, t.is_payment, t.is_refund)
        db.add(Transaction(
            statement_id=statement.id, account_id=account.id,
            txn_date=t.txn_date, description_raw=t.description,
            description_clean=clean, amount=t.amount, currency=t.currency,
            category_id=cat_id, is_payment=t.is_payment, is_refund=t.is_refund,
            dedup_key=dedup,
        ))
        added += 1

    pdf_path = PDF_DIR / f"{sha}.pdf"
    try:
        pdf_path.write_bytes(raw)
    except OSError as e:
        db.rollback()
        raise HTTPException(500, f"Failed to archive PDF: {e}")
    statement.pdf_path = str(pdf_path)
    db.commit()

    return UploadResult(
        statement_id=statement.id, account_id=account.id,
        issuer=parsed.issuer, last4=parsed.last4,
        period_start=parsed.period_start, period_end=parsed.period_end,
        transactions_added=added, transactions_skipped=skipped,
    )


@router.get("")
def list_statements(db: Session = Depends(get_db)):
    rows = (
        db.query(Statement)
        .join(Account)
        .order_by(Statement.uploaded_at.desc())
        .all()
    )
    return [_statement_to_dict(db, s) for s in rows]


@router.get("/{statement_id}/file")
def download_statement(statement_id: int, db: Session = Depends(get_db)):
    s = db.get(Statement, statement_id)
    if not s:
        raise HTTPException(404, "Not found")
    if not s.pdf_path or not Path(s.pdf_path).exists():
        raise HTTPException(410, "PDF no longer available on disk")
    return FileResponse(
        s.pdf_path,
        media_type="application/pdf",
        filename=s.source_filename or f"statement_{s.id}.pdf",
    )


@router.delete("/{statement_id}")
def delete_statement(statement_id: int, db: Session = Depends(get_db)):
    s = db.get(Statement, statement_id)
    if not s:
        raise HTTPException(404, "Not found")
    pdf_path = s.pdf_path
    db.delete(s); db.commit()
    if pdf_path:
        try: Path(pdf_path).unlink(missing_ok=True)
        except OSError: pass
    return {"ok": True}
