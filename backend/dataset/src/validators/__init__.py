"""
src/validators package - Deterministic validation and cross-document consistency engine for SIH26261.
Provides:
- ValidationFinding, DocumentValidationReport, CrossDocumentConsistencyReport
- RuleOutcome, RuleSeverity
- ValidationEngine
- Individual rule functions for single-document and cross-document checks
"""

from src.validators.cross_document import (
    check_cross_institution_id,
    check_cross_institution_name,
    check_cross_intake_mismatch,
    check_duplicate_hash,
)
from src.validators.engine import ValidationEngine
from src.validators.rules import (
    rule_ambiguous_evidence,
    rule_cgpa_range,
    rule_date_range_valid,
    rule_file_parseable,
    rule_format_application_id,
    rule_format_permanent_id,
    rule_grade_validity,
    rule_ocr_confidence_threshold,
    rule_required_academic_year,
    rule_schema_conformance,
)
from src.validators.schemas import (
    CrossDocumentConsistencyReport,
    DocumentValidationReport,
    RuleOutcome,
    RuleSeverity,
    ValidationFinding,
)

__all__ = [
    "ValidationEngine",
    "ValidationFinding",
    "DocumentValidationReport",
    "CrossDocumentConsistencyReport",
    "RuleOutcome",
    "RuleSeverity",
    "rule_file_parseable",
    "rule_schema_conformance",
    "rule_required_academic_year",
    "rule_format_application_id",
    "rule_format_permanent_id",
    "rule_date_range_valid",
    "rule_cgpa_range",
    "rule_grade_validity",
    "rule_ocr_confidence_threshold",
    "rule_ambiguous_evidence",
    "check_cross_institution_id",
    "check_cross_institution_name",
    "check_cross_intake_mismatch",
    "check_duplicate_hash",
]
