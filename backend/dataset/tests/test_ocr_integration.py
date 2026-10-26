"""
tests/test_ocr_integration.py - Comprehensive automated test suite for Phase 5 OCR integration.
Tests cover:
1. Interface & protocol conformance for swappable OCR engines.
2. Synthetic tests for OCR success, empty OCR output, engine errors, honest confidence preservation, and page routing.
3. Partial results preservation under simulated OCR engine failure.
4. Verification that digital extraction continues working cleanly on native text pages without OCR overhead.
5. End-to-end extraction on actual real scanned PDF from scanned_documents/ without altering originals.
"""

from pathlib import Path
import pytest
import pymupdf

from src.extractors import (
    BaseOCREngine,
    EasyOCREngine,
    SyntheticOCREngine,
    OCRExtractionError,
    route_and_extract_document,
    extract_document_to_contract,
    ExtractedBlock,
)
from src.schemas.extraction_result import ExtractionResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DIGITAL_DOC = PROJECT_ROOT / "real_documents" / "KGEC_AICTE_Approval_2026-27.pdf"
SCANNED_DOC = PROJECT_ROOT / "scanned_documents" / "NAAC_Certificate.pdf"
HYBRID_DOC = PROJECT_ROOT / "scanned_documents" / "NAAC_Certficate_and_Grade_Sheet.pdf"


def test_ocr_engine_protocol_conformance():
    """Verify OCR engines implement the BaseOCREngine interface."""
    assert issubclass(EasyOCREngine, BaseOCREngine)
    assert issubclass(SyntheticOCREngine, BaseOCREngine)

    synth = SyntheticOCREngine()
    assert synth.backend_name == "synthetic_ocr"

    easy = EasyOCREngine()
    assert easy.backend_name == "easyocr"


def test_synthetic_ocr_success_and_hybrid_routing():
    """
    Verify hybrid routing dispatches only scanned pages to OCR,
    while digital pages remain processed deterministically with confidence=None.
    """
    synth = SyntheticOCREngine(
        simulated_blocks=[
            ExtractedBlock(
                text="NATIONAL ASSESSMENT AND ACCREDITATION COUNCIL",
                bounding_box=[50.0, 100.0, 500.0, 140.0],
                page_number=1,
                confidence=0.9450,
                is_ocr=True,
            )
        ]
    )

    content = route_and_extract_document(HYBRID_DOC, ocr_engine=synth)

    assert content.total_pages == 5
    assert content.processed_pages == 5
    assert content.extraction_path == "hybrid"
    assert content.ocr_page_numbers == [1]
    assert content.digital_page_numbers == [2, 3, 4, 5]

    # Page 1 (scanned) was processed by OCR
    page_1 = content.pages[0]
    assert page_1.page_number == 1
    assert page_1.method == "ocr"
    assert len(page_1.blocks) == 1
    assert page_1.blocks[0].is_ocr is True
    assert page_1.blocks[0].confidence == 0.9450
    assert "NATIONAL ASSESSMENT" in page_1.text

    # Page 2 (digital) was NOT processed by OCR
    page_2 = content.pages[1]
    assert page_2.page_number == 2
    assert page_2.method == "digital"
    assert len(page_2.blocks) > 0
    # Honest confidence invariant: digital extraction never invents confidence
    for b in page_2.blocks:
        assert b.confidence is None
        assert b.is_ocr is False

    # OCR was called exactly once for page 1
    assert synth.calls_count == 1


def test_synthetic_ocr_empty_output_handling():
    """Verify empty OCR recognition produces well-formed PageExtraction and contract."""
    synth = SyntheticOCREngine(empty_output=True)

    result = extract_document_to_contract(
        SCANNED_DOC,
        document_id="DOC_TEST_EMPTY_SCAN",
        ocr_engine=synth,
    )

    assert isinstance(result, ExtractionResult)
    assert result.processing_metadata.ocr_backend == "synthetic_ocr"
    assert result.processing_metadata.ocr_pages == [1]
    assert result.processing_status == "SUCCESS"


def test_synthetic_ocr_engine_error_partial_retention():
    """
    Verify that when an OCR engine raises an error on a scanned page:
    1. The exception does not crash the extraction pipeline.
    2. Partial results for digital pages are preserved intact.
    3. The error is surfaced as a warning in ExtractionResult.
    """
    synth = SyntheticOCREngine(simulate_error="Simulated OCR hardware timeout")

    result = extract_document_to_contract(
        HYBRID_DOC,
        document_id="DOC_TEST_PARTIAL_ERROR",
        ocr_engine=synth,
    )

    assert isinstance(result, ExtractionResult)
    assert result.processing_status == "SUCCESS_WITH_WARNINGS"
    assert any("Simulated OCR hardware timeout" in w for w in result.warnings)

    # 4 digital pages were still successfully extracted and retained
    assert result.processing_metadata.processed_pages == 5
    assert len(result.processing_metadata.digital_pages) == 4
    assert result.processing_metadata.digital_pages == [2, 3, 4, 5]


def test_digital_document_does_not_invoke_ocr():
    """Verify that a native digital document never calls the OCR engine."""
    synth = SyntheticOCREngine()

    content = route_and_extract_document(DIGITAL_DOC, ocr_engine=synth)

    assert content.extraction_path == "digital"
    assert len(content.ocr_page_numbers) == 0
    assert len(content.digital_page_numbers) == 5
    # Zero calls to OCR engine
    assert synth.calls_count == 0


def test_ocr_caching_prevents_duplicate_processing():
    """Verify EasyOCREngine caching prevents redundant inference on identical page renderings."""
    easy = EasyOCREngine(gpu=False, cache_enabled=True)

    doc = pymupdf.open(SCANNED_DOC)
    page = doc[0]

    # First call - populates cache
    ext_1 = easy.extract_page_ocr(page, page_number=1)
    assert len(easy._cache) == 1

    # Second call - returns from cache
    ext_2 = easy.extract_page_ocr(page, page_number=1)
    assert ext_1.text == ext_2.text
    assert len(easy._cache) == 1

    doc.close()


def test_real_scanned_pdf_ocr_execution():
    """
    End-to-end integration test on an actual scanned PDF from scanned_documents/
    without altering the original file:
    - Scanned doc: scanned_documents/NAAC_Certificate.pdf
    - Confirms non-empty text on Page 1.
    - Confirms genuine confidence scores are recorded.
    - Confirms valid typographic point bounding box coordinates.
    - Confirms full conformance to Pydantic ExtractionResult contract.
    """
    easy = EasyOCREngine(gpu=False)

    contract_result = extract_document_to_contract(
        SCANNED_DOC,
        document_id="DOC_SCAN_006",
        document_type="naac_certificate",
        ocr_engine=easy,
    )

    assert isinstance(contract_result, ExtractionResult)
    assert contract_result.document_id == "DOC_SCAN_006"
    assert contract_result.processing_status == "SUCCESS"
    assert contract_result.processing_metadata.ocr_backend == "easyocr"
    assert contract_result.processing_metadata.ocr_pages == [1]
    assert contract_result.processing_metadata.extraction_path == "ocr"

    # Confirm non-empty recognized text on actual scanned document
    doc = pymupdf.open(SCANNED_DOC)
    page_1 = doc[0]
    page_w = float(page_1.rect.width)
    page_h = float(page_1.rect.height)
    page_ext = easy.extract_page_ocr(page_1, page_number=1)
    doc.close()

    assert len(page_ext.text.strip()) > 0, "OCR produced empty text on scanned document page 1"
    assert len(page_ext.blocks) > 0, "OCR produced 0 text blocks"
    assert "NAAC" in page_ext.text or "NATIONAL" in page_ext.text or "GRADE" in page_ext.text

    # Validate bounding box geometry and honest confidence preservation
    for block in page_ext.blocks:
        assert block.is_ocr is True
        assert block.confidence is not None
        assert 0.0 <= block.confidence <= 1.0, f"Invalid confidence {block.confidence}"

        x0, y0, x1, y1 = block.bounding_box
        assert 0.0 <= x0 <= page_w, f"x0 out of bounds: {x0}"
        assert 0.0 <= y0 <= page_h, f"y0 out of bounds: {y0}"
        assert x0 <= x1 <= page_w, f"x1 out of bounds: {x1}"
        assert y0 <= y1 <= page_h, f"y1 out of bounds: {y1}"
