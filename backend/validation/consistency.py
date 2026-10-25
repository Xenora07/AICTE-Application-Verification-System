"""
backend/validation/consistency.py - Cross-document consistency verification for SIH26261 (Person 2).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "dataset"
for p in [str(REPO_ROOT), str(DATASET_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.validators.cross_document import (
        check_cross_institution_id,
        check_cross_institution_name,
        check_cross_intake_mismatch,
        check_duplicate_hash,
    )
except ImportError:
    from dataset.src.validators.cross_document import (
        check_cross_institution_id,
        check_cross_institution_name,
        check_cross_intake_mismatch,
        check_duplicate_hash,
    )

__all__ = [
    "check_cross_institution_id",
    "check_cross_institution_name",
    "check_cross_intake_mismatch",
    "check_duplicate_hash",
]
