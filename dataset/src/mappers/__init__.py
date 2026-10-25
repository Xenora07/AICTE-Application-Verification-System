"""
src/mappers - Deterministic evidence-preserving field mapping layer.
Extracts structured canonical fields from raw extraction results (DocumentContent).
"""

from src.mappers.base_mapper import BaseMapper
from src.mappers.normalizers import (
    normalize_academic_year,
    normalize_cgpa,
    normalize_date_iso,
    normalize_grade,
    normalize_id,
    normalize_institution_name,
)
from src.mappers.regulatory_mapper import (
    AICTEEoAMapper,
    AICTEMandatoryDisclosureMapper,
    GenericDocumentMapper,
    NAACCertificateMapper,
    NBAAccreditationMapper,
    RegulatoryDocumentMapper,
)

__all__ = [
    "BaseMapper",
    "normalize_academic_year",
    "normalize_cgpa",
    "normalize_date_iso",
    "normalize_grade",
    "normalize_id",
    "normalize_institution_name",
    "AICTEEoAMapper",
    "AICTEMandatoryDisclosureMapper",
    "NAACCertificateMapper",
    "NBAAccreditationMapper",
    "GenericDocumentMapper",
    "RegulatoryDocumentMapper",
]
