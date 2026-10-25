"""
backend/extraction/field_mapper.py - Regulatory field mappers and normalizers for SIH26261 (Person 1).
Exposes mappers for AICTE EoA, AICTE Mandatory Disclosure, NAAC Certificate, and NBA Accreditation.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "dataset"
for p in [str(REPO_ROOT), str(DATASET_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.mappers.regulatory_mapper import (
        RegulatoryDocumentMapper,
        AICTEEoAMapper,
        AICTEMandatoryDisclosureMapper,
        NAACCertificateMapper,
        NBAAccreditationMapper,
    )
    from src.mappers.base_mapper import BaseMapper
    from src.mappers.normalizers import (
        normalize_academic_year,
        normalize_cgpa,
        normalize_date_iso,
        normalize_grade,
        normalize_id,
        normalize_institution_name,
    )
except ImportError:
    from dataset.src.mappers.regulatory_mapper import (
        RegulatoryDocumentMapper,
        AICTEEoAMapper,
        AICTEMandatoryDisclosureMapper,
        NAACCertificateMapper,
        NBAAccreditationMapper,
    )
    from dataset.src.mappers.base_mapper import BaseMapper
    from dataset.src.mappers.normalizers import (
        normalize_academic_year,
        normalize_cgpa,
        normalize_date_iso,
        normalize_grade,
        normalize_id,
        normalize_institution_name,
    )

__all__ = [
    "RegulatoryDocumentMapper",
    "AICTEEoAMapper",
    "AICTEMandatoryDisclosureMapper",
    "NAACCertificateMapper",
    "NBAAccreditationMapper",
    "BaseMapper",
    "normalize_academic_year",
    "normalize_cgpa",
    "normalize_date_iso",
    "normalize_grade",
    "normalize_id",
    "normalize_institution_name",
]
