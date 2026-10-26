"""
src/schemas/common.py - Common primitives and evidence structures for document extraction.
Provides evidence-preserving models, bounding box validations, and honest confidence handling.
"""

from typing import Any, List, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class BoundingBox(BaseModel):
    """
    Normalized or absolute bounding box coordinates [x0, y0, x1, y1].
    Coordinate System Convention:
    - Origin (0,0) is at the TOP-LEFT of the page (PyMuPDF / standard PDF rendering convention).
    - x0: left edge coordinate (PDF points, 1/72 inch).
    - y0: top edge coordinate (PDF points, 1/72 inch).
    - x1: right edge coordinate (PDF points, 1/72 inch).
    - y1: bottom edge coordinate (PDF points, 1/72 inch).
    - Condition: 0 <= x0 <= x1 and 0 <= y0 <= y1.
    """
    x0: float = Field(ge=0.0, description="Left coordinate in PDF points (top-left origin).")
    y0: float = Field(ge=0.0, description="Top coordinate in PDF points (top-left origin).")
    x1: float = Field(ge=0.0, description="Right coordinate in PDF points (top-left origin).")
    y1: float = Field(ge=0.0, description="Bottom coordinate in PDF points (top-left origin).")

    @model_validator(mode="after")
    def validate_box_order(self) -> "BoundingBox":
        if self.x0 > self.x1:
            raise ValueError(f"Invalid bounding box: x0 ({self.x0}) cannot exceed x1 ({self.x1})")
        if self.y0 > self.y1:
            raise ValueError(f"Invalid bounding box: y0 ({self.y0}) cannot exceed y1 ({self.y1})")
        return self

    def to_list(self) -> List[float]:
        return [round(self.x0, 2), round(self.y0, 2), round(self.x1, 2), round(self.y1, 2)]


class FieldEvidence(BaseModel):
    """
    Evidence-preserving field extraction model.
    Maintains exact raw text, normalized value, source page, bounding box,
    honest confidence score, and explicit uncertainty indicators.
    """
    raw_value: Optional[str] = Field(
        default=None,
        description="Exact raw text snippet extracted from the source page."
    )
    normalized_value: Optional[Any] = Field(
        default=None,
        description="Type-coerced and normalized representation (e.g. ISO date, integer, float, or cleaned string)."
    )
    page_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="1-indexed source page number where the field was discovered. Must be >= 1 if present."
    )
    bounding_box: Optional[List[float]] = Field(
        default=None,
        description="Coordinates [x0, y0, x1, y1] in PDF points (top-left origin), where x0 <= x1 and y0 <= y1."
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Preserved confidence score from OCR engine [0.0 - 1.0]. None for deterministic digital text."
    )
    extraction_method: Optional[Literal["digital", "ocr", "hybrid"]] = Field(
        default=None,
        description="Extraction pipeline path used to retrieve this field."
    )
    is_uncertain: bool = Field(
        default=False,
        description="True if the field has low recognition confidence, ambiguous format, or conflicting occurrences."
    )
    uncertainty_reason: Optional[str] = Field(
        default=None,
        description="Detailed reason for uncertainty or flagged manual review."
    )

    @field_validator("bounding_box", mode="before")
    @classmethod
    def validate_bounding_box(cls, v: Any) -> Optional[List[float]]:
        if v is None:
            return None
        if isinstance(v, BoundingBox):
            return v.to_list()
        if not isinstance(v, (list, tuple)):
            raise ValueError(f"Bounding box must be a list/tuple of 4 floats [x0, y0, x1, y1], got {type(v).__name__}")
        if len(v) != 4:
            raise ValueError(f"Bounding box must contain exactly 4 coordinates [x0, y0, x1, y1], got {len(v)}")
        try:
            x0, y0, x1, y1 = float(v[0]), float(v[1]), float(v[2]), float(v[3])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Bounding box coordinates must be numeric floats: {exc}")
        if x0 < 0 or y0 < 0 or x1 < 0 or y1 < 0:
            raise ValueError(f"Bounding box coordinates must be non-negative: {[x0, y0, x1, y1]}")
        if x0 > x1:
            raise ValueError(f"Invalid bounding box: x0 ({x0}) cannot exceed x1 ({x1})")
        if y0 > y1:
            raise ValueError(f"Invalid bounding box: y0 ({y0}) cannot exceed y1 ({y1})")
        return [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]


class TableData(BaseModel):
    """Structured tabular data extracted from a document page (e.g., approved intake tables)."""
    table_name: str = Field(description="Descriptive identifier for the extracted table.")
    page_number: int = Field(ge=1, description="1-indexed source page number containing the table.")
    headers: List[str] = Field(default_factory=list, description="Column header strings.")
    rows: List[dict[str, Any]] = Field(default_factory=list, description="Row objects mapped by column key.")
