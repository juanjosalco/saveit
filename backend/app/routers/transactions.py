from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..db import get_db
from ..models import Transaction, Account, Category
from ..schemas import TransactionOut, TransactionUpdate, AccountOut, CategoryOut

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    account_id: int | None = None,
    category_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    include_payments: bool = True,
    limit: int = Query(500, le=5000),
):
    q = select(Transaction)
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if category_id:
        q = q.where(Transaction.category_id == category_id)
    if start:
        q = q.where(Transaction.txn_date >= start)
    if end:
        q = q.where(Transaction.txn_date <= end)
    if not include_payments:
        q = q.where(Transaction.is_payment == False)  # noqa: E712
    q = q.order_by(Transaction.txn_date.desc()).limit(limit)
    return db.scalars(q).all()


@router.patch("/transactions/{txn_id}", response_model=TransactionOut)
def update_transaction(txn_id: int, body: TransactionUpdate, db: Session = Depends(get_db)):
    t = db.get(Transaction, txn_id)
    if not t:
        raise HTTPException(404, "Not found")
    if body.category_id is not None:
        t.category_id = body.category_id
        t.manual_category_override = True
    db.commit()
    db.refresh(t)
    return t


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()
