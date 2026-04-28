from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Rule
from ..schemas import RuleIn, RuleOut
from ..categorize import recategorize_all

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(Rule).order_by(Rule.priority, Rule.id).all()


@router.post("", response_model=RuleOut)
def create_rule(body: RuleIn, db: Session = Depends(get_db)):
    r = Rule(**body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: int, body: RuleIn, db: Session = Depends(get_db)):
    r = db.get(Rule, rule_id)
    if not r:
        raise HTTPException(404, "Not found")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return r


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    r = db.get(Rule, rule_id)
    if not r:
        raise HTTPException(404, "Not found")
    db.delete(r); db.commit()
    return {"ok": True}


@router.post("/recategorize")
def recategorize(db: Session = Depends(get_db), include_overridden: bool = False):
    n = recategorize_all(db, only_unoverridden=not include_overridden)
    return {"updated": n}
