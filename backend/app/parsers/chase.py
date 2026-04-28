import re
from datetime import date, datetime
from .base import ParsedStatement, ParsedTxn, extract_text


class ChaseParser:
    issuer = "chase"

    def detect(self, text: str) -> bool:
        # Chase credit card statements consistently include this footer/header pattern
        return ("CHASE" in text.upper() and "Payment Due Date" in text
                and ("PURCHASE" in text.upper() or "Account Number" in text))

    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        text = extract_text(pdf_bytes)
        lines = [l.rstrip() for l in text.splitlines()]

        # Find account ending - Chase formats as "Account Number: XXXX XXXX XXXX 7410" or similar
        last4 = "0000"
        m = re.search(r"Account Number[:\s]+[\d\s\*xX]+?(\d{4})\b", text)
        if m:
            last4 = m.group(1)

        # Period: "Opening/Closing Date 03/06/26 - 04/05/26"
        period_start = period_end = None
        m = re.search(
            r"Opening/Closing Date\s+(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}/\d{2}/\d{2})",
            text,
        )
        if m:
            period_start = datetime.strptime(m.group(1), "%m/%d/%y").date()
            period_end = datetime.strptime(m.group(2), "%m/%d/%y").date()

        # Default year = period_end year (Chase txn rows show MM/DD only)
        year = period_end.year if period_end else date.today().year

        txns: list[ParsedTxn] = []
        in_section = False
        # Match lines like:
        # "04/01     Payment Thank You - Web -250.00"
        # "03/08     COSTCO WHSE #0008 KIRKLAND WA 282.25"
        row_re = re.compile(
            r"^(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*$"
        )
        for l in lines:
            stripped = l.strip()
            upper = stripped.upper()
            if "PURCHASE" in upper and ("MERCHANT" in upper or "TRANSACTION" in upper or upper.startswith("PURCHASES")):
                in_section = True
                continue
            if "PAYMENTS AND OTHER CREDITS" in upper or upper.startswith("PAYMENTS, CREDITS"):
                in_section = True
                continue
            if "TOTALS YEAR-TO-DATE" in upper or "INTEREST CHARGED" in upper or "FEES CHARGED" in upper:
                in_section = False
                continue
            if not in_section:
                # Chase often lists txns without an explicit header; allow rows that match strictly
                pass
            m = row_re.match(stripped)
            if not m:
                continue
            md = m.group(1)
            desc = m.group(2).strip()
            amt = float(m.group(3).replace(",", ""))
            try:
                # Handle Dec/Jan boundary: if month > period_end month and period crosses years
                month = int(md.split("/")[0])
                yr = year
                if period_start and period_end and period_start.year != period_end.year:
                    if month >= period_start.month:
                        yr = period_start.year
                txn_date = datetime.strptime(f"{md}/{yr % 100:02d}", "%m/%d/%y").date()
            except ValueError:
                continue
            is_payment = amt < 0 and ("PAYMENT" in desc.upper() or "AUTOPAY" in desc.upper())
            is_refund = amt < 0 and not is_payment
            txns.append(ParsedTxn(
                txn_date=txn_date, description=desc, amount=amt,
                is_payment=is_payment, is_refund=is_refund,
            ))

        return ParsedStatement(
            issuer=self.issuer, last4=last4,
            period_start=period_start, period_end=period_end,
            transactions=txns,
        )
