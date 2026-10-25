"""
backend/extraction/ocr_processor.py - Pluggable OCR interface for SIH26261 (Person 1).
Exposes EasyOCREngine, SyntheticOCREngine, and image preprocessing utilities.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "dataset"
for p in [str(REPO_ROOT), str(DATASET_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.extractors.ocr_engine import (
        BaseOCREngine,
        EasyOCREngine,
        SyntheticOCREngine,
        OCRExtractionError,
    )
    from src.extractors.image_preprocessor import preprocess_image_for_ocr
except ImportError:
    from dataset.src.extractors.ocr_engine import (
        BaseOCREngine,
        EasyOCREngine,
        SyntheticOCREngine,
        OCRExtractionError,
    )
    from dataset.src.extractors.image_preprocessor import preprocess_image_for_ocr

__all__ = [
    "BaseOCREngine",
    "EasyOCREngine",
    "SyntheticOCREngine",
    "OCRExtractionError",
    "preprocess_image_for_ocr",
]
