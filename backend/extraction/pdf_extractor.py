"""
backend/extraction/pdf_extractor.py - Digital PDF extraction interface for SIH26261 (Person 1).
Exposes PyMuPDF-based text and bounding box extraction.
"""

import sys
from pathlib import Path

# Ensure paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "dataset"
for p in [str(REPO_ROOT), str(DATASET_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.extractors.digital_pdf import (
        extract_page_digital,
        compute_pdf_sha256,
        get_document_clean_stem,
    )
    from src.extractors.hybrid_router import (
        route_and_extract_document,
        extract_document_to_contract,
        evaluate_page_routing,
        parse_page_range,
    )
    from src.extractors.base import (
        DocumentContent,
        ExtractedBlock,
        PageExtraction,
    )
except ImportError:
    from dataset.src.extractors.digital_pdf import (
        extract_page_digital,
        compute_pdf_sha256,
        get_document_clean_stem,
    )
    from dataset.src.extractors.hybrid_router import (
        route_and_extract_document,
        extract_document_to_contract,
        evaluate_page_routing,
        parse_page_range,
    )
    from dataset.src.extractors.base import (
        DocumentContent,
        ExtractedBlock,
        PageExtraction,
    )

__all__ = [
    "extract_page_digital",
    "compute_pdf_sha256",
    "get_document_clean_stem",
    "route_and_extract_document",
    "extract_document_to_contract",
    "evaluate_page_routing",
    "parse_page_range",
    "DocumentContent",
    "ExtractedBlock",
    "PageExtraction",
]
