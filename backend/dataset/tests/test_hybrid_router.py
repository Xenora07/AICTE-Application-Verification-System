"""
tests/test_hybrid_router.py - Automated tests for page-by-page routing and hybrid document handling.
"""

from pathlib import Path
import pytest

from src.extractors import route_and_extract_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DIGITAL_DOC = PROJECT_ROOT / "real_documents" / "KGEC_AICTE_Approval_2026-27.pdf"
SCANNED_DOC = PROJECT_ROOT / "scanned_documents" / "IT_accr.pdf"
HYBRID_DOC_1 = PROJECT_ROOT / "scanned_documents" / "NAAC_Certficate_and_Grade_Sheet.pdf"
HYBRID_DOC_2 = PROJECT_ROOT / "scanned_documents" / "NBA-UG-PG-Approval-Letter-2021-22-to-2022-2024-2022-2027.pdf"


def test_routing_digital_document():
    """Verify clean digital document is routed 100% to digital extraction."""
    content = route_and_extract_document(DIGITAL_DOC)

    assert content.total_pages == 5
    assert content.processed_pages == 5
    assert content.extraction_path == "digital"
    assert len(content.digital_page_numbers) == 5
    assert len(content.ocr_page_numbers) == 0


def test_routing_scanned_document():
    """Verify pure scanned document is routed 100% to OCR path."""
    content = route_and_extract_document(SCANNED_DOC)

    assert content.total_pages == 2
    assert content.processed_pages == 2
    assert content.extraction_path == "ocr"
    assert len(content.digital_page_numbers) == 0
    assert len(content.ocr_page_numbers) == 2


def test_routing_hybrid_document_naac():
    """Verify NAAC mixed document routes Page 1 to OCR and Pages 2-5 to Digital."""
    content = route_and_extract_document(HYBRID_DOC_1)

    assert content.total_pages == 5
    assert content.processed_pages == 5
    assert content.extraction_path == "hybrid"
    assert content.ocr_page_numbers == [1]
    assert content.digital_page_numbers == [2, 3, 4, 5]


def test_routing_hybrid_document_nba():
    """Verify NBA mixed document routes Page 3 to Digital and Pages 1, 2, 4, 5 to OCR."""
    content = route_and_extract_document(HYBRID_DOC_2)

    assert content.total_pages == 5
    assert content.processed_pages == 5
    assert content.extraction_path == "hybrid"
    assert content.ocr_page_numbers == [1, 2, 4, 5]
    assert content.digital_page_numbers == [3]


def test_page_range_filtering():
    """Verify page_range parameter restricts processing to specified pages."""
    content = route_and_extract_document(DIGITAL_DOC, page_range="2-3")

    assert content.total_pages == 5
    assert content.processed_pages == 2
    assert [p.page_number for p in content.pages] == [2, 3]
