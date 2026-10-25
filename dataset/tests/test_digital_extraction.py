"""
tests/test_digital_extraction.py - Automated tests for PyMuPDF digital extraction, coordinates, and provenance.
Uses temporary synthetic PDFs for edge cases to ensure zero mutation of source documents.
"""

import hashlib
from pathlib import Path
import pytest
import pymupdf

from src.extractors import (
    extract_page_digital,
    find_text_bbox,
    extract_document_to_contract,
    get_document_clean_stem,
    compute_pdf_sha256,
)
from src.schemas import ExtractionResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PDF = PROJECT_ROOT / "real_documents" / "KGEC_AICTE_Approval_2026-27.pdf"


def test_digital_extraction_blocks_and_coordinates():
    """Verify PyMuPDF extracts text blocks with valid bounding box coordinates and honest confidence."""
    assert SAMPLE_PDF.exists()

    doc = pymupdf.open(SAMPLE_PDF)
    first_page = doc[0]

    page_ext = extract_page_digital(first_page, page_number=1)
    doc.close()

    assert page_ext.page_number == 1
    assert page_ext.method == "digital"
    assert page_ext.words_count > 50
    assert "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION" in page_ext.text

    # Verify blocks
    assert len(page_ext.blocks) > 0
    for block in page_ext.blocks:
        assert len(block.bounding_box) == 4
        x0, y0, x1, y1 = block.bounding_box
        assert x0 <= x1
        assert y0 <= y1
        assert x0 >= 0 and y0 >= 0
        # Honest confidence: None for deterministic digital extraction
        assert block.confidence is None
        assert block.is_ocr is False
        assert block.page_number == 1


def test_find_text_bbox_coordinates():
    """Verify find_text_bbox locates exact word coordinates."""
    doc = pymupdf.open(SAMPLE_PDF)
    first_page = doc[0]

    bbox = find_text_bbox(first_page, "Application No:")
    doc.close()

    assert bbox is not None
    assert len(bbox) == 4
    x0, y0, x1, y1 = bbox
    assert x0 < x1
    assert y0 < y1
    assert x0 >= 0 and y0 >= 0


def test_source_file_immutability():
    """Verify extraction does not modify source PDF file on disk."""
    with open(SAMPLE_PDF, "rb") as f:
        sha_before = hashlib.sha256(f.read()).hexdigest()

    doc = pymupdf.open(SAMPLE_PDF)
    _ = [extract_page_digital(page, i + 1) for i, page in enumerate(doc)]
    doc.close()

    with open(SAMPLE_PDF, "rb") as f:
        sha_after = hashlib.sha256(f.read()).hexdigest()

    assert sha_before == sha_after, "Source file was mutated during extraction!"


def test_synthetic_multipage_and_page_range(tmp_path: Path):
    """Verify multi-page synthetic PDF extraction with optional page ranges."""
    synth_path = tmp_path / "synthetic_3pages.pdf"
    doc = pymupdf.open()
    for i in range(1, 4):
        p = doc.new_page()
        p.insert_text((50, 72), f"Header for Page {i} of synthetic testing document.")
        p.insert_text((50, 120), f"Body text containing sufficient words to qualify as a full digital page for index {i}.")
    doc.save(synth_path)
    doc.close()

    # Extract all pages
    contract_all = extract_document_to_contract(synth_path, document_id="SYNTH_3P")
    assert isinstance(contract_all, ExtractionResult)
    assert contract_all.processing_metadata.total_pages == 3
    assert contract_all.processing_metadata.processed_pages == 3
    assert contract_all.processing_metadata.extraction_path == "digital"
    assert contract_all.processing_metadata.digital_pages == [1, 2, 3]
    assert contract_all.sha256 == compute_pdf_sha256(synth_path)

    # Extract page range "2-3"
    contract_range = extract_document_to_contract(synth_path, page_range="2-3")
    assert contract_range.processing_metadata.processed_pages == 2
    assert contract_range.processing_metadata.digital_pages == [2, 3]


def test_synthetic_mixed_text_and_image_page(tmp_path: Path):
    """Verify a page with substantive text and an image remains classified as digital (not misrouted to OCR)."""
    synth_path = tmp_path / "synthetic_mixed.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    # Insert substantive text (>= 10 words, >= 50 chars)
    page.insert_text(
        (50, 72),
        "This is an official institutional document with digital text and an embedded raster logo graphic."
    )
    # Insert a minimal 1x1 pixmap image
    pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 10, 10), 1)
    page.insert_image(pymupdf.Rect(50, 150, 100, 200), pixmap=pix)
    doc.save(synth_path)
    doc.close()

    contract = extract_document_to_contract(synth_path)
    assert contract.processing_metadata.extraction_path == "digital"
    assert contract.processing_metadata.digital_pages == [1]
    assert contract.processing_metadata.ocr_pages == []


def test_empty_pdf_handling(tmp_path: Path):
    """Verify empty PDF (0 bytes or blank page) produces structured result without unhandled crash."""
    # 1. 0-byte empty file
    empty_path = tmp_path / "empty_0bytes.pdf"
    empty_path.write_bytes(b"")

    contract_zero = extract_document_to_contract(empty_path)
    assert contract_zero.processing_metadata.total_pages == 0
    assert contract_zero.processing_metadata.processed_pages == 0
    assert len(contract_zero.warnings) > 0

    # 2. 1-page blank PDF (0 words, 0 images)
    blank_path = tmp_path / "blank_page.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(blank_path)
    doc.close()

    contract_blank = extract_document_to_contract(blank_path)
    assert contract_blank.processing_metadata.total_pages == 1
    assert contract_blank.processing_metadata.processed_pages == 1
    assert contract_blank.processing_status == "SUCCESS"



def test_corrupted_file_handling(tmp_path: Path):
    """Verify corrupted non-PDF binary produces EXTRACTION_ERROR with explicit error message."""
    bad_path = tmp_path / "corrupted_stream.pdf"
    bad_path.write_bytes(b"%PDF-1.4 NON-DECODABLE TRUNCATED STREAM WITHOUT XREF")

    contract = extract_document_to_contract(bad_path)
    assert contract.processing_status == "EXTRACTION_ERROR"
    assert len(contract.errors) > 0
    assert "PyMuPDF" in contract.errors[0] or "error" in contract.errors[0].lower()


def test_double_extension_clean_stem(tmp_path: Path):
    """Verify double extension .pdf.pdf is cleanly parsed using pathlib helper."""
    double_ext_file = tmp_path / "NAAC-Certificate-N-Quality-Profile.pdf.pdf"
    stem = get_document_clean_stem(double_ext_file)
    assert stem == "NAAC-Certificate-N-Quality-Profile"
    assert not stem.endswith(".pdf")

