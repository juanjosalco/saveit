from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable
import io
import pypdf


@dataclass
class ParsedTxn:
    txn_date: date
    description: str
    amount: float                 # positive = charge, negative = payment/credit
    currency: str = "USD"
    is_payment: bool = False
    is_refund: bool = False


@dataclass
class ParsedStatement:
    issuer: str
    last4: str
    period_start: date | None
    period_end: date | None
    transactions: list[ParsedTxn] = field(default_factory=list)


@runtime_checkable
class Parser(Protocol):
    issuer: str
    def detect(self, text: str) -> bool: ...
    def parse(self, pdf_bytes: bytes) -> ParsedStatement: ...


def extract_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def detect_parser(pdf_bytes: bytes) -> "Parser":
    from .amex import AmexParser
    from .chase import ChaseParser
    text = extract_text(pdf_bytes)
    for cls in (AmexParser, ChaseParser):
        p = cls()
        if p.detect(text):
            return p
    raise ValueError("Could not detect statement issuer (Amex or Chase supported)")
