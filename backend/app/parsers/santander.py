"""Santander Mexico (image-based) credit-card statement parser via Azure DI.

Santander statements are scanned/image PDFs, so pypdf returns no usable text.
We call Azure Document Intelligence's prebuilt-layout model and walk the
returned tables looking for one with Spanish columns like
`Fecha | Concepto/Descripcion | Cargo | Abono` (variants supported).
"""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import Any
from .base import ParsedStatement, ParsedTxn

# 4-digit account ending in any common Spanish phrasing
_LAST4_RE = re.compile(r"(?:terminaci[oó]n|cuenta|tarjeta)[^\d]{0,20}(\d{4})", re.I)
# Spanish dates: 12/ABR/26, 12-ABR-2026, 12 abr 26, 12/04/2026, etc.
_MONTHS_ES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace("á", "a").replace("é", "e").replace(
        "í", "i").replace("ó", "o").replace("ú", "u")


def _parse_es_date(s: str, fallback_year: int | None = None) -> date | None:
    s = (s or "").strip().upper().replace(".", "")
    # 12/ABR/26  or  12-ABR-2026  or  12 ABR 26
    m = re.match(r"^(\d{1,2})[\s/\-]+([A-Z]{3,9})[\s/\-]+(\d{2,4})$", s)
    if m:
        day = int(m.group(1))
        mon_raw = m.group(2)[:3]
        mon = _MONTHS_ES.get(mon_raw)
        if not mon:
            return None
        yr = int(m.group(3))
        if yr < 100:
            yr += 2000
        try:
            return date(yr, mon, day)
        except ValueError:
            return None
    # 12/04/26 or 12-04-2026 or 12.04.26
    m = re.match(r"^(\d{1,2})[\s/\-.](\d{1,2})[\s/\-.](\d{2,4})$", s)
    if m:
        day, mon, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if yr < 100:
            yr += 2000
        try:
            return date(yr, mon, day)
        except ValueError:
            return None
    # 12 ABR (no year) — use fallback
    m = re.match(r"^(\d{1,2})[\s/\-]+([A-Z]{3,9})$", s)
    if m and fallback_year:
        mon = _MONTHS_ES.get(m.group(2)[:3])
        if mon:
            try:
                return date(fallback_year, mon, int(m.group(1)))
            except ValueError:
                return None
    return None


def _parse_amount_mxn(s: str) -> float | None:
    """Spanish-locale amount. Strips $, MXN, NPE, spaces. Comma is thousands separator
    in MX (1,234.56). Negative may be `-` prefix or trailing CR."""
    if s is None:
        return None
    raw = s.strip()
    if not raw:
        return None
    is_neg = False
    upper = raw.upper()
    if upper.endswith("CR") or upper.endswith("ABONO") or upper.startswith("-"):
        is_neg = True
    cleaned = re.sub(r"[^\d,.\-]", "", raw)
    cleaned = cleaned.replace(",", "")
    try:
        v = float(cleaned)
    except ValueError:
        return None
    if is_neg and v > 0:
        v = -v
    return v


def _detect_table(result: Any) -> tuple[Any, dict[str, int]] | None:
    """Find the transaction table by header columns. Returns (table, col_index_map)."""
    target_keys = {"fecha", "concepto", "descripcion", "cargo", "abono", "importe", "monto"}
    for table in getattr(result, "tables", []) or []:
        # Build header row (first row's cells)
        header = {}
        for cell in table.cells:
            if getattr(cell, "row_index", None) == 0:
                header[cell.column_index] = _norm(cell.content or "")
        if not header:
            continue
        norm_vals = set(header.values())
        # need at least: a date col + a description col + an amount col
        has_date = any("fecha" in v for v in norm_vals)
        has_desc = any(("concepto" in v) or ("descripcion" in v) or ("descripción" in v) for v in norm_vals)
        has_amt = any(
            ("cargo" in v) or ("abono" in v) or ("importe" in v) or ("monto" in v)
            for v in norm_vals
        )
        if not (has_date and has_desc and has_amt):
            continue
        col = {}
        for idx, name in header.items():
            if "fecha" in name and "fecha" not in col:
                # prefer "fecha de operacion" if multiple
                col["fecha"] = idx
            if ("concepto" in name) or ("descripcion" in name) or ("descripción" in name):
                col["desc"] = idx
            if "cargo" in name:
                col["cargo"] = idx
            if "abono" in name:
                col["abono"] = idx
            if "importe" in name or "monto" in name:
                col["importe"] = idx
        if "fecha" in col and "desc" in col and (
            "cargo" in col or "abono" in col or "importe" in col
        ):
            return table, col
    return None


def _extract_text_from_result(result: Any) -> str:
    """Concatenate all line content from the AnalyzeResult."""
    parts: list[str] = []
    for page in getattr(result, "pages", []) or []:
        for line in getattr(page, "lines", []) or []:
            parts.append(line.content or "")
    if not parts and getattr(result, "content", None):
        return result.content
    return "\n".join(parts)


class SantanderParser:
    issuer = "santander"

    def __init__(self, di_result: Any | None = None):
        # Allows a parsed AnalyzeResult to be injected (avoids re-calling Azure
        # when the upload pipeline already invoked analyze_layout for detection).
        self._result = di_result

    @staticmethod
    def detect_text(text: str) -> bool:
        u = text.upper() if text else ""
        return ("SANTANDER" in u) and (
            "ESTADO DE CUENTA" in u
            or "TARJETA DE CR" in u  # "Tarjeta de Crédito"
            or "FECHA DE CORTE" in u
        )

    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        if self._result is None:
            raise RuntimeError(
                "SantanderParser must be constructed with a pre-fetched Azure DI result. "
                "Use parsers.detect_parser() in the upload pipeline."
            )
        result = self._result
        text = _extract_text_from_result(result)

        # last4
        last4 = "0000"
        m = _LAST4_RE.search(text)
        if m:
            last4 = m.group(1)

        # period_end via "Fecha de corte 12/ABR/26" or "Periodo: 13/MAR/26 al 12/ABR/26"
        period_start = period_end = None
        m = re.search(
            r"(?:Per[ií]odo|Periodo)[:\s]+(\d{1,2}[\s/\-][A-Za-z]{3,9}[\s/\-]\d{2,4})\s*(?:al|-|–|hasta)\s*(\d{1,2}[\s/\-][A-Za-z]{3,9}[\s/\-]\d{2,4})",
            text,
            re.IGNORECASE,
        )
        if m:
            period_start = _parse_es_date(m.group(1))
            period_end = _parse_es_date(m.group(2))
        else:
            m = re.search(r"Fecha\s+de\s+corte[:\s]+(\d{1,2}[\s/\-][A-Za-z]{3,9}[\s/\-]\d{2,4})",
                          text, re.IGNORECASE)
            if m:
                period_end = _parse_es_date(m.group(1))
        fallback_year = period_end.year if period_end else date.today().year

        # Locate transaction table
        found = _detect_table(result)
        txns: list[ParsedTxn] = []
        if found:
            table, col = found
            # Group cells by row_index
            rows: dict[int, dict[int, str]] = {}
            for cell in table.cells:
                if cell.row_index == 0:
                    continue
                rows.setdefault(cell.row_index, {})[cell.column_index] = (cell.content or "").strip()
            for ri in sorted(rows):
                row = rows[ri]
                date_s = row.get(col["fecha"], "")
                desc = row.get(col["desc"], "")
                txn_date = _parse_es_date(date_s, fallback_year=fallback_year)
                if txn_date is None or not desc:
                    continue
                amount: float | None = None
                is_refund = False
                if "cargo" in col and "abono" in col:
                    cargo = _parse_amount_mxn(row.get(col["cargo"], ""))
                    abono = _parse_amount_mxn(row.get(col["abono"], ""))
                    if cargo and cargo != 0:
                        amount = abs(cargo)
                    elif abono and abono != 0:
                        amount = -abs(abono)
                        is_refund = True
                elif "importe" in col:
                    v = _parse_amount_mxn(row.get(col["importe"], ""))
                    if v is not None:
                        amount = v
                        if v < 0:
                            is_refund = True
                if amount is None or amount == 0:
                    continue
                desc_clean = re.sub(r"\s+", " ", desc).strip()
                is_payment = is_refund and (
                    "PAGO" in desc_clean.upper()
                    and ("TARJETA" in desc_clean.upper() or "RECIBIDO" in desc_clean.upper())
                )
                if is_payment:
                    is_refund = False
                txns.append(ParsedTxn(
                    txn_date=txn_date, description=desc_clean, amount=amount,
                    currency="MXN", is_payment=is_payment, is_refund=is_refund,
                ))

        return ParsedStatement(
            issuer=self.issuer, last4=last4,
            period_start=period_start, period_end=period_end,
            transactions=txns,
        )
