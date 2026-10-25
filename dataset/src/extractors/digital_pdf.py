"""
src/extractors/digital_pdf.py - High-performance digital PDF text and coordinate extractor using PyMuPDF.
Strictly avoids deprecated imports, preserving page geometry and block coordinates.
Upholds honest confidence invariants (confidence is None for deterministic digital extraction).
"""

import hashlib
from pathlib import Path
from typing import List, Optional
import pymupdf

from src.extractors.base import ExtractedBlock, PageExtraction


def get_document_clean_stem(file_path: Path) -> str:
    """
    Safely extract clean document stem without trailing extensions.
    Correctly handles single (.pdf) and double (.pdf.pdf) extensions.
    """
    name = file_path.name
    while name.lower().endswith(".pdf"):
        name = name[:-4]
    return name


def compute_pdf_sha256(file_path: Path) -> str:
    """Compute full 64-character lowercase SHA-256 checksum."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def extract_page_digital(page: pymupdf.Page, page_number: int) -> PageExtraction:
    """
    Extract selectable digital text and bounding boxes from a single PDF page using PyMuPDF.
    Preserves text block coordinates [x0, y0, x1, y1] in PDF typographic points (top-left origin).
    Confidence is explicitly None because digital extraction is deterministic.
    """
    blocks_raw = page.get_text("blocks")
    extracted_blocks: List[ExtractedBlock] = []
    text_parts: List[str] = []

    for item in blocks_raw:
        # block tuple format: (x0, y0, x1, y1, "text", block_no, block_type)
        # block_type == 0 indicates text; 1 indicates image block
        if len(item) >= 7:
            x0, y0, x1, y1, text, block_no, b_type = item[:7]
            if b_type == 0 and text.strip():
                clean_text = text.strip()
                text_parts.append(clean_text)
                extracted_blocks.append(
                    ExtractedBlock(
                        text=clean_text,
                        bounding_box=[
                            max(0.0, round(float(x0), 2)),
                            max(0.0, round(float(y0), 2)),
                            max(0.0, round(float(x1), 2)),
                            max(0.0, round(float(y1), 2)),
                        ],
                        page_number=page_number,
                        confidence=None,
                        is_ocr=False,
                    )
                )

    full_page_text = "\n".join(text_parts)
    words = [w for w in full_page_text.split() if any(c.isalnum() for c in w)]
    img_count = len(page.get_images())

    return PageExtraction(
        page_number=page_number,
        method="digital",
        text=full_page_text,
        blocks=extracted_blocks,
        images_count=img_count,
        words_count=len(words),
        characters_count=len(full_page_text),
    )


def find_text_bbox(page: pymupdf.Page, query: str) -> Optional[List[float]]:
    """
    Locate precise bounding box coordinates for a specific query string on a digital page.
    Returns [x0, y0, x1, y1] in top-left origin convention or None if not found.
    """
    rects = page.search_for(query)
    if rects:
        r = rects[0]
        return [
            max(0.0, round(float(r.x0), 2)),
            max(0.0, round(float(r.y0), 2)),
            max(0.0, round(float(r.x1), 2)),
            max(0.0, round(float(r.y1), 2)),
        ]
    return None

