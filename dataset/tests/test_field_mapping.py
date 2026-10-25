"""
tests/test_field_mapping.py - Comprehensive test suite for Phase 6 field-mapping layer.
Tests:
1. Normalizer functions for institution names, academic years, IDs, ISO dates, CGPA, and grades.
2. Synthetic field extractions across all 4 regulatory document types (AICTE EoA, AICTE Mandatory Disclosure, NAAC, NBA).
3. Ambiguity handling: conflicting candidates flag uncertainty; identical candidates remain clean.
4. Missing field handling: absent fields remain unmapped, never guessed or fabricated.
5. Evidence preservation: raw values, page numbers, coordinates, nullable digital confidence, and OCR confidence.
6. OCR low-confidence threshold flagging.
7. End-to-end test on a real digital PDF (KGEC_AICTE_Approval_2026-27.pdf).
8. End-to-end test on a real scanned PDF (NAAC_Certificate.pdf) using EasyOCR.
"""

from pathlib import Path
import pytest

from src.extractors.base import DocumentContent, ExtractedBlock, PageExtraction
from src.extractors.hybrid_router import extract_document_to_contract
from src.extractors.ocr_engine import EasyOCREngine
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
    NAACCertificateMapper,
    NBAAccreditationMapper,
    RegulatoryDocumentMapper,
)
from src.schemas.common import FieldEvidence
from src.schemas.extraction_result import ExtractionResult


# ==============================================================================
# 1. Normalizer Unit Tests
# ==============================================================================

def test_normalize_institution_name():
    # Uppercase conversion to title case
    assert normalize_institution_name("KALYANI GOVERNMENT ENGINEERING COLLEGE") == "Kalyani Government Engineering College"
    # Mixed case preserved
    assert normalize_institution_name("Apex Institute of Technology") == "Apex Institute of Technology"
    # Trailing punctuation cleaned
    assert normalize_institution_name("Vivekananda Polytechnic, ") == "Vivekananda Polytechnic"
    assert normalize_institution_name("Name of the Institution: ") == "Name of the Institution"
    # Whitespace condensed
    assert normalize_institution_name("   TERNA   ENGINEERING \n  COLLEGE  ") == "Terna Engineering College"


def test_normalize_academic_year():
    # 2-digit end year expansion
    assert normalize_academic_year("2026-27") == "2026-2027"
    assert normalize_academic_year("2025/26") == "2025-2026"
    assert normalize_academic_year("2021-22") == "2021-2022"
    # Full 4-digit preservation
    assert normalize_academic_year("2022-2027") == "2022-2027"
    assert normalize_academic_year("2025-2026") == "2025-2026"
    # Multi-period spans (NBA validity)
    assert normalize_academic_year("2022-2023 to 2026-2027") == "2022-2027"
    assert normalize_academic_year("2021-22 to 2023-24") == "2021-2024"
    # Fallback
    assert normalize_academic_year("unknown") == "unknown"


def test_normalize_id():
    assert normalize_id(" 1 - 46227285868 ") == "1-46227285868"
    assert normalize_id("1-5884273") == "1-5884273"
    assert normalize_id("southern/1-44640924090") == "SOUTHERN/1-44640924090"


def test_normalize_date_iso():
    # Varied written and numeric formats
    assert normalize_date_iso("June 01, 2025") == "2025-06-01"
    assert normalize_date_iso("16-Mar-2026") == "2026-03-16"
    assert normalize_date_iso("06 - 04 - 2022") == "2022-04-06"
    assert normalize_date_iso("30-06-2027") == "2027-06-30"
    assert normalize_date_iso("2025-06-01") == "2025-06-01"
    assert normalize_date_iso("invalid date format") is None


def test_normalize_cgpa():
    assert normalize_cgpa("3.42") == 3.42
    assert normalize_cgpa("3.02") == 3.02
    # OCR character substitution 'O' -> '0'
    assert normalize_cgpa("3.O8") == 3.08
    assert normalize_cgpa("3.o5") == 3.05
    assert normalize_cgpa("no numeric value") is None


def test_normalize_grade():
    assert normalize_grade("A+") == "A+"
    assert normalize_grade("a++") == "A++"
    assert normalize_grade("at A+ Grade") == "A+"
    assert normalize_grade("Grade: B++") == "B++"


# ==============================================================================
# 2. Synthetic Mapper Tests: AICTE EoA
# ==============================================================================

def test_aicte_eoa_mapper_synthetic():
    mapper = AICTEEoAMapper()
    content = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text=(
                    "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION\n"
                    "APPROVAL PROCESS 2026-27\n"
                    "Extension of Approval (EoA)\n"
                    "Permanent Id\n1-5884273\n"
                    "Application Id\n1-46227285868\n"
                    "Name of the Institution\nAPEX INSTITUTE OF TECHNOLOGY\n"
                    "Institution Address\nSalt Lake City, Kolkata\n"
                ),
                blocks=[
                    ExtractedBlock(
                        text="ALL INDIA COUNCIL FOR TECHNICAL EDUCATION",
                        bounding_box=[100.0, 50.0, 500.0, 65.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                    ExtractedBlock(
                        text="Permanent Id\n1-5884273",
                        bounding_box=[72.0, 100.0, 200.0, 120.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                    ExtractedBlock(
                        text="Application Id\n1-46227285868",
                        bounding_box=[250.0, 100.0, 400.0, 120.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                    ExtractedBlock(
                        text="Name of the Institution\nAPEX INSTITUTE OF TECHNOLOGY\nInstitution Address",
                        bounding_box=[72.0, 140.0, 450.0, 170.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            )
        ],
    )

    fields = mapper.map_fields(content)

    assert "institution_name" in fields
    assert fields["institution_name"].normalized_value == "Apex Institute of Technology"
    assert fields["institution_name"].page_number == 1
    assert fields["institution_name"].confidence is None  # Strictly null for digital text
    assert fields["institution_name"].extraction_method == "digital"
    assert fields["institution_name"].bounding_box == [72.0, 140.0, 450.0, 170.0]

    assert "application_id" in fields
    assert fields["application_id"].normalized_value == "1-46227285868"
    assert fields["application_id"].bounding_box == [250.0, 100.0, 400.0, 120.0]

    assert "permanent_institute_id" in fields
    assert fields["permanent_institute_id"].normalized_value == "1-5884273"

    assert "academic_year" in fields
    assert fields["academic_year"].normalized_value == "2026-2027"

    assert "accreditation_body" in fields
    assert fields["accreditation_body"].normalized_value == "AICTE"

    assert "document_type" in fields
    assert fields["document_type"].normalized_value == "aicte_eoa"


# ==============================================================================
# 3. Synthetic Mapper Tests: AICTE Mandatory Disclosure
# ==============================================================================

def test_aicte_mandatory_disclosure_mapper_synthetic():
    mapper = AICTEMandatoryDisclosureMapper()
    content = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text=(
                    "MANDATORY DISCLOSURE\n"
                    "AICTE permanent application ID: 1-4011650\n"
                    "AICTE current application ID: 1-44640924090\n"
                    "Name of the Institution\nTERNA ENGINEERING COLLEGE\n"
                    "Approved Intake (2025-26)\n"
                ),
                blocks=[
                    ExtractedBlock(
                        text="MANDATORY DISCLOSURE",
                        bounding_box=[150.0, 40.0, 450.0, 60.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                    ExtractedBlock(
                        text="Name of the Institution\nTERNA ENGINEERING COLLEGE\nAddress",
                        bounding_box=[50.0, 120.0, 400.0, 150.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            )
        ],
    )

    fields = mapper.map_fields(content)

    assert fields["institution_name"].normalized_value == "Terna Engineering College"
    assert fields["permanent_institute_id"].normalized_value == "1-4011650"
    assert fields["application_id"].normalized_value == "1-44640924090"
    assert fields["academic_year"].normalized_value == "2025-2026"
    assert fields["document_type"].normalized_value == "aicte_mandatory_disclosure"


# ==============================================================================
# 4. Synthetic Mapper Tests: NAAC Certificate
# ==============================================================================

def test_naac_certificate_mapper_synthetic():
    mapper = NAACCertificateMapper()
    content = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="ocr",
        pages=[
            PageExtraction(
                page_number=1,
                method="ocr",
                text=(
                    "NATIONAL ASSESSMENT AND ACCREDITATION COUNCIL\n"
                    "Certificate of Accreditation\n"
                    "This is to certify that\n"
                    "METROPOLITAN UNIVERSITY\n"
                    "has been accredited at A+ Grade\n"
                    "with CGPA of 3.42\n"
                    "Valid from June 01, 2025 upto May 31, 2030\n"
                ),
                blocks=[
                    ExtractedBlock(
                        text="NATIONAL ASSESSMENT AND ACCREDITATION COUNCIL",
                        bounding_box=[80.0, 60.0, 520.0, 85.0],
                        page_number=1,
                        confidence=0.98,
                        is_ocr=True,
                    ),
                    ExtractedBlock(
                        text="This is to certify that\nMETROPOLITAN UNIVERSITY\nhas been accredited",
                        bounding_box=[90.0, 180.0, 480.0, 220.0],
                        page_number=1,
                        confidence=0.94,
                        is_ocr=True,
                    ),
                    ExtractedBlock(
                        text="Grade: A+",
                        bounding_box=[200.0, 280.0, 300.0, 300.0],
                        page_number=1,
                        confidence=0.95,
                        is_ocr=True,
                    ),
                    ExtractedBlock(
                        text="CGPA of 3.42",
                        bounding_box=[200.0, 310.0, 320.0, 330.0],
                        page_number=1,
                        confidence=0.91,
                        is_ocr=True,
                    ),
                    ExtractedBlock(
                        text="Valid from June 01, 2025 upto May 31, 2030",
                        bounding_box=[100.0, 400.0, 450.0, 420.0],
                        page_number=1,
                        confidence=0.89,
                        is_ocr=True,
                    ),
                ],
            )
        ],
    )

    fields = mapper.map_fields(content)

    assert fields["institution_name"].normalized_value == "Metropolitan University"
    assert fields["accreditation_grade"].normalized_value == "A+"
    assert fields["cgpa"].normalized_value == 3.42
    assert fields["valid_from"].normalized_value == "2025-06-01"
    assert fields["valid_to"].normalized_value == "2030-05-31"
    assert fields["accreditation_body"].normalized_value == "NAAC"
    assert fields["document_type"].normalized_value == "naac_certificate"

    # Verify OCR confidence preserved
    assert fields["accreditation_body"].confidence == 0.98
    assert fields["institution_name"].confidence == 0.94
    assert fields["cgpa"].confidence == 0.91
    assert fields["institution_name"].extraction_method == "ocr"


# ==============================================================================
# 5. Synthetic Mapper Tests: NBA Accreditation
# ==============================================================================

def test_nba_accreditation_mapper_synthetic():
    mapper = NBAAccreditationMapper()
    content = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text=(
                    "NATIONAL BOARD OF ACCREDITATION\n"
                    "Sub: Accreditation status of programmes applied by\n"
                    "CHAITANYA BHARATHI INSTITUTE OF TECHNOLOGY\n"
                    "Name of the Programme: Computer Science and Engineering\n"
                    "Academic Years 2022-2023 to 2026-2027\n"
                ),
                blocks=[
                    ExtractedBlock(
                        text="NATIONAL BOARD OF ACCREDITATION",
                        bounding_box=[100.0, 50.0, 500.0, 70.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                    ExtractedBlock(
                        text="applied by\nCHAITANYA BHARATHI INSTITUTE OF TECHNOLOGY\nName of the Programme",
                        bounding_box=[80.0, 150.0, 500.0, 190.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            )
        ],
    )

    fields = mapper.map_fields(content)

    assert "Chaitanya Bharathi Institute" in fields["institution_name"].normalized_value
    assert fields["programme_name"].normalized_value == "Computer Science and Engineering"
    assert fields["academic_year"].normalized_value == "2022-2027"
    assert fields["accreditation_body"].normalized_value == "NBA"
    assert fields["document_type"].normalized_value == "nba_accreditation"


# ==============================================================================
# 6. Ambiguity Handling Tests (Requirement 5)
# ==============================================================================

def test_ambiguity_conflicting_candidates_flagged():
    """
    When conflicting candidate values exist across blocks or pages,
    the field evidence must retain primary value, set is_uncertain=True,
    and include conflict details in uncertainty_reason.
    """
    mapper = AICTEEoAMapper()
    content = DocumentContent(
        total_pages=2,
        processed_pages=2,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text="APPROVAL PROCESS 2026-27\nName of the Institution\nAPEX TECH\nAddress",
                blocks=[
                    ExtractedBlock(
                        text="APPROVAL PROCESS 2026-27",
                        bounding_box=[100.0, 50.0, 300.0, 70.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            ),
            PageExtraction(
                page_number=2,
                method="digital",
                text="APPROVAL PROCESS 2024-25\nName of the Institution\nAPEX TECH\nAddress",
                blocks=[
                    ExtractedBlock(
                        text="APPROVAL PROCESS 2024-25",
                        bounding_box=[100.0, 50.0, 300.0, 70.0],
                        page_number=2,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            ),
        ],
    )

    fields = mapper.map_fields(content)

    assert "academic_year" in fields
    acad_ev = fields["academic_year"]
    assert acad_ev.is_uncertain is True
    assert acad_ev.uncertainty_reason is not None
    assert "Conflicting candidates detected" in acad_ev.uncertainty_reason
    assert "2026-27" in acad_ev.uncertainty_reason
    assert "2024-25" in acad_ev.uncertainty_reason


def test_ambiguity_identical_candidates_clean():
    """
    When identical candidates appear repeatedly across pages,
    there is no conflict; is_uncertain must remain False.
    """
    mapper = AICTEEoAMapper()
    content = DocumentContent(
        total_pages=2,
        processed_pages=2,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text="Application Id\n1-46227285868\nName of the Institution\nAPEX TECH\nAddress",
                blocks=[
                    ExtractedBlock(
                        text="Application Id\n1-46227285868",
                        bounding_box=[100.0, 50.0, 300.0, 70.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            ),
            PageExtraction(
                page_number=2,
                method="digital",
                text="Application Id\n1-46227285868\nName of the Institution\nAPEX TECH\nAddress",
                blocks=[
                    ExtractedBlock(
                        text="Application Id\n1-46227285868",
                        bounding_box=[100.0, 50.0, 300.0, 70.0],
                        page_number=2,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            ),
        ],
    )

    fields = mapper.map_fields(content)

    assert fields["application_id"].is_uncertain is False
    assert fields["application_id"].uncertainty_reason is None


def test_missing_fields_remain_absent_not_guessed():
    """
    Fields that are not visibly present in the document content
    must remain absent/null and never guessed or hallucinated.
    """
    mapper = AICTEEoAMapper()
    # Content has institution name, but NO application_id, permanent_id, or academic_year
    content = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text="Name of the Institution\nSTANDALONE ACADEMY\nAddress: City Center",
                blocks=[
                    ExtractedBlock(
                        text="Name of the Institution\nSTANDALONE ACADEMY\nAddress: City Center",
                        bounding_box=[50.0, 50.0, 400.0, 90.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            )
        ],
    )

    fields = mapper.map_fields(content)

    assert "institution_name" in fields
    assert "application_id" not in fields
    assert "permanent_institute_id" not in fields
    assert "academic_year" not in fields
    assert "accreditation_grade" not in fields


def test_ocr_low_confidence_flagged():
    """
    When an OCR block has confidence below the 0.65 threshold,
    the field evidence must flag is_uncertain=True.
    """
    mapper = NAACCertificateMapper()
    content = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="ocr",
        pages=[
            PageExtraction(
                page_number=1,
                method="ocr",
                text="NATIONAL ASSESSMENT AND ACCREDITATION COUNCIL\nGrade: A+\nCGPA: 3.08",
                blocks=[
                    ExtractedBlock(
                        text="CGPA: 3.08",
                        bounding_box=[100.0, 200.0, 250.0, 220.0],
                        page_number=1,
                        confidence=0.48,  # Below 0.65 threshold
                        is_ocr=True,
                    ),
                ],
            )
        ],
    )

    fields = mapper.map_fields(content)

    assert "cgpa" in fields
    cgpa_ev = fields["cgpa"]
    assert cgpa_ev.confidence == 0.48
    assert cgpa_ev.is_uncertain is True
    assert "0.48" in cgpa_ev.uncertainty_reason


# ==============================================================================
# 7. Regulatory Document Master Dispatcher Tests
# ==============================================================================

def test_regulatory_dispatcher_content_routing():
    dispatcher = RegulatoryDocumentMapper()

    # Content with AICTE Mandatory Disclosure markers
    content_md = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text="MANDATORY DISCLOSURE\nName of the Institute\nCollege of Engineering\nAddress",
                blocks=[],
            )
        ],
    )
    assert dispatcher.detect_document_type(content_md) == "aicte_mandatory_disclosure"

    # Content with NAAC markers
    content_naac = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text="NATIONAL ASSESSMENT AND ACCREDITATION COUNCIL\nGrade Sheet",
                blocks=[],
            )
        ],
    )
    assert dispatcher.detect_document_type(content_naac) == "naac_certificate"

    # Content with NBA markers
    content_nba = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text="NATIONAL BOARD OF ACCREDITATION\nSub: Accreditation status",
                blocks=[],
            )
        ],
    )
    assert dispatcher.detect_document_type(content_nba) == "nba_accreditation"


# ==============================================================================
# 8. End-to-End Test on Real Digital PDF
# ==============================================================================

def test_e2e_real_digital_document():
    pdf_path = Path("real_documents/KGEC_AICTE_Approval_2026-27.pdf")
    assert pdf_path.exists(), f"Source file missing: {pdf_path}"

    mapper = RegulatoryDocumentMapper(document_type="aicte_eoa")
    result: ExtractionResult = extract_document_to_contract(
        doc_path=pdf_path,
        document_id="DOC_REAL_003",
        document_type="aicte_eoa",
        page_range="1",
        mapper=mapper,
    )

    # 1. Processing status and contract conformance
    assert result.processing_status in ("SUCCESS", "SUCCESS_WITH_UNCERTAINTY", "SUCCESS_WITH_WARNINGS")
    assert result.processing_metadata.extraction_path == "digital"
    assert result.processing_metadata.total_pages == 5
    assert result.processing_metadata.processed_pages == 1

    # 2. Field assertions
    fields = result.fields
    assert "institution_name" in fields
    assert "Kalyani Government Engineering College" in fields["institution_name"].normalized_value
    assert fields["institution_name"].page_number == 1
    assert fields["institution_name"].confidence is None  # Strictly null for digital text
    assert fields["institution_name"].extraction_method == "digital"
    # Block 14 combines Institution Name and Society/Trust Name in a multi-field table cell
    # So bounding box is safely None to prevent fabricating coordinates or coarse false attribution
    assert fields["institution_name"].bounding_box is None

    assert "application_id" in fields
    assert fields["application_id"].normalized_value == "1-46227285868"
    assert fields["application_id"].confidence is None
    # Application ID appears only in composite running footer (Block 0) and multi-cell row (Block 13)
    # Bounding box is safely None rather than coarse block or fabricated coordinates
    assert fields["application_id"].bounding_box is None

    assert "permanent_institute_id" in fields
    assert fields["permanent_institute_id"].normalized_value == "1-5884273"
    assert fields["permanent_institute_id"].confidence is None
    assert fields["permanent_institute_id"].bounding_box is None

    assert "academic_year" in fields
    assert fields["academic_year"].normalized_value == "2026-2027"
    # Dedicated title block (Block 4) reliably bounds academic year
    assert fields["academic_year"].bounding_box == pytest.approx([232.65, 114.48, 379.36, 128.25], abs=1.0)

    assert "accreditation_body" in fields
    assert fields["accreditation_body"].normalized_value == "AICTE"
    # Dedicated title banner (Block 2) reliably bounds council name
    assert fields["accreditation_body"].bounding_box == pytest.approx([114.07, 70.32, 446.35, 89.55], abs=1.0)

    # Confirm accreditation_body and application_id do NOT share the same bounding box
    assert fields["accreditation_body"].bounding_box != fields["application_id"].bounding_box

    # 3. Full Pydantic validation roundtrip
    dumped = result.model_dump()
    revalidated = ExtractionResult.model_validate(dumped)
    assert revalidated.document_id == "DOC_REAL_003"


# ==============================================================================
# 8b. Focused Audit Tests: Provenance & Normalization Safety
# ==============================================================================

def test_bounding_box_provenance_isolated_vs_composite():
    """
    Verify that bounding box is attached only when the extraction block reliably
    isolates the source text. Composite running footers or multi-cell table rows
    must return None to prevent false attribution or fabricated coordinates.
    """
    mapper = AICTEEoAMapper()
    content = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text="",
                blocks=[
                    # 1. Composite running footer with disclaimer & pagination -> Unreliable
                    ExtractedBlock(
                        text="Application No:1-46227285868\nALL INDIA COUNCIL FOR TECHNICAL EDUCATION\nPage 1 of 5\nNote: This is a Computer generated Report.",
                        bounding_box=[41.40, 758.43, 558.00, 776.38],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                    # 2. Dedicated single-line council title banner -> Reliable
                    ExtractedBlock(
                        text="All India Council for Technical Education",
                        bounding_box=[114.07, 70.32, 446.35, 89.55],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                    # 3. Multi-field table row (Permanent Id + Application Id) -> Unreliable
                    ExtractedBlock(
                        text="Permanent Id\n1-5884273\nApplication Id\n1-46227285868",
                        bounding_box=[54.0, 376.95, 480.06, 388.14],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    ),
                ],
            )
        ],
    )

    fields = mapper.map_fields(content)

    # Council title matched dedicated banner Block 2
    assert fields["accreditation_body"].bounding_box == [114.07, 70.32, 446.35, 89.55]
    # Application ID appears only in composite footer and multi-cell row -> honestly None
    assert fields["application_id"].bounding_box is None
    # Permanent ID appears only in multi-cell row -> honestly None
    assert fields["permanent_institute_id"].bounding_box is None
    # They do NOT share a false bounding box
    assert fields["accreditation_body"].bounding_box != fields["application_id"].bounding_box


def test_normalization_safety_cgpa_substitution():
    """
    Verify that OCR character substitution ('O' -> '0') preserves raw_value
    unchanged, normalizes accurately, and marks the field is_uncertain=True.
    Clean numeric values remain is_uncertain=False.
    """
    mapper = NAACCertificateMapper()

    # Clean numeric value: should remain certain
    content_clean = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="ocr",
        pages=[
            PageExtraction(
                page_number=1,
                method="ocr",
                text="",
                blocks=[
                    ExtractedBlock(
                        text="CGPA of 3.42",
                        bounding_box=[100.0, 200.0, 250.0, 220.0],
                        page_number=1,
                        confidence=0.92,
                        is_ocr=True,
                    )
                ],
            )
        ],
    )
    fields_clean = mapper.map_fields(content_clean)
    assert fields_clean["cgpa"].raw_value == "3.42"
    assert fields_clean["cgpa"].normalized_value == 3.42
    assert fields_clean["cgpa"].is_uncertain is False
    assert fields_clean["cgpa"].uncertainty_reason is None

    # Ambiguous OCR value with 'O': preserves raw, normalizes, flags uncertain
    content_sub = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="ocr",
        pages=[
            PageExtraction(
                page_number=1,
                method="ocr",
                text="",
                blocks=[
                    ExtractedBlock(
                        text="Institutional CGPA = 3.O8",
                        bounding_box=[100.0, 200.0, 250.0, 220.0],
                        page_number=1,
                        confidence=0.90,
                        is_ocr=True,
                    )
                ],
            )
        ],
    )
    fields_sub = mapper.map_fields(content_sub)
    assert fields_sub["cgpa"].raw_value == "3.O8"  # Preserved unchanged
    assert fields_sub["cgpa"].normalized_value == 3.08
    assert fields_sub["cgpa"].confidence == 0.90
    assert fields_sub["cgpa"].is_uncertain is True
    assert "OCR character substitution" in fields_sub["cgpa"].uncertainty_reason


def test_normalization_safety_institution_acronyms_and_ambiguity():
    """
    Verify that institution normalization preserves education acronyms (IIT, NIT, KGEC)
    during title casing, preserves mixed-case, and flags postal code pollution.
    """
    # Acronym preservation
    assert normalize_institution_name("IIT BOMBAY") == "IIT Bombay"
    assert normalize_institution_name("NIT ROURKELA") == "NIT Rourkela"
    assert normalize_institution_name("KALYANI GOVERNMENT ENGINEERING COLLEGE") == "Kalyani Government Engineering College"
    # Mixed case preserved
    assert normalize_institution_name("Apex Institute of Technology") == "Apex Institute of Technology"

    # Address/postal code pollution detection in field mapper
    mapper = AICTEEoAMapper()
    content_polluted = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        pages=[
            PageExtraction(
                page_number=1,
                method="digital",
                text="",
                blocks=[
                    ExtractedBlock(
                        text="Name of the Institution: COLLEGE OF ENGINEERING, PUNE - 411005\nAddress: Pune",
                        bounding_box=[50.0, 50.0, 400.0, 80.0],
                        page_number=1,
                        confidence=None,
                        is_ocr=False,
                    )
                ],
            )
        ],
    )
    fields = mapper.map_fields(content_polluted)
    assert "institution_name" in fields
    assert fields["institution_name"].is_uncertain is True
    assert "postal code" in fields["institution_name"].uncertainty_reason


def test_normalization_preserves_ocr_low_confidence():
    """
    Verify that normalization does not overwrite or erase low OCR confidence (< 0.65).
    Both the OCR confidence and character substitution reasons must be preserved.
    """
    mapper = NAACCertificateMapper()
    content = DocumentContent(
        total_pages=1,
        processed_pages=1,
        extraction_path="ocr",
        pages=[
            PageExtraction(
                page_number=1,
                method="ocr",
                text="",
                blocks=[
                    ExtractedBlock(
                        text="CGPA of 3.O8",
                        bounding_box=[100.0, 200.0, 250.0, 220.0],
                        page_number=1,
                        confidence=0.45,  # Low OCR confidence
                        is_ocr=True,
                    )
                ],
            )
        ],
    )
    fields = mapper.map_fields(content)
    cgpa = fields["cgpa"]
    assert cgpa.raw_value == "3.O8"
    assert cgpa.normalized_value == 3.08
    assert cgpa.confidence == 0.45
    assert cgpa.is_uncertain is True
    assert "0.45" in cgpa.uncertainty_reason
    assert "OCR character substitution" in cgpa.uncertainty_reason


# ==============================================================================
# 9. End-to-End Test on Real Scanned PDF
# ==============================================================================

def test_e2e_real_scanned_document():
    pdf_path = Path("scanned_documents/NAAC_Certificate.pdf")
    assert pdf_path.exists(), f"Source file missing: {pdf_path}"

    ocr_engine = EasyOCREngine()
    mapper = RegulatoryDocumentMapper(document_type="naac_certificate")

    result: ExtractionResult = extract_document_to_contract(
        doc_path=pdf_path,
        document_id="DOC_SCAN_006",
        document_type="naac_certificate",
        page_range="1",
        ocr_engine=ocr_engine,
        mapper=mapper,
    )

    # 1. Pipeline routing
    assert result.processing_metadata.extraction_path == "ocr"
    assert result.processing_metadata.ocr_backend == "easyocr"

    # 2. Accreditation body mapping from OCR
    fields = result.fields
    assert "accreditation_body" in fields
    assert fields["accreditation_body"].normalized_value == "NAAC"
    assert fields["accreditation_body"].extraction_method == "ocr"

    # 3. Verify non-brittle OCR tolerance:
    # If confidence is present on OCR evidence, it must be a valid float [0.0 - 1.0]
    for name, ev in fields.items():
        if ev.extraction_method == "ocr" and ev.confidence is not None:
            assert 0.0 <= ev.confidence <= 1.0, f"Confidence {ev.confidence} out of range for {name}"

    # 4. Full Pydantic schema validation roundtrip
    dumped = result.model_dump()
    revalidated = ExtractionResult.model_validate(dumped)
    assert revalidated.document_id == "DOC_SCAN_006"
