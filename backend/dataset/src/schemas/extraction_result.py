"""
src/schemas/extraction_result.py - Stable Pydantic extraction output contract for SIH26261.
Consumed by downstream modules: Validation, Privacy, Authenticity, Consistency, and API.
"""

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from src.schemas.common import FieldEvidence, TableData


class ProcessingMetadata(BaseModel):
    """Metadata regarding how the document was processed by the extraction pipeline."""
    total_pages: int = Field(ge=0, description="Total number of pages in source document.")
    processed_pages: int = Field(ge=0, description="Number of pages processed.")
    page_range: Optional[str] = Field(
        default=None,
        description="Optional page range (e.g. '1-5' or '3') used during extraction."
    )
    extraction_path: Literal["digital", "ocr", "hybrid"] = Field(
        description="High-level processing route: 'digital' (all native text), 'ocr' (all image OCR), or 'hybrid' (mixed)."
    )
    digital_pages: List[int] = Field(
        default_factory=list,
        description="1-indexed list of pages extracted digitally."
    )
    ocr_pages: List[int] = Field(
        default_factory=list,
        description="1-indexed list of pages requiring OCR."
    )
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of the extraction execution in ISO 8601 format."
    )
    ocr_backend: Optional[str] = Field(
        default=None,
        description="Identifier of the OCR engine used (e.g. 'easyocr', 'paddleocr', 'synthetic_test_engine'), if any."
    )


class ExtractionResult(BaseModel):
    """
    Standard canonical document extraction payload.
    Emitted by the extraction pipeline and consumed by downstream verification and dashboard services.

    Key Contract Invariants:
    1. Deterministic text extraction NEVER invents confidence scores (confidence is explicitly None).
    2. Document IDs follow stable prefixes (e.g. 'DOC_REAL_003', 'DOC_SCAN_001', 'SYNTH_DOC_001').
    3. Bounding boxes follow standard PDF typographic point coordinates [x0, y0, x1, y1] with top-left origin.
    4. Partial results are always preserved alongside explicit non-fatal warnings or fatal errors.
    """
    document_id: str = Field(description="Deterministic stable document ID (e.g. 'DOC_REAL_003').")
    source_file: str = Field(description="POSIX-style relative path to the original document file.")
    sha256: Optional[str] = Field(
        default=None,
        description="Full 64-character lowercase SHA-256 checksum of the original document, if available."
    )
    document_type: str = Field(
        description="Identified regulatory document type (e.g. 'aicte_eoa', 'aicte_mandatory_disclosure', 'naac_certificate', 'nba_accreditation')."
    )
    classification_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for document classification [0.0 - 1.0], if provided by a probabilistic classifier; otherwise None."
    )
    processing_status: Literal[
        "SUCCESS",
        "SUCCESS_WITH_WARNINGS",
        "SUCCESS_WITH_UNCERTAINTY",
        "NEEDS_HUMAN_REVIEW",
        "EXTRACTION_ERROR",
    ] = Field(
        default="SUCCESS",
        description="High-level processing status code."
    )
    processing_metadata: ProcessingMetadata
    fields: Dict[str, FieldEvidence] = Field(
        default_factory=dict,
        description="Map of extracted document fields with full evidence and coordinate tracking."
    )
    table_data: List[TableData] = Field(
        default_factory=list,
        description="Extracted table rows (e.g. programme approval quotas, criteria marks)."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal warnings encountered during extraction (e.g. low OCR confidence, ambiguous formats)."
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Fatal or blocking errors encountered (e.g. corrupted page, unreadable stream)."
    )

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean_v = v.strip()
        if not re.match(r"^[0-9a-fA-F]{64}$", clean_v):
            raise ValueError(f"SHA-256 must be a 64-character hexadecimal string, got '{v}' (len={len(clean_v)})")
        return clean_v.lower()

    def to_json(self, indent: int = 2) -> str:
        """Serialize payload to standard formatted JSON string."""
        return self.model_dump_json(indent=indent)

    def save_to_file(self, target_path: Path) -> None:
        """Write JSON output to the specified target path."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
