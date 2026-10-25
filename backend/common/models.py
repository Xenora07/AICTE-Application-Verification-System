"""
backend/common/models.py - Canonical shared Pydantic data contracts for SIH26261.
Provides unified access to ExtractionResult, FieldEvidence, ValidationFinding,
and API request/response payloads.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

# Ensure dataset/src and repo root are accessible
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "dataset"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(DATASET_PATH) not in sys.path:
    sys.path.insert(0, str(DATASET_PATH))

# Resolve circular import between mappers and extractors by pre-loading base modules
try:
    import src.extractors.base  # noqa: F401
    import src.mappers.base_mapper  # noqa: F401
except ImportError:
    pass

# Re-export core schema objects from dataset/src/schemas
try:
    from src.schemas.common import FieldEvidence, TableData
    from src.schemas.extraction_result import ExtractionResult, ProcessingMetadata
    from src.validators.schemas import (
        ValidationFinding,
        DocumentValidationReport,
        CrossDocumentConsistencyReport,
        RuleOutcome,
        RuleSeverity,
    )
except ImportError:
    # Graceful fallback if dataset is moved or structured as dataset.src
    from dataset.src.schemas.common import FieldEvidence, TableData
    from dataset.src.schemas.extraction_result import ExtractionResult, ProcessingMetadata
    from dataset.src.validators.schemas import (
        ValidationFinding,
        DocumentValidationReport,
        CrossDocumentConsistencyReport,
        RuleOutcome,
        RuleSeverity,
    )


# ==============================================================================
# Phase 9: Unified API & Reviewer Dashboard Models
# ==============================================================================

class DocumentProcessRequest(BaseModel):
    """Optional parameters passed when requesting document processing."""
    document_id: Optional[str] = Field(default=None, description="Custom document ID; generated if omitted.")
    document_type: Optional[str] = Field(default=None, description="Document type if pre-classified.")
    enable_privacy_masking: bool = Field(default=True, description="Whether to mask PII in response fields.")
    ocr_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="OCR confidence threshold.")


class NormalizedFinding(BaseModel):
    """
    Unified finding model representing Compliance, Authenticity, Privacy, or Consistency signals.
    Emitted by Phase 9 normalization layer.
    """
    finding_id: str = Field(description="Unique finding identifier.")
    category: Literal["COMPLIANCE", "AUTHENTICITY", "PRIVACY", "CONSISTENCY"] = Field(
        description="Functional category of finding."
    )
    rule_id: str = Field(description="Stable rule identifier (e.g. 'RULE_REQ_ACADEMIC_YEAR', 'AUTH_DUPLICATE_HASH').")
    rule_name: str = Field(description="Human-readable rule title.")
    outcome: Literal["PASS", "FAIL", "INCONCLUSIVE"] = Field(
        description="Finding outcome: PASS, FAIL, or INCONCLUSIVE."
    )
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] = Field(
        description="Finding severity level."
    )
    explanation: str = Field(description="Human-readable explanation of why finding was emitted.")
    affected_document_ids: List[str] = Field(default_factory=list, description="Associated document IDs.")
    affected_fields: List[str] = Field(default_factory=list, description="Fields evaluated.")
    evidence_values: Dict[str, Any] = Field(default_factory=dict, description="Raw and normalized values evaluated.")
    requires_human_review: bool = Field(default=False, description="True if manual review is required.")
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp in ISO 8601 UTC."
    )


class ReviewerSummary(BaseModel):
    """High-level summary of verification metrics for reviewer dashboard."""
    total_rules_evaluated: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    inconclusive_rules: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    info_findings: int = 0
    authenticity_signals_count: int = 0
    privacy_redactions_count: int = 0
    overall_status: Literal["VERIFIED", "NEEDS_HUMAN_REVIEW", "ACTION_REQUIRED", "REJECTED"] = "VERIFIED"
    requires_human_review: bool = False


class DocumentProcessResponse(BaseModel):
    """Complete unified payload returned by the Phase 9 backend orchestration pipeline."""
    success: bool = True
    document_id: str
    filename: str
    file_size_bytes: int
    sha256: str
    document_type: str
    processing_status: str
    processing_metadata: ProcessingMetadata
    extracted_fields: Dict[str, FieldEvidence]
    table_data: List[TableData] = Field(default_factory=list)
    validation_report: DocumentValidationReport
    normalized_findings: List[NormalizedFinding] = Field(default_factory=list)
    reviewer_summary: ReviewerSummary
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class CrossValidateRequest(BaseModel):
    """Request payload to perform cross-document consistency checks on a set of documents."""
    document_ids: Optional[List[str]] = Field(default=None, description="Document IDs to compare.")


class CrossValidateResponse(BaseModel):
    """Response payload for cross-document consistency verification."""
    success: bool = True
    consistency_report: CrossDocumentConsistencyReport
    normalized_findings: List[NormalizedFinding] = Field(default_factory=list)
    overall_status: str = "PASS"
    requires_human_review: bool = False
