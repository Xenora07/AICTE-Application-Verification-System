"""
src/extractors/base.py - Core data structures and abstract protocols for extraction.
"""

from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


class ExtractedBlock(BaseModel):
    """A discrete block of text with coordinates and provenance."""
    text: str
    bounding_box: List[float] = Field(description="[x0, y0, x1, y1] on page")
    page_number: int
    confidence: Optional[float] = Field(default=None, description="Preserved OCR confidence or None for digital")
    is_ocr: bool = False


class PageExtraction(BaseModel):
    """Raw extraction result for a single page."""
    page_number: int
    method: Literal["digital", "ocr", "empty"]
    text: str
    blocks: List[ExtractedBlock] = Field(default_factory=list)
    images_count: int = 0
    words_count: int = 0
    characters_count: int = 0


class DocumentContent(BaseModel):
    """Consolidated raw extraction result across all processed pages of a document."""
    total_pages: int
    processed_pages: int
    page_range: Optional[str] = None
    extraction_path: Literal["digital", "ocr", "hybrid"]
    pages: List[PageExtraction] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Concatenate text from all pages in order."""
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def digital_page_numbers(self) -> List[int]:
        return [p.page_number for p in self.pages if p.method == "digital"]

    @property
    def ocr_page_numbers(self) -> List[int]:
        return [p.page_number for p in self.pages if p.method == "ocr"]


class BaseOCREngine:
    """Abstract base protocol for pluggable/swappable OCR backends."""

    @property
    def backend_name(self) -> str:
        """Name of the OCR engine (e.g. 'easyocr', 'synthetic')."""
        raise NotImplementedError

    def extract_page_ocr(self, page: Any, page_number: int) -> PageExtraction:
        """
        Extract text blocks, bounding boxes, and honest confidences from a page.
        Never invents confidence scores.
        """
        raise NotImplementedError

