"""
backend/validation/schemas.py - Validation finding and report schemas for SIH26261 (Person 2).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "dataset"
for p in [str(REPO_ROOT), str(DATASET_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.validators.schemas import (
        ValidationFinding,
        DocumentValidationReport,
        CrossDocumentConsistencyReport,
        RuleOutcome,
        RuleSeverity,
    )
except ImportError:
    from dataset.src.validators.schemas import (
        ValidationFinding,
        DocumentValidationReport,
        CrossDocumentConsistencyReport,
        RuleOutcome,
        RuleSeverity,
    )

__all__ = [
    "ValidationFinding",
    "DocumentValidationReport",
    "CrossDocumentConsistencyReport",
    "RuleOutcome",
    "RuleSeverity",
]
