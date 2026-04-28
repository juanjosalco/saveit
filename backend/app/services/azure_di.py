"""Thin wrapper around Azure Document Intelligence's prebuilt-layout model."""
from __future__ import annotations
from typing import Any


class AzureDIUnavailable(RuntimeError):
    pass


def analyze_layout(pdf_bytes: bytes, endpoint: str, key: str) -> Any:
    if not endpoint or not key:
        raise AzureDIUnavailable(
            "Azure Document Intelligence is not configured. "
            "Set the endpoint and key on the Settings page."
        )
    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        from azure.core.credentials import AzureKeyCredential
    except ImportError as e:  # pragma: no cover
        raise AzureDIUnavailable(
            "The `azure-ai-documentintelligence` package is not installed. "
            "Install with: pip install -e '.[azure]'"
        ) from e

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    poller = client.begin_analyze_document(
        "prebuilt-layout",
        AnalyzeDocumentRequest(bytes_source=pdf_bytes),
    )
    return poller.result()
