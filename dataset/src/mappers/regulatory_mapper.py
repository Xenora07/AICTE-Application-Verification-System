"""
src/mappers/regulatory_mapper.py - Specialized deterministic mappers for regulatory documents.
Implements field mapping for document types present in the dataset:
- aicte_eoa (AICTE Extension of Approval)
- aicte_mandatory_disclosure (AICTE Mandatory Disclosure)
- naac_certificate (NAAC Accreditation Certificate and Grade Sheets)
- nba_accreditation (NBA Accreditation Letters)

Follows strict evidence preservation:
- Preserves raw source text, normalized value, source page, bounding box, and extraction method.
- Preserves genuine OCR engine confidence (or None for digital text).
- Flags uncertainty with explicit uncertainty_reason when conflicting candidates exist or confidence is low.
- Missing fields remain absent/null rather than guessed.
"""

import re
from typing import Dict, List, Optional
from src.extractors.base import DocumentContent
from src.schemas.common import FieldEvidence, TableData
from src.mappers.base_mapper import BaseMapper
from src.mappers.normalizers import (
    normalize_academic_year,
    normalize_cgpa,
    normalize_date_iso,
    normalize_grade,
    normalize_id,
    normalize_institution_name,
)


class AICTEEoAMapper(BaseMapper):
    """
    Deterministic field mapper for AICTE Extension of Approval (EoA) documents.
    Extracts institution name, application ID, permanent institute ID, academic year, and accreditation body.
    """

    document_type: str = "aicte_eoa"

    INSTITUTION_NAME_PATTERN = re.compile(
        r"(?:Name\s+of\s+the\s+Institution|Name\s+of\s+the\s+Institute)\s*[:\n]\s*([^\n]+(?:\n[^\n]+)?)(?=\n\s*(?:Name\s+of\s+the\s+Society|Institution\s+Address|Address|Permanent|Application|City|State|$))",
        re.IGNORECASE,
    )
    PERMANENT_ID_PATTERN = re.compile(
        r"Permanent\s*(?:Institute\s*)?(?:Id|ID|No\.?)\s*[:\n]\s*([1-9]-[0-9]+|[0-9]+)",
        re.IGNORECASE,
    )
    APPLICATION_ID_PATTERN = re.compile(
        r"Application\s*(?:Id|ID|No\.?|Number)\s*[:\n]\s*([1-9]-[0-9]+|[0-9]+)",
        re.IGNORECASE,
    )
    ACADEMIC_YEAR_PATTERN = re.compile(
        r"(?:APPROVAL\s+PROCESS\s+|Academic\s+Year\s*[:\-]?\s*|for\s+the\s+Academic\s+Year\s*)([0-9]{4}\s*[-/]\s*[0-9]{2,4})",
        re.IGNORECASE,
    )
    BODY_PATTERN = re.compile(
        r"(ALL\s+INDIA\s+COUNCIL\s+FOR\s+TECHNICAL\s+EDUCATION|All\s+India\s+Council\s+for\s+Technical\s+Education|AICTE)",
        re.IGNORECASE,
    )
    DOC_TYPE_PATTERN = re.compile(
        r"(Extension\s+of\s+Approval\s*(?:\(EoA\))?|APPROVAL\s+PROCESS)",
        re.IGNORECASE,
    )

    def map_fields(self, content: DocumentContent) -> Dict[str, FieldEvidence]:
        fields: Dict[str, FieldEvidence] = {}

        # 1. Institution Name
        inst_name = self.search_pattern_with_evidence(
            content=content,
            pattern=self.INSTITUTION_NAME_PATTERN,
            normalizer=normalize_institution_name,
        )
        if inst_name:
            fields["institution_name"] = inst_name

        # 2. Permanent Institute ID
        perm_id = self.search_pattern_with_evidence(
            content=content,
            pattern=self.PERMANENT_ID_PATTERN,
            normalizer=normalize_id,
        )
        if perm_id:
            fields["permanent_institute_id"] = perm_id

        # 3. Application ID
        app_id = self.search_pattern_with_evidence(
            content=content,
            pattern=self.APPLICATION_ID_PATTERN,
            normalizer=normalize_id,
        )
        if app_id:
            fields["application_id"] = app_id

        # 4. Academic Year
        acad_year = self.search_pattern_with_evidence(
            content=content,
            pattern=self.ACADEMIC_YEAR_PATTERN,
            normalizer=normalize_academic_year,
        )
        if acad_year:
            fields["academic_year"] = acad_year

        # 5. Accreditation Body
        body = self.search_pattern_with_evidence(
            content=content,
            pattern=self.BODY_PATTERN,
            normalizer=lambda _: "AICTE",
        )
        if body:
            fields["accreditation_body"] = body

        # 6. Document Type evidence
        doc_type_ev = self.search_pattern_with_evidence(
            content=content,
            pattern=self.DOC_TYPE_PATTERN,
            normalizer=lambda _: "aicte_eoa",
        )
        if doc_type_ev:
            fields["document_type"] = doc_type_ev

        return fields


class AICTEMandatoryDisclosureMapper(BaseMapper):
    """
    Deterministic field mapper for AICTE Mandatory Disclosure documents.
    Extracts institution name, application ID, permanent institute ID, academic year, and accreditation body.
    """

    document_type: str = "aicte_mandatory_disclosure"

    INSTITUTION_NAME_PATTERN = re.compile(
        r"(?:(?:1\)\s*)?Name\s+of\s+the\s+Institution|Name\s+of\s+the\s+Institute|Institution\s+Name)\s*[:\n]\s*([^\n]+(?:\n[^\n]+)?)(?=\n\s*(?:Address|Location|City|State|Pin|AICTE|Permanent|Application|Phone|Email|Website|$))",
        re.IGNORECASE,
    )
    PERMANENT_ID_PATTERN = re.compile(
        r"(?:AICTE\s*permanent\s*application\s*ID|Permanent\s*(?:Institute\s*)?(?:Id|ID)|AICTE\s*File\s*No\.?)\s*[:\n]\s*([1-9]-[0-9]+|[A-Za-z0-9\-/]+)",
        re.IGNORECASE,
    )
    APPLICATION_ID_PATTERN = re.compile(
        r"(?:AICTE\s*current\s*application\s*(?:Id|ID|No\.?)|(?<!permanent\s)Application\s*(?:Id|ID|No\.?|Number))\s*[:\n]\s*([1-9]-[0-9]+|[0-9]+)",
        re.IGNORECASE,
    )
    ACADEMIC_YEAR_PATTERN = re.compile(
        r"(?:Academic\s*Year\s*[:\-]?\s*|Handbook\s*|Approved\s*Intake\s*\(?|Mandatory\s*Disclosure\s*[-–]?\s*)([0-9]{4}\s*[-/]\s*[0-9]{2,4})",
        re.IGNORECASE,
    )
    BODY_PATTERN = re.compile(
        r"(ALL\s+INDIA\s+COUNCIL\s+FOR\s+TECHNICAL\s+EDUCATION|All\s+India\s+Council\s+for\s+Technical\s+Education|AICTE)",
        re.IGNORECASE,
    )
    DOC_TYPE_PATTERN = re.compile(
        r"(MANDATORY\s+DISCLOSURE[S]?)",
        re.IGNORECASE,
    )

    def map_fields(self, content: DocumentContent) -> Dict[str, FieldEvidence]:
        fields: Dict[str, FieldEvidence] = {}

        # 1. Institution Name
        inst_name = self.search_pattern_with_evidence(
            content=content,
            pattern=self.INSTITUTION_NAME_PATTERN,
            normalizer=normalize_institution_name,
        )
        if inst_name:
            fields["institution_name"] = inst_name

        # 2. Permanent Institute ID
        perm_id = self.search_pattern_with_evidence(
            content=content,
            pattern=self.PERMANENT_ID_PATTERN,
            normalizer=normalize_id,
        )
        if perm_id:
            fields["permanent_institute_id"] = perm_id

        # 3. Application ID
        app_id = self.search_pattern_with_evidence(
            content=content,
            pattern=self.APPLICATION_ID_PATTERN,
            normalizer=normalize_id,
        )
        if app_id:
            fields["application_id"] = app_id

        # 4. Academic Year
        acad_year = self.search_pattern_with_evidence(
            content=content,
            pattern=self.ACADEMIC_YEAR_PATTERN,
            normalizer=normalize_academic_year,
        )
        if acad_year:
            fields["academic_year"] = acad_year

        # 5. Accreditation Body
        body = self.search_pattern_with_evidence(
            content=content,
            pattern=self.BODY_PATTERN,
            normalizer=lambda _: "AICTE",
        )
        if body:
            fields["accreditation_body"] = body

        # 6. Document Type
        doc_type_ev = self.search_pattern_with_evidence(
            content=content,
            pattern=self.DOC_TYPE_PATTERN,
            normalizer=lambda _: "aicte_mandatory_disclosure",
        )
        if doc_type_ev:
            fields["document_type"] = doc_type_ev

        return fields


class NAACCertificateMapper(BaseMapper):
    """
    Deterministic field mapper for NAAC Accreditation Certificates and Grade Sheets.
    Extracts institution name, accreditation grade, CGPA, valid_from, valid_to, and accreditation body.
    """

    document_type: str = "naac_certificate"

    INSTITUTION_NAME_PATTERN = re.compile(
        r"(?:This\s+is\s+to\s+certify\s+that|Name\s+of\s+the\s+Institution\s*[:\n]|pleased\s+(?:to|lo)\s+declare)\s*([^\n]+(?:\n[^\n]+)?)(?=\n\s*(?:has\s+been\s+accredited|is\s+accredited|accredited\s+with|Type\s+of\s+the\s+Institution|Dates\s+of\s+Visit|at\s+|Place|Date|Raj\s+Baug|Boni|as\s+Accredited|as\s+Sccrediled|$))",
        re.IGNORECASE,
    )
    CYCLE_FALLBACK_PATTERN = re.compile(
        r"(?:Cycle:\s*\d\)?\s*\n\s*)([A-Z\s,]+?)(?=\n\s*Track ID|\n\s*AISHE)",
    )
    GRADE_PATTERN = re.compile(
        r"(?:Grade\s*[:\-=]\s*|at\s+)([A-C]\+{0,2})\s*(?:Grade)?",
        re.IGNORECASE,
    )
    CGPA_PATTERN = re.compile(
        r"(?:Institutional\s*CGPA\s*=\s*(?:=\s*)?|CGPA\s*(?:of|at|is)?\s*[:\-=]?\s*|CGTH\s*of\s*|Grade\s+Point\s+Average[^\n]*?)([0-9][\.,][0-9Oob]{1,2})\b",
        re.IGNORECASE,
    )
    VALID_FROM_PATTERN = re.compile(
        r"(?:Valid\s*(?:from|w\.?e\.?f\.?|effective\s*from)\s*[:\-=]?\s*|Dates\s+of\s+Visit\s*[:\-]?\s*)([A-Za-z0-9\s,\-]+?)(?=\s*(?:to|upto|up\s+to|valid\s+up\s+to|$|\n))",
        re.IGNORECASE,
    )
    VALID_TO_PATTERN = re.compile(
        r"(?:(?:valid\s*(?:to|upto|up\s*to|up\s*lo)|upto|up\s*to|up\s*lo)\s*[:\-=]?\s*)([A-Za-z0-9\s,\-]+?)(?=\s*(?:$|\n|\.|\)|Grade|Acu))",
        re.IGNORECASE,
    )
    BODY_PATTERN = re.compile(
        r"(NATIONAL\s+ASSESSMENT\s+AND\s+ACCREDITATION\s+COUNCIL|National\s+Assessment\s+and\s+Accreditation\s+Council|NAAC)",
        re.IGNORECASE,
    )
    DOC_TYPE_PATTERN = re.compile(
        r"(NATIONAL\s+ASSESSMENT\s+AND\s+ACCREDITATION\s+COUNCIL|NAAC|Institutional\s+Assessment\s+and\s+Accreditation|Certificate\s+of\s+Accreditation|Gerlificale\s+%f\s+Iccredilalion)",
        re.IGNORECASE,
    )

    def map_fields(self, content: DocumentContent) -> Dict[str, FieldEvidence]:
        fields: Dict[str, FieldEvidence] = {}

        # 1. Institution Name (primary pattern, fallback to cycle header block if needed)
        inst_name = self.search_pattern_with_evidence(
            content=content,
            pattern=self.INSTITUTION_NAME_PATTERN,
            normalizer=normalize_institution_name,
        )
        if not inst_name:
            inst_name = self.search_pattern_with_evidence(
                content=content,
                pattern=self.CYCLE_FALLBACK_PATTERN,
                normalizer=normalize_institution_name,
            )
        if inst_name:
            fields["institution_name"] = inst_name

        # 2. Accreditation Grade
        grade = self.search_pattern_with_evidence(
            content=content,
            pattern=self.GRADE_PATTERN,
            normalizer=normalize_grade,
        )
        if grade:
            fields["accreditation_grade"] = grade

        # 3. CGPA
        cgpa = self.search_pattern_with_evidence(
            content=content,
            pattern=self.CGPA_PATTERN,
            normalizer=normalize_cgpa,
        )
        if cgpa:
            fields["cgpa"] = cgpa

        # 4. Valid From
        valid_from = self.search_pattern_with_evidence(
            content=content,
            pattern=self.VALID_FROM_PATTERN,
            normalizer=normalize_date_iso,
        )
        if valid_from:
            fields["valid_from"] = valid_from

        # 5. Valid To
        valid_to = self.search_pattern_with_evidence(
            content=content,
            pattern=self.VALID_TO_PATTERN,
            normalizer=normalize_date_iso,
        )
        if valid_to:
            fields["valid_to"] = valid_to

        # 6. Accreditation Body
        body = self.search_pattern_with_evidence(
            content=content,
            pattern=self.BODY_PATTERN,
            normalizer=lambda _: "NAAC",
        )
        if body:
            fields["accreditation_body"] = body

        # 7. Document Type
        doc_type_ev = self.search_pattern_with_evidence(
            content=content,
            pattern=self.DOC_TYPE_PATTERN,
            normalizer=lambda _: "naac_certificate",
        )
        if doc_type_ev:
            fields["document_type"] = doc_type_ev

        return fields


class NBAAccreditationMapper(BaseMapper):
    """
    Deterministic field mapper for NBA Accreditation letters.
    Extracts institution name, programme details, validity period, and accreditation body.
    """

    document_type: str = "nba_accreditation"

    INSTITUTION_NAME_PATTERN = re.compile(
        r"(?:offered\s+by\s+|applied\s+by\s+|convey\s+the\s+accreditation\s+status\s+to\s+|To\s*,\s*\n\s*(?:The\s+Principal|The\s+Director)\s*,\s*\n\s*)([A-Za-z0-9\s.,&'\-()]+?)(?=\n\s*(?:has\s+been|are\s+accredited|is\s+accredited|under\s+Tier|Tier-I|Tier-II|for\s+the\s+Academic|Subject|Sub:|Name\s+of\s+the\s+Programme|Programmes?\s*Accredited|$))",
        re.IGNORECASE,
    )
    PROGRAMME_PATTERN = re.compile(
        r"(?:Programmes?\s*Accredited|Name\s+of\s+the\s+Programme\(?s?\)?)\s*[:\n]\s*([A-Za-z0-9\s.,&'\-()]+?)(?=\n\s*(?:Academic\s*Years?|Period|Validity|Level|$))",
        re.IGNORECASE,
    )
    VALIDITY_PATTERN = re.compile(
        r"(?:Academic\s*Years?\s*|Period\s+of\s+Validity\s*[:\-]?\s*)([0-9]{4}\s*[-/]\s*[0-9]{2,4}(?:\s*(?:to|and|-)\s*[0-9]{4}\s*[-/]\s*[0-9]{2,4})?)",
        re.IGNORECASE,
    )
    BODY_PATTERN = re.compile(
        r"(NATIONAL\s+BOARD\s+OF\s+ACCREDITATION|National\s+Board\s+of\s+Accreditation|NBA)",
        re.IGNORECASE,
    )
    DOC_TYPE_PATTERN = re.compile(
        r"(NATIONAL\s+BOARD\s+OF\s+ACCREDITATION|NBA)",
        re.IGNORECASE,
    )

    def map_fields(self, content: DocumentContent) -> Dict[str, FieldEvidence]:
        fields: Dict[str, FieldEvidence] = {}

        # 1. Institution Name
        inst_name = self.search_pattern_with_evidence(
            content=content,
            pattern=self.INSTITUTION_NAME_PATTERN,
            normalizer=normalize_institution_name,
        )
        if inst_name:
            fields["institution_name"] = inst_name

        # 2. Programme Name
        prog = self.search_pattern_with_evidence(
            content=content,
            pattern=self.PROGRAMME_PATTERN,
            normalizer=lambda s: s.strip(),
        )
        if prog:
            fields["programme_name"] = prog

        # 3. Validity Period / Academic Year
        validity = self.search_pattern_with_evidence(
            content=content,
            pattern=self.VALIDITY_PATTERN,
            normalizer=normalize_academic_year,
        )
        if validity:
            fields["academic_year"] = validity

        # 4. Accreditation Body
        body = self.search_pattern_with_evidence(
            content=content,
            pattern=self.BODY_PATTERN,
            normalizer=lambda _: "NBA",
        )
        if body:
            fields["accreditation_body"] = body

        # 5. Document Type
        doc_type_ev = self.search_pattern_with_evidence(
            content=content,
            pattern=self.DOC_TYPE_PATTERN,
            normalizer=lambda _: "nba_accreditation",
        )
        if doc_type_ev:
            fields["document_type"] = doc_type_ev

        return fields


class GenericDocumentMapper(BaseMapper):
    """
    Fallback mapper for documents without a dedicated specialized schema.
    Attempts conservative extraction of common institutional markers without making unfounded guesses.
    """

    document_type: str = "generic"

    GENERIC_INSTITUTION_PATTERN = re.compile(
        r"(?:Name\s+of\s+the\s+Institution|Name\s+of\s+the\s+Institute|Name\s+of\s+the\s+College|University)\s*[:\n]\s*([^\n]+)",
        re.IGNORECASE,
    )

    def map_fields(self, content: DocumentContent) -> Dict[str, FieldEvidence]:
        fields: Dict[str, FieldEvidence] = {}
        inst_name = self.search_pattern_with_evidence(
            content=content,
            pattern=self.GENERIC_INSTITUTION_PATTERN,
            normalizer=normalize_institution_name,
        )
        if inst_name:
            fields["institution_name"] = inst_name
        return fields


class RegulatoryDocumentMapper(BaseMapper):
    """
    Master dispatcher for regulatory document field mapping.
    Selects the appropriate specialized mapper based on explicit document_type
    or header/content detection.
    """

    def __init__(self, document_type: Optional[str] = None):
        self.explicit_document_type = document_type
        self._mappers: Dict[str, BaseMapper] = {
            "aicte_eoa": AICTEEoAMapper(),
            "aicte_mandatory_disclosure": AICTEMandatoryDisclosureMapper(),
            "naac_certificate": NAACCertificateMapper(),
            "nba_accreditation": NBAAccreditationMapper(),
            "generic": GenericDocumentMapper(),
        }

    def detect_document_type(self, content: DocumentContent) -> str:
        """Conservatively detect document type from full document text."""
        text_snippet = content.full_text[:3000].lower()

        if "national assessment and accreditation council" in text_snippet or "naac" in text_snippet:
            return "naac_certificate"
        if "national board of accreditation" in text_snippet or "nba" in text_snippet:
            return "nba_accreditation"
        if "mandatory disclosure" in text_snippet:
            return "aicte_mandatory_disclosure"
        if "all india council for technical education" in text_snippet or "extension of approval" in text_snippet:
            return "aicte_eoa"

        return "generic"

    def get_delegate(self, content: DocumentContent) -> BaseMapper:
        """Resolve the appropriate concrete mapper."""
        doc_type = self.explicit_document_type
        if not doc_type or doc_type == "unknown":
            doc_type = self.detect_document_type(content)

        return self._mappers.get(doc_type, self._mappers["generic"])

    def map_fields(self, content: DocumentContent) -> Dict[str, FieldEvidence]:
        delegate = self.get_delegate(content)
        return delegate.map_fields(content)

    def extract_tables(self, content: DocumentContent) -> List[TableData]:
        delegate = self.get_delegate(content)
        return delegate.extract_tables(content)
