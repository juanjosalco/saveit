import re
from datetime import date, datetime
from .base import ParsedStatement, ParsedTxn, extract_text


def _to_date(s: str) -> date:
    return datetime.strptime(s, "%m/%d/%y").date()


class AmexParser:
    issuer = "amex"

    def detect(self, text: str) -> bool:
        return "American Express" in text or "americanexpress.com" in text.lower()

    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        text = extract_text(pdf_bytes)
        lines = [l.rstrip() for l in text.splitlines()]

        # Account last 4
        last4 = "0000"
        m = re.search(r"Account Ending\s+([\d\-]+)", text)
        if m:
            digits = re.sub(r"\D", "", m.group(1))
            last4 = digits[-4:] if len(digits) >= 4 else digits

        # Closing date (period_end). Period_start = closing date - ~30 days, fallback None
        period_end = None
        period_start = None
        m = re.search(r"Closing Date\s+(\d{2}/\d{2}/\d{2})", text)
        if m:
            period_end = _to_date(m.group(1))

        txns: list[ParsedTxn] = []
        # Two interleaved sections: Credits (negative) and New Charges (positive)
        # We handle them in a single sweep using state flags.
        state = None  # 'credits' or 'charges' or 'fees'
        for i, l in enumerate(lines):
            stripped = l.strip()
            if "Credits Amount" in stripped:
                state = "credits"
                continue
            if re.match(r"Total\s+New Charges", stripped):
                state = "charges"
                continue
            if "Fees ⧫" in stripped or "Total Fees for this Period" in stripped:
                state = "fees"
                continue
            if state in ("credits", "charges", "fees"):
                m = re.match(r"(\d{2}/\d{2}/\d{2})\s+(.+)", stripped)
                if not m:
                    continue
                txn_date = _to_date(m.group(1))
                desc = m.group(2).strip()
                # Skip phantom lines: travel-detail rows are just "MM/DD/YY" with another
                # date as the description, or any txn dated after the closing date.
                if re.fullmatch(r"\d{2}/\d{2}/\d{2}", desc):
                    continue
                if period_end and txn_date > period_end:
                    continue
                # Look ahead for amount line
                amount = None
                for j in range(i, min(i + 8, len(lines))):
                    am = re.match(
                        r"^\s*(-?)\$([\d,]+\.\d{2})\s*⧫?\s*$", lines[j]
                    )
                    if am:
                        sign = -1.0 if am.group(1) == "-" else 1.0
                        amount = sign * float(am.group(2).replace(",", ""))
                        break
                if amount is None:
                    continue
                if state == "credits":
                    # credits are stored as negative
                    if amount > 0:
                        amount = -amount
                    txns.append(ParsedTxn(
                        txn_date=txn_date, description=desc, amount=amount,
                        is_refund=True,
                    ))
                elif state == "charges":
                    txns.append(ParsedTxn(
                        txn_date=txn_date, description=desc, amount=abs(amount),
                    ))
                elif state == "fees":
                    txns.append(ParsedTxn(
                        txn_date=txn_date, description=desc, amount=abs(amount),
                    ))

        return ParsedStatement(
            issuer=self.issuer, last4=last4,
            period_start=period_start, period_end=period_end,
            transactions=txns,
        )
