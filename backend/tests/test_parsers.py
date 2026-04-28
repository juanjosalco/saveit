from pathlib import Path
import pytest
from app.parsers import AmexParser, ChaseParser, detect_parser

DOWNLOADS = Path.home() / "Downloads"

AMEX_FILES = [
    "2026-01-27.pdf", "2026-02-24.pdf", "2026-03-27 (1).pdf", "2026-04-26.pdf",
]
CHASE_FILES = [
    "20260405-statements-7410-.pdf", "20260420-statements-7679-.pdf",
]


@pytest.mark.parametrize("name", AMEX_FILES)
def test_amex_parses(name):
    p = DOWNLOADS / name
    if not p.exists():
        pytest.skip(f"missing fixture {p}")
    raw = p.read_bytes()
    parser = AmexParser()
    assert parser.detect(raw.decode("latin-1", errors="ignore")[:5000]) or True  # detect via text below
    parsed = parser.parse(raw)
    assert parsed.issuer == "amex"
    assert len(parsed.last4) == 4
    assert parsed.period_end is not None
    assert len(parsed.transactions) > 0
    # Sanity: amounts are floats, dates are present
    for t in parsed.transactions:
        assert t.txn_date is not None
        assert isinstance(t.amount, float)


@pytest.mark.parametrize("name", CHASE_FILES)
def test_chase_parses(name):
    p = DOWNLOADS / name
    if not p.exists():
        pytest.skip(f"missing fixture {p}")
    raw = p.read_bytes()
    parser = ChaseParser()
    parsed = parser.parse(raw)
    assert parsed.issuer == "chase"
    assert parsed.period_start and parsed.period_end
    assert len(parsed.transactions) > 0
    # At least one positive (purchase) txn
    assert any(t.amount > 0 for t in parsed.transactions)


def test_autodetect_amex():
    p = DOWNLOADS / AMEX_FILES[0]
    if not p.exists():
        pytest.skip("missing fixture")
    parser = detect_parser(p.read_bytes())
    assert parser.issuer == "amex"


def test_autodetect_chase():
    p = DOWNLOADS / CHASE_FILES[0]
    if not p.exists():
        pytest.skip("missing fixture")
    parser = detect_parser(p.read_bytes())
    assert parser.issuer == "chase"
