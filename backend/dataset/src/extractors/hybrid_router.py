"""
src/extractors/hybrid_router.py - Intelligent page-by-page routing and extraction orchestrator.
Determines whether each page is native digital or raster scanned, routing accordingly.
Supports optional page ranges, partial error retention, and bridges to the Phase 3 ExtractionResult contract.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Union
import pymupdf

from src.extractors.base import DocumentContent, PageExtraction, BaseOCREngine
from src.extractors.digital_pdf import (
    extract_page_digital,
    compute_pdf_sha256,
    get_document_clean_stem,
)
from src.schemas.common import FieldEvidence, TableData
from src.schemas.extraction_result import ExtractionResult, ProcessingMetadata
from src.mappers.base_mapper import BaseMapper


def parse_page_range(range_str: Optional[str], total_pages: int) -> Tuple[int, int]:
    """
    Parse a 1-indexed page range string like '1-5', '3-10', or '2'.
    If range_str is None or empty, returns (1, total_pages).
    If total_pages == 0, returns (1, 0).
    """
    if total_pages == 0:
        return 1, 0

    if not range_str or not range_str.strip():
        return 1, total_pages

    parts = range_str.strip().split("-")
    if len(parts) == 1:
        start = int(parts[0])
        clamped = max(1, min(start, total_pages))
        return clamped, clamped
    elif len(parts) == 2:
        start = int(parts[0])
        end = int(parts[1])
        return max(1, min(start, total_pages)), max(1, min(end, total_pages))
    else:
        raise ValueError(f"Invalid page range format: '{range_str}'. Expected 'start-end' or 'page'.")


def evaluate_page_routing(page: pymupdf.Page) -> Tuple[str, int, int, int]:
    """
    Explainable multi-factor evaluation of a single PDF page:
    Returns (route_method, char_count, word_count, image_count).
    Route methods: 'digital', 'ocr', 'empty'.

    Routing Rules:
    1. Digital: Page has substantive selectable alphanumeric words and character density
       (word_count >= 10 and chars >= 50).
       IMPORTANT: Pages with images (e.g. institution logos, signatures, letterheads)
       are STILL routed to digital extraction if they contain sufficient text.
    2. OCR: Page contains raster images and lacks sufficient selectable text
       (img_count > 0 and word_count < 10).
    3. Sparse Digital: Contains text with no raster images (chars > 0 and img_count == 0).
    4. Empty: Contains neither text nor raster images.
    """
    text = page.get_text()
    chars = len(text.strip())
    words = [w for w in text.split() if any(c.isalnum() for c in w)]
    word_count = len(words)
    img_count = len(page.get_images())

    # 1. Digital: Substantive text takes precedence over the presence of images
    if word_count >= 10 and chars >= 50:
        return "digital", chars, word_count, img_count

    # 2. OCR: Has raster images and lacks sufficient digital text
    if img_count > 0:
        return "ocr", chars, word_count, img_count

    # 3. Text exists but sparse, no raster images
    if chars > 0 and img_count == 0:
        return "digital", chars, word_count, img_count

    # 4. Pure blank page
    return "empty", chars, word_count, img_count


def route_and_extract_document(
    doc_path: Path,
    page_range: Optional[str] = None,
    ocr_handler: Optional[Callable[[pymupdf.Page, int], PageExtraction]] = None,
    ocr_engine: Optional[BaseOCREngine] = None,
) -> DocumentContent:
    """
    Open PDF, inspect every page within page_range, route to digital extractor or OCR handler,
    and return unified DocumentContent.
    Retains partial results if individual pages experience extraction errors.
    """
    if not doc_path.exists():
        raise FileNotFoundError(f"Document not found at: {doc_path}")

    doc = pymupdf.open(doc_path)
    total_pages = len(doc)

    if total_pages == 0:
        doc.close()
        return DocumentContent(
            total_pages=0,
            processed_pages=0,
            page_range=page_range or "0",
            extraction_path="digital",
            pages=[],
        )

    start_p, end_p = parse_page_range(page_range, total_pages)

    extracted_pages: List[PageExtraction] = []
    digital_count = 0
    ocr_count = 0

    effective_ocr: Optional[Callable[[pymupdf.Page, int], PageExtraction]] = None
    if ocr_engine is not None:
        effective_ocr = ocr_engine.extract_page_ocr
    elif ocr_handler is not None:
        effective_ocr = ocr_handler

    for p_idx in range(start_p - 1, end_p):
        page_num = p_idx + 1
        page = doc[p_idx]
        try:
            method, chars, words, imgs = evaluate_page_routing(page)

            if method == "digital":
                p_ext = extract_page_digital(page, page_num)
                extracted_pages.append(p_ext)
                digital_count += 1
            elif method == "ocr":
                if effective_ocr is not None:
                    try:
                        p_ext = effective_ocr(page, page_num)
                    except Exception as ocr_exc:
                        p_ext = PageExtraction(
                            page_number=page_num,
                            method="ocr",
                            text=f"[OCR ERROR ON PAGE {page_num}: {ocr_exc}]",
                            blocks=[],
                            images_count=imgs,
                            words_count=0,
                            characters_count=0,
                        )
                else:
                    p_ext = PageExtraction(
                        page_number=page_num,
                        method="ocr",
                        text="",
                        blocks=[],
                        images_count=imgs,
                        words_count=0,
                        characters_count=0,
                    )
                extracted_pages.append(p_ext)
                ocr_count += 1
            else:
                extracted_pages.append(
                    PageExtraction(
                        page_number=page_num,
                        method="empty",
                        text="",
                        blocks=[],
                        images_count=imgs,
                        words_count=0,
                        characters_count=0,
                    )
                )
        except Exception as page_exc:
            # Retain partial results on single-page failure
            extracted_pages.append(
                PageExtraction(
                    page_number=page_num,
                    method="empty",
                    text=f"[EXTRACTION ERROR ON PAGE {page_num}: {page_exc}]",
                    blocks=[],
                    images_count=0,
                    words_count=0,
                    characters_count=0,
                )
            )

    doc.close()

    if ocr_count == 0 and digital_count > 0:
        overall_path = "digital"
    elif digital_count == 0 and ocr_count > 0:
        overall_path = "ocr"
    elif digital_count > 0 and ocr_count > 0:
        overall_path = "hybrid"
    else:
        overall_path = "digital"

    return DocumentContent(
        total_pages=total_pages,
        processed_pages=len(extracted_pages),
        page_range=page_range if page_range else f"1-{total_pages}",
        extraction_path=overall_path,
        pages=extracted_pages,
    )


def extract_document_to_contract(
    doc_path: Path,
    document_id: Optional[str] = None,
    document_type: str = "unknown",
    page_range: Optional[str] = None,
    ocr_handler: Optional[Callable[[pymupdf.Page, int], PageExtraction]] = None,
    ocr_engine: Optional[BaseOCREngine] = None,
    mapper: Optional[BaseMapper] = None,
) -> ExtractionResult:
    """
    Extract PDF document into canonical Phase 3 ExtractionResult payload.
    Emits full provenance (SHA-256, document_id, relative_path) and processing metadata.
    Handles unreadable/corrupted files and 0-page empty PDFs gracefully.
    """
    clean_stem = get_document_clean_stem(doc_path)
    doc_id = document_id or f"DOC_{clean_stem}"
    source_file_str = str(doc_path).replace("\\", "/")

    # Check file existence
    if not doc_path.exists():
        return ExtractionResult(
            document_id=doc_id,
            source_file=source_file_str,
            sha256=None,
            document_type=document_type,
            classification_confidence=None,
            processing_status="EXTRACTION_ERROR",
            processing_metadata=ProcessingMetadata(
                total_pages=0,
                processed_pages=0,
                page_range=page_range,
                extraction_path="digital",
            ),
            warnings=[],
            errors=[f"File does not exist: {doc_path}"],
        )

    # Compute full SHA-256 checksum
    try:
        sha256_hash = compute_pdf_sha256(doc_path)
    except Exception as exc:
        return ExtractionResult(
            document_id=doc_id,
            source_file=source_file_str,
            sha256=None,
            document_type=document_type,
            classification_confidence=None,
            processing_status="EXTRACTION_ERROR",
            processing_metadata=ProcessingMetadata(
                total_pages=0,
                processed_pages=0,
                page_range=page_range,
                extraction_path="digital",
            ),
            warnings=[],
            errors=[f"Failed to read file for checksum computation: {exc}"],
        )

    # Handle 0-byte empty file
    if doc_path.stat().st_size == 0:
        return ExtractionResult(
            document_id=doc_id,
            source_file=source_file_str,
            sha256=sha256_hash,
            document_type=document_type,
            classification_confidence=None,
            processing_status="SUCCESS_WITH_WARNINGS",
            processing_metadata=ProcessingMetadata(
                total_pages=0,
                processed_pages=0,
                page_range="0",
                extraction_path="digital",
            ),
            warnings=["Document is empty (0 bytes, 0 pages)."],
            errors=[],
        )

    # Attempt to open and inspect via PyMuPDF
    try:
        doc = pymupdf.open(doc_path)
        total_pages = len(doc)
    except Exception as open_exc:
        return ExtractionResult(
            document_id=doc_id,
            source_file=source_file_str,
            sha256=sha256_hash,
            document_type=document_type,
            classification_confidence=None,
            processing_status="EXTRACTION_ERROR",
            processing_metadata=ProcessingMetadata(
                total_pages=0,
                processed_pages=0,
                page_range=page_range,
                extraction_path="digital",
            ),
            warnings=[],
            errors=[f"PyMuPDF unreadable PDF stream error: {open_exc}"],
        )

    # Handle 0-page empty document
    if total_pages == 0:
        doc.close()
        return ExtractionResult(
            document_id=doc_id,
            source_file=source_file_str,
            sha256=sha256_hash,
            document_type=document_type,
            classification_confidence=None,
            processing_status="SUCCESS_WITH_WARNINGS",
            processing_metadata=ProcessingMetadata(
                total_pages=0,
                processed_pages=0,
                page_range="0",
                extraction_path="digital",
            ),
            warnings=["Document contains 0 pages."],
            errors=[],
        )

    doc.close()

    # Route and extract pages
    try:
        content = route_and_extract_document(
            doc_path=doc_path,
            page_range=page_range,
            ocr_handler=ocr_handler,
            ocr_engine=ocr_engine,
        )
    except Exception as route_exc:
        return ExtractionResult(
            document_id=doc_id,
            source_file=source_file_str,
            sha256=sha256_hash,
            document_type=document_type,
            classification_confidence=None,
            processing_status="EXTRACTION_ERROR",
            processing_metadata=ProcessingMetadata(
                total_pages=total_pages,
                processed_pages=0,
                page_range=page_range,
                extraction_path="digital",
            ),
            warnings=[],
            errors=[f"Routing and extraction failure: {route_exc}"],
        )

    warnings: List[str] = []
    if content.extraction_path in ("ocr", "hybrid") and ocr_handler is None and ocr_engine is None:
        warnings.append(
            f"{len(content.ocr_page_numbers)} pages routed to OCR pending Phase 5 OCR backend execution."
        )

    # Check for individual page errors (retaining partial results)
    page_errors = [
        p for p in content.pages
        if p.text.startswith("[EXTRACTION ERROR") or p.text.startswith("[OCR ERROR")
    ]
    for pe in page_errors:
        warnings.append(f"Partial extraction warning on Page {pe.page_number}: {pe.text}")

    status = "SUCCESS_WITH_WARNINGS" if warnings else "SUCCESS"
    ocr_backend_name = ocr_engine.backend_name if ocr_engine is not None else None

    # Apply deterministic field mapping if mapper is provided
    fields: Dict[str, FieldEvidence] = {}
    table_data: List[TableData] = []
    if mapper is not None:
        fields = mapper.map_fields(content)
        table_data = mapper.extract_tables(content)
        if any(f.is_uncertain for f in fields.values()):
            if status == "SUCCESS":
                status = "SUCCESS_WITH_UNCERTAINTY"

    return ExtractionResult(
        document_id=doc_id,
        source_file=source_file_str,
        sha256=sha256_hash,
        document_type=document_type,
        classification_confidence=None,
        processing_status=status,
        processing_metadata=ProcessingMetadata(
            total_pages=content.total_pages,
            processed_pages=content.processed_pages,
            page_range=content.page_range,
            extraction_path=content.extraction_path,
            digital_pages=content.digital_page_numbers,
            ocr_pages=content.ocr_page_numbers,
            ocr_backend=ocr_backend_name,
        ),
        fields=fields,
        table_data=table_data,
        warnings=warnings,
        errors=[],
    )

