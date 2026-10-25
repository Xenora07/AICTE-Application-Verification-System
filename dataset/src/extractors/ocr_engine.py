"""
src/extractors/ocr_engine.py - Pluggable OCR backend implementation for raster and scanned documents.
Provides EasyOCREngine adhering to BaseOCREngine interface with genuine confidence tracking,
PDF typographic point coordinate mapping, page-level caching, and robust partial failure handling.
Also provides SyntheticOCREngine for deterministic, fast testing of OCR failure and routing branches.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
import pymupdf

from src.extractors.base import BaseOCREngine, ExtractedBlock, PageExtraction
from src.extractors.image_preprocessor import preprocess_image_for_ocr

logger = logging.getLogger(__name__)


class OCRExtractionError(RuntimeError):
    """Raised when an OCR engine encounters an unrecoverable page extraction failure."""
    pass


class EasyOCREngine(BaseOCREngine):
    """
    Production-grade EasyOCR backend running on PyTorch CPU/GPU.
    - Preserves genuine engine confidence values (never invents confidence).
    - Maps bounding boxes from rendered pixel space back to PDF typographic point coordinates [x0, y0, x1, y1].
    - In-memory SHA-256 image sample caching prevents redundant processing of identical pages.
    """

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        dpi: int = 150,
        apply_preprocessing: bool = False,
        cache_enabled: bool = True,
    ):
        self.languages = languages or ["en"]
        self.gpu = gpu
        self.dpi = dpi
        self.apply_preprocessing = apply_preprocessing
        self.cache_enabled = cache_enabled
        self._reader: Optional[Any] = None
        self._cache: Dict[str, PageExtraction] = {}

    @property
    def backend_name(self) -> str:
        return "easyocr"

    def _get_reader(self) -> Any:
        """Lazily initialize EasyOCR Reader so non-OCR workloads incur zero startup penalty."""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
            except Exception as exc:
                raise OCRExtractionError(f"Failed to initialize EasyOCR engine: {exc}") from exc
        return self._reader

    def clear_cache(self) -> None:
        """Clear cached page extractions."""
        self._cache.clear()

    def extract_page_ocr(self, page: pymupdf.Page, page_number: int) -> PageExtraction:
        """
        Extract text blocks, bounding boxes, and honest confidences from a raster/scanned PDF page.
        """
        try:
            # 1. Render page to high-fidelity pixmap
            pix = page.get_pixmap(dpi=self.dpi, alpha=False)
            img_bytes = pix.samples

            # 2. Check cache by image hash if caching is enabled
            if self.cache_enabled:
                cache_key = hashlib.sha256(img_bytes).hexdigest()
                if cache_key in self._cache:
                    cached_entry = self._cache[cache_key]
                    return cached_entry.model_copy(update={"page_number": page_number})

            # 3. Convert pixmap to numpy array
            img_np = np.frombuffer(img_bytes, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
            if pix.n == 4:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
            elif pix.n == 1:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)

            # 4. Optional OpenCV contrast enhancement / deskewing
            if self.apply_preprocessing:
                img_np, _ = preprocess_image_for_ocr(img_np)

            # 5. Execute OCR inference
            reader = self._get_reader()
            raw_detections = reader.readtext(img_np)

            # 6. Transform coordinates from rendered pixmap back to PDF point space
            page_w_pts = float(page.rect.width)
            page_h_pts = float(page.rect.height)
            pix_w = float(pix.width)
            pix_h = float(pix.height)

            scale_x = pix_w / page_w_pts if page_w_pts > 0 else 1.0
            scale_y = pix_h / page_h_pts if page_h_pts > 0 else 1.0

            blocks: List[ExtractedBlock] = []
            text_lines: List[str] = []

            for item in raw_detections:
                polygon, text, conf = item
                clean_text = str(text).strip()
                if not clean_text:
                    continue

                text_lines.append(clean_text)

                # Polygon points to bounding box [x0, y0, x1, y1]
                xs = [pt[0] for pt in polygon]
                ys = [pt[1] for pt in polygon]

                min_x = max(0.0, float(min(xs)) / scale_x)
                min_y = max(0.0, float(min(ys)) / scale_y)
                max_x = min(page_w_pts, float(max(xs)) / scale_x)
                max_y = min(page_h_pts, float(max(ys)) / scale_y)

                bbox = [
                    round(min_x, 2),
                    round(min_y, 2),
                    round(max_x, 2),
                    round(max_y, 2),
                ]

                # Preserve genuine confidence from engine, never invent values
                honest_confidence = round(float(conf), 4)

                blocks.append(
                    ExtractedBlock(
                        text=clean_text,
                        bounding_box=bbox,
                        page_number=page_number,
                        confidence=honest_confidence,
                        is_ocr=True,
                    )
                )

            full_page_text = "\n".join(text_lines)
            words = [w for w in full_page_text.split() if any(c.isalnum() for c in w)]
            img_count = len(page.get_images())

            extraction = PageExtraction(
                page_number=page_number,
                method="ocr",
                text=full_page_text,
                blocks=blocks,
                images_count=img_count,
                words_count=len(words),
                characters_count=len(full_page_text),
            )

            # Store in cache
            if self.cache_enabled:
                self._cache[cache_key] = extraction

            return extraction

        except Exception as exc:
            logger.error(f"Error during EasyOCR page {page_number} extraction: {exc}", exc_info=True)
            raise OCRExtractionError(f"EasyOCR page {page_number} failed: {exc}") from exc


class SyntheticOCREngine(BaseOCREngine):
    """
    Lightweight deterministic OCR engine for unit and integration testing.
    Allows simulating OCR success, empty recognition, engine errors, and custom confidence values.
    """

    def __init__(
        self,
        backend_name: str = "synthetic_ocr",
        simulated_blocks: Optional[List[ExtractedBlock]] = None,
        simulate_error: Optional[str] = None,
        empty_output: bool = False,
    ):
        self._name = backend_name
        self.simulated_blocks = simulated_blocks
        self.simulate_error = simulate_error
        self.empty_output = empty_output
        self.calls_count = 0

    @property
    def backend_name(self) -> str:
        return self._name

    def extract_page_ocr(self, page: pymupdf.Page, page_number: int) -> PageExtraction:
        self.calls_count += 1
        if self.simulate_error:
            raise OCRExtractionError(self.simulate_error)

        if self.empty_output:
            return PageExtraction(
                page_number=page_number,
                method="ocr",
                text="",
                blocks=[],
                images_count=len(page.get_images()),
                words_count=0,
                characters_count=0,
            )

        if self.simulated_blocks is not None:
            blocks = [
                b.model_copy(update={"page_number": page_number})
                for b in self.simulated_blocks
            ]
        else:
            # Default synthetic test block
            blocks = [
                ExtractedBlock(
                    text="SYNTHETIC OCR TEXT RECOGNIZED",
                    bounding_box=[10.0, 10.0, 200.0, 50.0],
                    page_number=page_number,
                    confidence=0.8850,
                    is_ocr=True,
                )
            ]

        full_text = "\n".join(b.text for b in blocks)
        words = [w for w in full_text.split() if any(c.isalnum() for c in w)]

        return PageExtraction(
            page_number=page_number,
            method="ocr",
            text=full_text,
            blocks=blocks,
            images_count=len(page.get_images()),
            words_count=len(words),
            characters_count=len(full_text),
        )
