from .base import Parser, ParsedStatement, ParsedTxn, extract_text  # noqa
from .amex import AmexParser  # noqa
from .chase import ChaseParser  # noqa
from .santander import SantanderParser  # noqa


def detect_parser(pdf_bytes: bytes, *, db=None) -> "Parser":
    """Detect the right parser. Text-based first (Amex/Chase). If text is too
    short to detect anything, fall back to Azure Document Intelligence and try
    to detect Santander on the OCR'd text. Requires a DB session for Santander
    (to read Azure DI credentials)."""
    text = extract_text(pdf_bytes)
    for cls in (AmexParser, ChaseParser):
        p = cls()
        if p.detect(text):
            return p
    # Image-based PDFs (Santander Mexico): pypdf returns very little text.
    # Or: text-based but the issuer string is in the image layer.
    if db is not None:
        from ..services.settings import azure_di_config
        from ..services.azure_di import analyze_layout, AzureDIUnavailable
        endpoint, key = azure_di_config(db)
        if endpoint and key:
            try:
                result = analyze_layout(pdf_bytes, endpoint, key)
            except AzureDIUnavailable as e:
                raise ValueError(str(e))
            ocr_text = "\n".join(
                (l.content or "") for page in (getattr(result, "pages", []) or [])
                for l in (getattr(page, "lines", []) or [])
            )
            if SantanderParser.detect_text(ocr_text) or SantanderParser.detect_text(text):
                return SantanderParser(di_result=result)
            raise ValueError(
                "Could not detect statement issuer (Amex, Chase, or Santander). "
                "Azure DI ran but no known issuer was found."
            )
        # No Azure DI — give a helpful hint if it looks like an image PDF
        if len(text.strip()) < 100:
            raise ValueError(
                "This looks like an image-based PDF (Santander Mexico). "
                "Configure Azure Document Intelligence on the Settings page to enable OCR."
            )
    raise ValueError("Could not detect statement issuer (Amex or Chase supported)")
