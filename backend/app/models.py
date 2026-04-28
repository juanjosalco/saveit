from datetime import date, datetime
from sqlalchemy import (
    String, Integer, Float, Date, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    issuer: Mapped[str] = mapped_column(String(32))           # 'amex' | 'chase' | 'santander'
    last4: Mapped[str] = mapped_column(String(8))
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_currency: Mapped[str] = mapped_column(String(8), default="USD")
    __table_args__ = (UniqueConstraint("issuer", "last4", name="uq_issuer_last4"),)
    statements: Mapped[list["Statement"]] = relationship(back_populates="account")


class Statement(Base):
    __tablename__ = "statements"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    account: Mapped[Account] = relationship(back_populates="statements")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="statement", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    color: Mapped[str] = mapped_column(String(16), default="#888888")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)


class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    pattern: Mapped[str] = mapped_column(String(255))           # case-insensitive substring or regex
    match_type: Mapped[str] = mapped_column(String(16), default="contains")  # contains|regex
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    priority: Mapped[int] = mapped_column(Integer, default=100)


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(ForeignKey("statements.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    txn_date: Mapped[date] = mapped_column(Date, index=True)
    post_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description_raw: Mapped[str] = mapped_column(Text)
    description_clean: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Float)               # positive=charge, negative=payment/credit
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    is_payment: Mapped[bool] = mapped_column(Boolean, default=False)
    is_refund: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_category_override: Mapped[bool] = mapped_column(Boolean, default=False)
    dedup_key: Mapped[str] = mapped_column(String(128), index=True)

    statement: Mapped[Statement] = relationship(back_populates="transactions")
    category: Mapped[Category | None] = relationship()


class Setting(Base):
    """Single-row config table (key/value). Used for Azure DI endpoint+key."""
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
