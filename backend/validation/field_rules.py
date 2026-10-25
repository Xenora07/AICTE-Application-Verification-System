"""
backend/validation/field_rules.py - Single-document validation rules and engine for SIH26261 (Person 2).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "dataset"
for p in [str(REPO_ROOT), str(DATASET_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
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
    from src.validators.engine import ValidationEngine
except ImportError:
    from dataset.src.validators.rules import (
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
    from dataset.src.validators.engine import ValidationEngine

__all__ = [
    "ValidationEngine",
    "rule_ambiguous_evidence",
    "rule_cgpa_range",
    "rule_date_range_valid",
    "rule_file_parseable",
    "rule_format_application_id",
    "rule_format_permanent_id",
    "rule_grade_validity",
    "rule_ocr_confidence_threshold",
    "rule_required_academic_year",
    "rule_schema_conformance",
]
