"""Unit tests for the Santander parser using a mock Azure DI AnalyzeResult.

We don't call Azure here — we synthesize the shape of `AnalyzeResult` that
prebuilt-layout returns: pages with lines, and tables with cells indexed by
(row_index, column_index).
"""
from dataclasses import dataclass, field
from app.parsers.santander import (
    SantanderParser, _parse_es_date, _parse_amount_mxn,
)


@dataclass
class _Cell:
    row_index: int
    column_index: int
    content: str


@dataclass
class _Table:
    cells: list[_Cell]


@dataclass
class _Line:
    content: str


@dataclass
class _Page:
    lines: list[_Line]


@dataclass
class _Result:
    pages: list[_Page]
    tables: list[_Table]
    content: str = ""


def _build_result(rows: list[tuple[str, str, str, str]],
                  *, header=("FECHA", "CONCEPTO", "CARGO", "ABONO"),
                  meta_lines: list[str] | None = None) -> _Result:
    cells = [
        _Cell(0, c, h) for c, h in enumerate(header)
    ]
    for ri, row in enumerate(rows, start=1):
        for ci, val in enumerate(row):
            cells.append(_Cell(ri, ci, val))
    table = _Table(cells=cells)
    lines = [_Line(content=l) for l in (meta_lines or [])]
    return _Result(pages=[_Page(lines=lines)], tables=[table])


def test_parse_es_date_variants():
    assert _parse_es_date("12/ABR/26").isoformat() == "2026-04-12"
    assert _parse_es_date("05-MAY-2026").isoformat() == "2026-05-05"
    assert _parse_es_date("12/04/26").isoformat() == "2026-04-12"
    assert _parse_es_date("31/02/26") is None  # invalid


def test_parse_amount_mxn():
    assert _parse_amount_mxn("$1,234.56") == 1234.56
    assert _parse_amount_mxn("250.00 CR") == -250.0
    assert _parse_amount_mxn("-99.99") == -99.99
    assert _parse_amount_mxn("") is None


def test_santander_basic_table():
    rows = [
        ("12/ABR/26", "OXXO ROMA NORTE",          "350.00", ""),
        ("13/ABR/26", "PEMEX 1234",               "800.00", ""),
        ("14/ABR/26", "PAGO RECIBIDO TARJETA",    "",       "1500.00"),
        ("15/ABR/26", "BONIFICACION INTERESES",   "",       "12.50"),
    ]
    result = _build_result(
        rows,
        meta_lines=[
            "BANCO SANTANDER MEXICO ESTADO DE CUENTA",
            "Tarjeta de Crédito terminación 4321",
            "Período: 13/MAR/26 al 12/ABR/26",
            "Fecha de corte 12/ABR/26",
        ],
    )
    parser = SantanderParser(di_result=result)
    parsed = parser.parse(b"")
    assert parsed.issuer == "santander"
    assert parsed.last4 == "4321"
    assert parsed.period_end is not None and parsed.period_end.isoformat() == "2026-04-12"
    assert parsed.period_start is not None and parsed.period_start.isoformat() == "2026-03-13"
    assert len(parsed.transactions) == 4
    t1, t2, t3, t4 = parsed.transactions
    assert (t1.amount, t1.is_refund, t1.is_payment, t1.currency) == (350.0, False, False, "MXN")
    assert (t2.amount, t2.currency) == (800.0, "MXN")
    # Payment recibido → marked is_payment, not refund
    assert t3.amount == -1500.0
    assert t3.is_payment is True and t3.is_refund is False
    # Bonificación = refund/credit
    assert t4.amount == -12.5
    assert t4.is_refund is True and t4.is_payment is False


def test_santander_importe_column_only():
    rows = [
        ("01/MAY/26", "WALMART", "299.00"),
        ("02/MAY/26", "REEMBOLSO", "-50.00"),
    ]
    result = _build_result(
        rows,
        header=("FECHA", "DESCRIPCION", "IMPORTE"),
        meta_lines=["SANTANDER ESTADO DE CUENTA"],
    )
    parser = SantanderParser(di_result=result)
    parsed = parser.parse(b"")
    assert len(parsed.transactions) == 2
    assert parsed.transactions[0].amount == 299.0
    assert parsed.transactions[1].amount == -50.0
    assert parsed.transactions[1].is_refund is True
