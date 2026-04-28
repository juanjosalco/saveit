from datetime import date
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..db import get_db
from ..models import Transaction, Category

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _base_query(db, start, end, account_id, exclude_payments=True, currency=None):
    q = select(Transaction)
    if start:
        q = q.where(Transaction.txn_date >= start)
    if end:
        q = q.where(Transaction.txn_date <= end)
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if currency:
        q = q.where(Transaction.currency == currency)
    if exclude_payments:
        q = q.where(Transaction.is_payment == False)  # noqa: E712
    return db.scalars(q).all()


def _currency_breakdown(txns) -> list[dict]:
    """Per-currency totals. Never sums across currencies."""
    agg: dict[str, dict] = {}
    for t in txns:
        cur = t.currency or "USD"
        a = agg.setdefault(cur, {"currency": cur, "transaction_count": 0,
                                  "total_spend": 0.0, "total_refunds": 0.0})
        a["transaction_count"] += 1
        if t.amount > 0:
            a["total_spend"] += t.amount
        elif t.amount < 0:
            a["total_refunds"] += -t.amount
    out = []
    for a in agg.values():
        a["total_spend"] = round(a["total_spend"], 2)
        a["total_refunds"] = round(a["total_refunds"], 2)
        a["net_spend"] = round(a["total_spend"] - a["total_refunds"], 2)
        out.append(a)
    out.sort(key=lambda x: -x["total_spend"])
    return out


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    start: date | None = None,
    end: date | None = None,
    account_id: int | None = None,
    currency: str | None = None,
):
    txns = _base_query(db, start, end, account_id, currency=currency)
    breakdown = _currency_breakdown(txns)
    spend = sum(t.amount for t in txns if t.amount > 0)
    refunds = sum(-t.amount for t in txns if t.amount < 0)
    # Legacy top-level fields (single currency: meaningful; mixed: nominal sum — UI should
    # prefer `by_currency`).
    return {
        "transaction_count": len(txns),
        "total_spend": round(spend, 2),
        "total_refunds": round(refunds, 2),
        "net_spend": round(spend - refunds, 2),
        "by_currency": breakdown,
    }


@router.get("/by-category")
def by_category(
    db: Session = Depends(get_db),
    start: date | None = None,
    end: date | None = None,
    account_id: int | None = None,
    currency: str | None = None,
):
    txns = _base_query(db, start, end, account_id, currency=currency)
    cats = {c.id: c for c in db.query(Category).all()}
    agg: dict[int | None, list[float | int]] = defaultdict(lambda: [0.0, 0])
    for t in txns:
        if t.amount <= 0:
            continue
        agg[t.category_id][0] += t.amount
        agg[t.category_id][1] += 1
    out = []
    for cid, (amt, n) in agg.items():
        c = cats.get(cid) if cid else None
        out.append({
            "category_id": cid,
            "category_name": c.name if c else "Uncategorized",
            "color": c.color if c else "#9ca3af",
            "amount": round(amt, 2),
            "count": n,
        })
    out.sort(key=lambda x: -x["amount"])
    return out


@router.get("/over-time")
def over_time(
    db: Session = Depends(get_db),
    start: date | None = None,
    end: date | None = None,
    account_id: int | None = None,
    currency: str | None = None,
    granularity: str = Query("month", pattern="^(day|week|month)$"),
):
    txns = _base_query(db, start, end, account_id, currency=currency)
    buckets: dict[str, float] = defaultdict(float)
    for t in txns:
        if t.amount <= 0:
            continue
        d = t.txn_date
        if granularity == "month":
            key = f"{d.year:04d}-{d.month:02d}"
        elif granularity == "week":
            iso = d.isocalendar()
            key = f"{iso[0]:04d}-W{iso[1]:02d}"
        else:
            key = d.isoformat()
        buckets[key] += t.amount
    return [{"period": k, "amount": round(v, 2)} for k, v in sorted(buckets.items())]


@router.get("/top-merchants")
def top_merchants(
    db: Session = Depends(get_db),
    start: date | None = None,
    end: date | None = None,
    account_id: int | None = None,
    currency: str | None = None,
    limit: int = 10,
):
    txns = _base_query(db, start, end, account_id, currency=currency)
    agg: dict[str, list[float | int]] = defaultdict(lambda: [0.0, 0])
    for t in txns:
        if t.amount <= 0:
            continue
        # Use first 30 chars of clean desc as merchant key (rough but effective)
        key = (t.description_clean or t.description_raw)[:32].strip()
        agg[key][0] += t.amount
        agg[key][1] += 1
    out = [
        {"merchant": k, "amount": round(v[0], 2), "count": v[1]}
        for k, v in agg.items()
    ]
    out.sort(key=lambda x: -x["amount"])
    return out[:limit]
