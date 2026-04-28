import re
from sqlalchemy.orm import Session
from .models import Rule, Transaction, Category


_PUNCT_RE = re.compile(r"\s+")


def clean_description(raw: str) -> str:
    """Light normalization for display + matching."""
    s = raw.upper()
    s = re.sub(r"APLPAY\s+", "", s)
    s = re.sub(r"AAPLPAY\s+", "", s)
    s = re.sub(r"\b\d{6,}\b", "", s)         # drop long merchant ID numbers
    s = re.sub(r"\b\d{3}-\d{3}-\d{4}\b", "", s)  # phone numbers
    s = _PUNCT_RE.sub(" ", s).strip()
    return s


def _matches(rule: Rule, desc_upper: str) -> bool:
    if rule.match_type == "regex":
        try:
            return bool(re.search(rule.pattern, desc_upper, re.IGNORECASE))
        except re.error:
            return False
    return rule.pattern.upper() in desc_upper


def categorize_one(db: Session, description: str, is_payment: bool, is_refund: bool) -> int | None:
    if is_payment:
        cat = db.query(Category).filter_by(name="Payment").first()
        return cat.id if cat else None
    if is_refund:
        cat = db.query(Category).filter_by(name="Refund").first()
        return cat.id if cat else None
    desc_u = description.upper()
    rules = db.query(Rule).order_by(Rule.priority.asc(), Rule.id.asc()).all()
    for r in rules:
        if _matches(r, desc_u):
            return r.category_id
    other = db.query(Category).filter_by(name="Other").first()
    return other.id if other else None


def recategorize_all(db: Session, *, only_unoverridden: bool = True) -> int:
    q = db.query(Transaction)
    if only_unoverridden:
        q = q.filter(Transaction.manual_category_override == False)  # noqa: E712
    count = 0
    for t in q.all():
        new_cat = categorize_one(db, t.description_clean or t.description_raw, t.is_payment, t.is_refund)
        if new_cat != t.category_id:
            t.category_id = new_cat
            count += 1
    db.commit()
    return count
