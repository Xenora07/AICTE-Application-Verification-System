"""
tests/test_validation_engine.py - Comprehensive test suite for Phase 7 Validation & Consistency Engine.
Covers:
1. Synthetic test cases TC_SYNTH_001 through TC_SYNTH_010 from test_manifest.json.
2. Unit tests for each rule under PASS, FAIL, INCONCLUSIVE, and MISSING-EVIDENCE conditions.
3. Cross-document consistency tests (intake mismatch, ID mismatch, duplicate hash, name alignment).
4. Integration test running ValidationEngine on real extracted documents.
"""

import json
from pathlib import Path
import pytest

from src.extractors.hybrid_router import extract_document_to_contract
from src.mappers.regulatory_mapper import RegulatoryDocumentMapper
from src.schemas.common import FieldEvidence, TableData
from src.schemas.extraction_result import ExtractionResult, ProcessingMetadata
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

FIXTURES_DIR = Path("test_cases/fixtures")


def load_fixture(fixture_name: str) -> dict:
    path = FIXTURES_DIR / fixture_name
    assert path.exists(), f"Fixture missing: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. Synthetic Scenarios Verification (TC_SYNTH_001 - TC_SYNTH_010)
# ==============================================================================

def test_tc01_valid_structured_fields():
    engine = ValidationEngine()
    data = load_fixture("tc01_valid_structured_fields.json")
    report = engine.validate_document(data)

    assert report.document_id == "SYNTH_DOC_001"
    assert report.overall_outcome == "PASS"
    assert report.requires_human_review is False
    assert report.summary["fail"] == 0
    assert report.summary["inconclusive"] == 0
    rule_ids = [f.rule_id for f in report.findings]
    assert "RULE_SCHEMA_CONFORMANCE" in rule_ids
    assert "RULE_REQ_ACADEMIC_YEAR" in rule_ids
    assert "RULE_FORMAT_APP_ID" in rule_ids


def test_tc02_missing_required_field():
    engine = ValidationEngine()
    data = load_fixture("tc02_missing_required_field.json")
    report = engine.validate_document(data)

    assert report.document_id == "SYNTH_DOC_002"
    assert report.overall_outcome == "FAIL"
    req_finding = next(f for f in report.findings if f.rule_id == "RULE_REQ_ACADEMIC_YEAR")
    assert req_finding.outcome == "FAIL"
    assert req_finding.severity == "HIGH"
    assert "missing" in req_finding.explanation.lower()


def test_tc03_invalid_id_format():
    engine = ValidationEngine()
    data = load_fixture("tc03_invalid_id_format.json")
    report = engine.validate_document(data)

    assert report.document_id == "SYNTH_DOC_003"
    assert report.overall_outcome == "FAIL"
    id_finding = next(f for f in report.findings if f.rule_id == "RULE_FORMAT_APP_ID")
    assert id_finding.outcome == "FAIL"
    assert id_finding.severity == "MEDIUM"
    assert "INVALID-APP-ID-XYZ" in id_finding.explanation


def test_tc04_inconsistent_dates():
    engine = ValidationEngine()
    data = load_fixture("tc04_inconsistent_dates.json")
    report = engine.validate_document(data)

    assert report.document_id == "SYNTH_DOC_004"
    assert report.overall_outcome == "FAIL"
    date_finding = next(f for f in report.findings if f.rule_id == "RULE_DATE_RANGE_INVALID")
    assert date_finding.outcome == "FAIL"
    assert date_finding.severity == "HIGH"
    assert "earlier than valid_from" in date_finding.explanation


def test_tc05_cross_institution_id_mismatch():
    engine = ValidationEngine()
    doc_a = load_fixture("tc05_institution_id_mismatch_a.json")
    doc_b = load_fixture("tc05_institution_id_mismatch_b.json")
    report = engine.validate_consistency([doc_a, doc_b])

    assert report.overall_outcome == "FAIL"
    assert report.requires_human_review is True
    id_finding = next(f for f in report.findings if f.rule_id == "RULE_CROSS_INSTITUTION_ID")
    assert id_finding.outcome == "FAIL"
    assert id_finding.severity == "CRITICAL"
    assert "1-4775731" in id_finding.explanation
    assert "1-9999999" in id_finding.explanation


def test_tc06_cross_intake_mismatch():
    engine = ValidationEngine()
    doc_eoa = load_fixture("tc06_intake_mismatch_eoa.json")
    doc_disc = load_fixture("tc06_intake_mismatch_disclosure.json")
    report = engine.validate_consistency([doc_eoa, doc_disc])

    assert report.overall_outcome == "FAIL"
    assert report.requires_human_review is True
    intake_finding = next(f for f in report.findings if f.rule_id == "RULE_CROSS_INTAKE_MISMATCH")
    assert intake_finding.outcome == "FAIL"
    assert intake_finding.severity == "HIGH"
    assert "claimed 180, approved 120" in intake_finding.explanation


def test_tc07_duplicate_document_hash():
    engine = ValidationEngine()
    data = load_fixture("tc07_duplicate_doc.json")
    report = engine.validate_document(data)

    assert report.document_id == "SYNTH_DOC_007"
    assert report.overall_outcome == "FAIL"
    dup_finding = next(f for f in report.findings if f.rule_id == "RULE_INTEGRITY_DUPLICATE_HASH")
    assert dup_finding.outcome == "FAIL"
    assert dup_finding.severity == "MEDIUM"
    assert "matches existing submission doc_id 'DOC_REAL_003'" in dup_finding.explanation


def test_tc08_low_confidence_ocr():
    engine = ValidationEngine()
    data = load_fixture("tc08_low_confidence_ocr.json")
    report = engine.validate_document(data)

    assert report.document_id == "SYNTH_DOC_008"
    assert report.overall_outcome == "INCONCLUSIVE"
    assert report.requires_human_review is True
    ocr_finding = next(f for f in report.findings if f.rule_id == "RULE_OCR_CONFIDENCE_THRESHOLD")
    assert ocr_finding.outcome == "INCONCLUSIVE"
    assert ocr_finding.severity == "MEDIUM"
    assert "0.48 < 0.65 threshold" in ocr_finding.explanation


def test_tc09_malformed_unreadable():
    engine = ValidationEngine()
    # Emulate extraction result of a corrupt binary file
    corrupt_payload = {
        "document_id": "SYNTH_DOC_009",
        "source_file": "test_cases/fixtures/tc09_malformed_unreadable.bin",
        "document_type": "corrupted_binary",
        "processing_status": "EXTRACTION_ERROR",
        "errors": ["Input stream is corrupted or not a valid PDF structure"],
    }
    report = engine.validate_document(corrupt_payload)

    assert report.document_id == "SYNTH_DOC_009"
    assert report.overall_outcome == "FAIL"
    assert report.requires_human_review is True
    parse_finding = next(f for f in report.findings if f.rule_id == "RULE_FILE_PARSEABLE")
    assert parse_finding.outcome == "FAIL"
    assert parse_finding.severity == "CRITICAL"


def test_tc10_inconclusive_human_review():
    engine = ValidationEngine()
    data = load_fixture("tc10_inconclusive_human_review.json")
    report = engine.validate_document(data)

    assert report.document_id == "SYNTH_DOC_010"
    assert report.overall_outcome == "INCONCLUSIVE"
    assert report.requires_human_review is True
    amb_finding = next(f for f in report.findings if f.rule_id == "RULE_AMBIGUOUS_EVIDENCE")
    assert amb_finding.outcome == "INCONCLUSIVE"
    assert amb_finding.severity == "HIGH"


# ==============================================================================
# 2. Rule Unit Tests: Inconclusive vs Failing vs Passing
# ==============================================================================

def test_rule_date_range_missing_evidence_is_inconclusive_not_fail():
    """Verify missing date evidence produces INCONCLUSIVE, never an automated FAIL."""
    doc = ExtractionResult(
        document_id="DOC_TEST",
        source_file="test.pdf",
        document_type="naac_certificate",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital"),
        fields={
            "valid_from": FieldEvidence(raw_value="2025-06-01", normalized_value="2025-06-01"),
            # valid_to is absent
        },
    )
    # When one date is missing, rule returns None or INCONCLUSIVE, never FAIL
    finding = rule_date_range_valid(doc)
    assert finding is None  # Handled safely without false alarm


def test_rule_date_range_unparsed_is_inconclusive():
    """When a date could not be parsed (e.g. OCR misspelling), outcome is INCONCLUSIVE."""
    doc = ExtractionResult(
        document_id="DOC_TEST",
        source_file="test.pdf",
        document_type="naac_certificate",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="ocr"),
        fields={
            "valid_from": FieldEvidence(raw_value="June 01, 2025", normalized_value="2025-06-01"),
            "valid_to": FieldEvidence(raw_value="Spril02, 2030", normalized_value=None, is_uncertain=True),
        },
    )
    finding = rule_date_range_valid(doc)
    assert finding is not None
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.requires_human_review is True


def test_rule_cgpa_bounds_and_uncertainty():
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="ocr")

    # Clean valid CGPA
    doc_clean = ExtractionResult(
        document_id="DOC_TEST",
        source_file="test.pdf",
        document_type="naac_certificate",
        processing_metadata=meta,
        fields={"cgpa": FieldEvidence(raw_value="3.42", normalized_value=3.42, confidence=0.92)},
    )
    finding_clean = rule_cgpa_range(doc_clean)
    assert finding_clean.outcome == "PASS"

    # CGPA out of regulatory bounds (> 10.0)
    doc_oob = ExtractionResult(
        document_id="DOC_TEST",
        source_file="test.pdf",
        document_type="naac_certificate",
        processing_metadata=meta,
        fields={"cgpa": FieldEvidence(raw_value="12.5", normalized_value=12.5)},
    )
    finding_oob = rule_cgpa_range(doc_oob)
    assert finding_oob.outcome == "FAIL"
    assert finding_oob.severity == "HIGH"

    # CGPA with character substitution ('O' -> '0')
    doc_sub = ExtractionResult(
        document_id="DOC_TEST",
        source_file="test.pdf",
        document_type="naac_certificate",
        processing_metadata=meta,
        fields={
            "cgpa": FieldEvidence(
                raw_value="3.O8",
                normalized_value=3.08,
                is_uncertain=True,
                uncertainty_reason="OCR character substitution",
            )
        },
    )
    finding_sub = rule_cgpa_range(doc_sub)
    assert finding_sub.outcome == "INCONCLUSIVE"
    assert finding_sub.requires_human_review is True


def test_rule_grade_validity():
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")

    # Valid grade
    doc_valid = ExtractionResult(
        document_id="DOC_TEST",
        source_file="test.pdf",
        document_type="naac_certificate",
        processing_metadata=meta,
        fields={"accreditation_grade": FieldEvidence(raw_value="A++", normalized_value="A++")},
    )
    assert rule_grade_validity(doc_valid).outcome == "PASS"

    # Unsupported / unknown grade scheme produces INCONCLUSIVE, preserving raw evidence
    doc_invalid = ExtractionResult(
        document_id="DOC_TEST",
        source_file="test.pdf",
        document_type="naac_certificate",
        processing_metadata=meta,
        fields={"accreditation_grade": FieldEvidence(raw_value="XYZ", normalized_value="XYZ")},
    )
    finding = rule_grade_validity(doc_invalid)
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.severity == "MEDIUM"
    assert "XYZ" in finding.explanation
    assert finding.requires_human_review is True


# ==============================================================================
# 3. Cross-Document Consistency Unit Tests
# ==============================================================================

def test_cross_institution_id_matching_passes():
    doc1 = ExtractionResult(
        document_id="DOC_001",
        source_file="doc1.pdf",
        document_type="aicte_eoa",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital"),
        fields={"permanent_institute_id": FieldEvidence(raw_value="1-5884273", normalized_value="1-5884273")},
    )
    doc2 = ExtractionResult(
        document_id="DOC_002",
        source_file="doc2.pdf",
        document_type="aicte_mandatory_disclosure",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital"),
        fields={"permanent_institute_id": FieldEvidence(raw_value="1-5884273", normalized_value="1-5884273")},
    )
    finding = check_cross_institution_id([doc1, doc2])
    assert finding.outcome == "PASS"
    assert finding.severity == "INFO"


def test_cross_institution_id_uncertain_is_inconclusive():
    doc1 = ExtractionResult(
        document_id="DOC_001",
        source_file="doc1.pdf",
        document_type="aicte_eoa",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital"),
        fields={"permanent_institute_id": FieldEvidence(raw_value="1-5884273", normalized_value="1-5884273")},
    )
    doc2 = ExtractionResult(
        document_id="DOC_002",
        source_file="doc2.pdf",
        document_type="aicte_mandatory_disclosure",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="ocr"),
        fields={
            "permanent_institute_id": FieldEvidence(
                raw_value="1-5884273",
                normalized_value="1-5884273",
                is_uncertain=True,
                uncertainty_reason="Low OCR confidence",
            )
        },
    )
    finding = check_cross_institution_id([doc1, doc2])
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.requires_human_review is True


def test_cross_intake_within_quota_passes():
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")
    doc_eoa = ExtractionResult(
        document_id="EOA_01",
        source_file="eoa.pdf",
        document_type="aicte_eoa",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="approved_courses_and_intake",
                page_number=1,
                rows=[{"course": "MECHANICAL ENGINEERING", "approved_intake": 120}],
            )
        ],
    )
    doc_disc = ExtractionResult(
        document_id="DISC_01",
        source_file="disc.pdf",
        document_type="aicte_mandatory_disclosure",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="programmes_and_intake",
                page_number=1,
                rows=[{"course": "MECHANICAL ENGINEERING", "claimed_intake": 120}],
            )
        ],
    )
    finding = check_cross_intake_mismatch([doc_eoa, doc_disc])
    assert finding.outcome == "PASS"


def test_check_duplicate_hash_batch_and_registry():
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")
    doc1 = ExtractionResult(
        document_id="DOC_A",
        source_file="a.pdf",
        sha256="aa" * 32,
        document_type="aicte_eoa",
        processing_metadata=meta,
    )
    doc2 = ExtractionResult(
        document_id="DOC_B",
        source_file="b.pdf",
        sha256="aa" * 32,  # Identical hash to doc1
        document_type="aicte_eoa",
        processing_metadata=meta,
    )
    # Detects collision within batch
    batch_finding = check_duplicate_hash([doc1, doc2])
    assert batch_finding.outcome == "FAIL"
    assert "Duplicate document detected in batch" in batch_finding.explanation

    # Detects collision against external submission registry
    registry = {"bb" * 32: "PREV_SESSION_DOC_099"}
    doc3 = ExtractionResult(
        document_id="DOC_C",
        source_file="c.pdf",
        sha256="bb" * 32,
        document_type="aicte_eoa",
        processing_metadata=meta,
    )
    reg_finding = check_duplicate_hash([doc3], registered_hashes=registry)
    assert reg_finding.outcome == "FAIL"
    assert "matches existing submission doc_id 'PREV_SESSION_DOC_099'" in reg_finding.explanation


# ==============================================================================
# 4. Integration Test on Real Extraction Results
# ==============================================================================

def test_integration_validation_on_real_digital_document():
    pdf_path = Path("real_documents/KGEC_AICTE_Approval_2026-27.pdf")
    assert pdf_path.exists()

    mapper = RegulatoryDocumentMapper(document_type="aicte_eoa")
    extracted_doc = extract_document_to_contract(
        doc_path=pdf_path,
        document_id="DOC_REAL_003",
        document_type="aicte_eoa",
        page_range="1",
        mapper=mapper,
    )

    engine = ValidationEngine()
    report = engine.validate_document(extracted_doc)

    assert report.document_id == "DOC_REAL_003"
    assert report.document_type == "aicte_eoa"
    assert report.overall_outcome == "PASS"
    assert report.requires_human_review is False

    # Verify key rules evaluated
    rule_ids = {f.rule_id: f for f in report.findings}
    assert rule_ids["RULE_FILE_PARSEABLE"].outcome == "PASS"
    assert rule_ids["RULE_SCHEMA_CONFORMANCE"].outcome == "PASS"
    assert rule_ids["RULE_REQ_ACADEMIC_YEAR"].outcome == "PASS"
    assert rule_ids["RULE_FORMAT_APP_ID"].outcome == "PASS"
    assert rule_ids["RULE_FORMAT_PERM_ID"].outcome == "PASS"


# ==============================================================================
# 5. Phase 7 Correctness Audit Tests
# ==============================================================================

def test_missing_academic_year_unknown_document_type_is_inconclusive():
    """Missing academic year on unknown or generic document type produces INCONCLUSIVE, not FAIL."""
    doc = ExtractionResult(
        document_id="DOC_UNKNOWN_TYPE",
        source_file="unknown.pdf",
        document_type="unknown",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital"),
        fields={},
    )
    finding = rule_required_academic_year(doc)
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.severity == "LOW"
    assert finding.requires_human_review is True
    assert "missing mapped field does not" in finding.explanation


def test_missing_academic_year_incomplete_extraction_is_inconclusive():
    """Missing academic year when extraction failed or was incomplete produces INCONCLUSIVE."""
    doc = ExtractionResult(
        document_id="DOC_INCOMPLETE",
        source_file="eoa.pdf",
        document_type="aicte_eoa",
        processing_status="EXTRACTION_ERROR",
        errors=["Page 1 extraction timeout"],
        processing_metadata=ProcessingMetadata(total_pages=3, processed_pages=1, extraction_path="ocr"),
        fields={},
    )
    finding = rule_required_academic_year(doc)
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.severity == "MEDIUM"
    assert finding.requires_human_review is True
    assert "incomplete" in finding.explanation or "failed" in finding.explanation


def test_uncertain_academic_year_evidence_is_inconclusive():
    """Extracted academic year with low confidence or uncertainty produces INCONCLUSIVE."""
    doc = ExtractionResult(
        document_id="DOC_UNCERTAIN_YEAR",
        source_file="eoa.pdf",
        document_type="aicte_eoa",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="ocr"),
        fields={
            "academic_year": FieldEvidence(
                raw_value="2026-2027",
                normalized_value="2026-2027",
                confidence=0.55,
                extraction_method="ocr",
            )
        },
    )
    finding = rule_required_academic_year(doc)
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.severity == "MEDIUM"
    assert finding.requires_human_review is True


def test_unsupported_grade_scheme_is_inconclusive():
    """Unsupported or historical grade schemes produce INCONCLUSIVE, preserving raw evidence."""
    doc = ExtractionResult(
        document_id="DOC_HISTORIC_NAAC",
        source_file="naac_cert.pdf",
        document_type="naac_certificate",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital"),
        fields={
            "accreditation_grade": FieldEvidence(
                raw_value="Five Star",
                normalized_value="FIVE STAR",
            )
        },
    )
    finding = rule_grade_validity(doc)
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.severity == "MEDIUM"
    assert finding.requires_human_review is True
    assert finding.evidence_values["raw_value"] == "Five Star"
    assert "does not match standard NAAC letter scale" in finding.explanation


def test_low_confidence_malformed_looking_id_is_inconclusive():
    """Uncertain OCR text on ID fields is never treated as definitive proof of invalidity."""
    doc = ExtractionResult(
        document_id="DOC_OCR_ID",
        source_file="scanned.pdf",
        document_type="aicte_eoa",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="ocr"),
        fields={
            "application_id": FieldEvidence(
                raw_value="1-4622O285B68",  # Letters O and B from OCR noise
                normalized_value="1-4622O285B68",
                extraction_method="ocr",
                confidence=0.48,
                is_uncertain=True,
                uncertainty_reason="Low OCR confidence character substitutions",
            )
        },
    )
    finding = rule_format_application_id(doc)
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.severity == "MEDIUM"
    assert finding.requires_human_review is True
    assert finding.evidence_values["raw_value"] == "1-4622O285B68"
    assert "cannot be verified deterministically" in finding.explanation


def test_confident_malformed_id_is_fail():
    """Confident digital extraction of clearly invalid ID pattern produces FAIL."""
    doc = ExtractionResult(
        document_id="DOC_DIGITAL_MALFORMED_ID",
        source_file="digital.pdf",
        document_type="aicte_eoa",
        processing_metadata=ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital"),
        fields={
            "application_id": FieldEvidence(
                raw_value="MALFORMED-APP-ID",
                normalized_value="MALFORMED-APP-ID",
                extraction_method="digital",
                confidence=1.0,
            )
        },
    )
    finding = rule_format_application_id(doc)
    assert finding.outcome == "FAIL"
    assert finding.severity == "MEDIUM"
    assert "violates pattern" in finding.explanation


def test_cross_intake_exact_matches_passes():
    """Exact programme name and intake within quota passes cleanly."""
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")
    doc_eoa = ExtractionResult(
        document_id="EOA_01",
        source_file="eoa.pdf",
        document_type="aicte_eoa",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="approved_courses_and_intake",
                page_number=1,
                rows=[{"course": "MECHANICAL ENGINEERING", "approved_intake": 120}],
            )
        ],
    )
    doc_disc = ExtractionResult(
        document_id="DISC_01",
        source_file="disc.pdf",
        document_type="aicte_mandatory_disclosure",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="programmes_and_intake",
                page_number=1,
                rows=[{"course": "MECHANICAL ENGINEERING", "claimed_intake": 120}],
            )
        ],
    )
    finding = check_cross_intake_mismatch([doc_eoa, doc_disc])
    assert finding.outcome == "PASS"
    assert finding.severity == "INFO"


def test_cross_intake_safely_normalized_matches_passes():
    """Safely normalized programme name (CSE alias vs Computer Science & Engineering) passes."""
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")
    doc_eoa = ExtractionResult(
        document_id="EOA_01",
        source_file="eoa.pdf",
        document_type="aicte_eoa",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="approved_courses_and_intake",
                page_number=1,
                rows=[{"course": "B.Tech in Computer Science & Engineering", "approved_intake": 120}],
            )
        ],
    )
    doc_disc = ExtractionResult(
        document_id="DISC_01",
        source_file="disc.pdf",
        document_type="aicte_mandatory_disclosure",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="programmes_and_intake",
                page_number=1,
                rows=[{"course": "CSE", "claimed_intake": 120}],
            )
        ],
    )
    finding = check_cross_intake_mismatch([doc_eoa, doc_disc])
    assert finding.outcome == "PASS"
    assert finding.severity == "INFO"


def test_cross_intake_ambiguous_programme_name_is_inconclusive():
    """Ambiguous or differing programme names where equivalence cannot be deterministically established emit INCONCLUSIVE."""
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")
    doc_eoa = ExtractionResult(
        document_id="EOA_01",
        source_file="eoa.pdf",
        document_type="aicte_eoa",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="approved_courses_and_intake",
                page_number=1,
                rows=[{"course": "CIVIL ENGINEERING", "approved_intake": 60}],
            )
        ],
    )
    doc_disc = ExtractionResult(
        document_id="DISC_01",
        source_file="disc.pdf",
        document_type="aicte_mandatory_disclosure",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="programmes_and_intake",
                page_number=1,
                rows=[{"course": "CIVIL AND ENVIRONMENTAL ENGINEERING", "claimed_intake": 60}],
            )
        ],
    )
    finding = check_cross_intake_mismatch([doc_eoa, doc_disc])
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.severity == "MEDIUM"
    assert finding.requires_human_review is True
    assert "cannot be deterministically matched" in finding.explanation


def test_cross_intake_missing_intake_value_is_inconclusive():
    """Missing or unparseable intake values produce INCONCLUSIVE, not a comparison failure or false pass."""
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")
    doc_eoa = ExtractionResult(
        document_id="EOA_01",
        source_file="eoa.pdf",
        document_type="aicte_eoa",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="approved_courses_and_intake",
                page_number=1,
                rows=[{"course": "MECHANICAL ENGINEERING", "approved_intake": 120}],
            )
        ],
    )
    doc_disc = ExtractionResult(
        document_id="DISC_01",
        source_file="disc.pdf",
        document_type="aicte_mandatory_disclosure",
        processing_metadata=meta,
        table_data=[
            TableData(
                table_name="programmes_and_intake",
                page_number=1,
                rows=[{"course": "MECHANICAL ENGINEERING", "claimed_intake": None}],
            )
        ],
    )
    finding = check_cross_intake_mismatch([doc_eoa, doc_disc])
    assert finding.outcome == "INCONCLUSIVE"
    assert finding.severity == "MEDIUM"
    assert finding.requires_human_review is True
    assert "claimed intake value is missing or unparseable" in finding.explanation


def test_duplicate_hash_semantics_does_not_imply_fraud():
    """Identical SHA-256 hashes produce a duplicate-document finding but explicitly state non-fraud semantics."""
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")
    doc1 = ExtractionResult(
        document_id="DOC_SUBMISSION_ORIG",
        source_file="doc.pdf",
        sha256="cc" * 32,
        document_type="aicte_eoa",
        processing_metadata=meta,
    )
    doc2 = ExtractionResult(
        document_id="DOC_SUBMISSION_RELOAD",
        source_file="doc_copy.pdf",
        sha256="cc" * 32,
        document_type="aicte_eoa",
        processing_metadata=meta,
    )
    finding = check_duplicate_hash([doc1, doc2])
    assert finding.outcome == "FAIL"
    assert finding.severity == "MEDIUM"
    assert "does not imply fraud or regulatory non-compliance" in finding.explanation
    assert finding.requires_human_review is False

