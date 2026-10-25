"""
src/extractors package - Document extraction and routing modules.
"""

from src.extractors.base import BaseOCREngine, DocumentContent, ExtractedBlock, PageExtraction
from src.extractors.digital_pdf import (
    extract_page_digital,
    find_text_bbox,
    compute_pdf_sha256,
    get_document_clean_stem,
)
from src.extractors.hybrid_router import (
    evaluate_page_routing,
    route_and_extract_document,
    extract_document_to_contract,
    parse_page_range,
)
from src.extractors.ocr_engine import (
    EasyOCREngine,
    SyntheticOCREngine,
    OCRExtractionError,
)

__all__ = [
    "BaseOCREngine",
    "DocumentContent",
    "ExtractedBlock",
    "PageExtraction",
    "extract_page_digital",
    "find_text_bbox",
    "compute_pdf_sha256",
    "get_document_clean_stem",
    "evaluate_page_routing",
    "route_and_extract_document",
    "extract_document_to_contract",
    "parse_page_range",
    "EasyOCREngine",
    "SyntheticOCREngine",
    "OCRExtractionError",
]

