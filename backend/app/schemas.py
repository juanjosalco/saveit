from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    color: str


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    issuer: str
    last4: str
    nickname: str | None = None


class StatementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_id: int
    period_start: date | None
    period_end: date | None
    uploaded_at: datetime
    source_filename: str


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_id: int
    statement_id: int
    txn_date: date
    description_raw: str
    description_clean: str
    amount: float
    currency: str
    category_id: int | None
    is_payment: bool
    is_refund: bool
    manual_category_override: bool


class TransactionUpdate(BaseModel):
    category_id: int | None = None


class RuleIn(BaseModel):
    pattern: str
    match_type: str = "contains"
    category_id: int
    priority: int = 100


class RuleOut(RuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UploadResult(BaseModel):
    statement_id: int
    account_id: int
    issuer: str
    last4: str
    period_start: date | None
    period_end: date | None
    transactions_added: int
    transactions_skipped: int
    duplicate: bool = False
