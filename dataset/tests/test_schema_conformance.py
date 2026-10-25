"""
tests/test_schema_conformance.py - Automated tests for Pydantic v2 schema validation and contract constraints.
Tests valid data, invalid confidence, invalid checksum, invalid page/bounding-box data, and nullable confidence.
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.schemas import ExtractionResult, FieldEvidence, ProcessingMetadata, TableData, BoundingBox

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_extraction_result_serialization_roundtrip():
    """Verify ExtractionResult serializes to JSON and deserializes cleanly without data loss."""
    meta = ProcessingMetadata(
        total_pages=5,
        processed_pages=5,
        page_range="1-5",
        extraction_path="digital",
        digital_pages=[1, 2, 3, 4, 5],
        ocr_pages=[],
    )

    evidence = FieldEvidence(
        raw_value="1-46227285868",
        normalized_value="1-46227285868",
        page_number=1,
        bounding_box=[120.0, 72.5, 240.0, 84.0],
        confidence=None,  # Honest confidence: None for deterministic digital text
        extraction_method="digital",
        is_uncertain=False,
    )

    table = TableData(
        table_name="approved_intake",
        page_number=2,
        headers=["Programme", "Course", "Intake"],
        rows=[{"programme": "ENG", "course": "CSE", "intake": 60}],
    )

    result = ExtractionResult(
        document_id="DOC_REAL_003",
        source_file="real_documents/KGEC_AICTE_Approval_2026-27.pdf",
        sha256="cd44e07be8edccc5424eaf757614309a42392324976304dfb840de393a5a0767",
        document_type="aicte_eoa",
        classification_confidence=None,
        processing_status="SUCCESS",
        processing_metadata=meta,
        fields={"application_id": evidence},
        table_data=[table],
        warnings=[],
        errors=[],
    )

    json_str = result.to_json()
    data = json.loads(json_str)

    # Verify honest confidence serializes as null
    assert data["fields"]["application_id"]["confidence"] is None
    assert data["fields"]["application_id"]["extraction_method"] == "digital"
    assert data["classification_confidence"] is None

    # Deserialize back
    recovered = ExtractionResult.model_validate(data)
    assert recovered.document_id == "DOC_REAL_003"
    assert recovered.fields["application_id"].raw_value == "1-46227285868"
    assert recovered.fields["application_id"].confidence is None
    assert recovered.table_data[0].rows[0]["intake"] == 60


def test_nullable_confidence_preserved():
    """Verify confidence is explicitly nullable and None is never replaced with default values."""
    evidence = FieldEvidence(
        raw_value="Sample Text",
        page_number=1,
        confidence=None,
        extraction_method="digital",
    )
    assert evidence.confidence is None
    dumped = evidence.model_dump()
    assert dumped["confidence"] is None


def test_invalid_confidence_rejected():
    """Verify confidence outside [0.0, 1.0] raises ValidationError."""
    with pytest.raises(ValidationError):
        FieldEvidence(confidence=1.5)

    with pytest.raises(ValidationError):
        FieldEvidence(confidence=-0.1)

    with pytest.raises(ValidationError):
        meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="ocr")
        ExtractionResult(
            document_id="DOC_TEST",
            source_file="test.pdf",
            document_type="aicte_eoa",
            classification_confidence=1.05,
            processing_metadata=meta,
        )


def test_invalid_checksum_rejected():
    """Verify invalid SHA-256 (wrong length or non-hex) raises ValidationError."""
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")

    # Too short (63 chars)
    with pytest.raises(ValidationError):
        ExtractionResult(
            document_id="DOC_TEST",
            source_file="test.pdf",
            sha256="a" * 63,
            document_type="aicte_eoa",
            processing_metadata=meta,
        )

    # Too long (65 chars)
    with pytest.raises(ValidationError):
        ExtractionResult(
            document_id="DOC_TEST",
            source_file="test.pdf",
            sha256="a" * 65,
            document_type="aicte_eoa",
            processing_metadata=meta,
        )

    # Non-hex characters
    with pytest.raises(ValidationError):
        ExtractionResult(
            document_id="DOC_TEST",
            source_file="test.pdf",
            sha256="z" * 64,
            document_type="aicte_eoa",
            processing_metadata=meta,
        )


def test_invalid_page_number_rejected():
    """Verify page numbers < 1 raise ValidationError."""
    with pytest.raises(ValidationError):
        FieldEvidence(page_number=0)

    with pytest.raises(ValidationError):
        FieldEvidence(page_number=-2)

    with pytest.raises(ValidationError):
        TableData(table_name="test_tbl", page_number=0)


def test_invalid_bounding_box_rejected():
    """Verify malformed bounding box (wrong length, inverted coordinates, negative coordinates) raises ValidationError."""
    # Length not 4
    with pytest.raises(ValidationError):
        FieldEvidence(bounding_box=[10.0, 20.0, 30.0])

    # x0 > x1
    with pytest.raises(ValidationError):
        FieldEvidence(bounding_box=[100.0, 20.0, 50.0, 40.0])

    # y0 > y1
    with pytest.raises(ValidationError):
        FieldEvidence(bounding_box=[10.0, 200.0, 50.0, 40.0])

    # Negative coordinate
    with pytest.raises(ValidationError):
        FieldEvidence(bounding_box=[-5.0, 10.0, 50.0, 40.0])

    # BoundingBox class validation
    with pytest.raises(ValidationError):
        BoundingBox(x0=100.0, y0=10.0, x1=50.0, y1=20.0)


def test_example_contract_fixture_conforms():
    """Verify example_extraction_contract.json validates cleanly against ExtractionResult."""
    contract_path = PROJECT_ROOT / "test_cases" / "fixtures" / "example_extraction_contract.json"
    assert contract_path.exists(), f"Missing example contract: {contract_path}"

    with open(contract_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = ExtractionResult.model_validate(data)
    assert result.document_id == "SYNTH_DOC_CONTRACT_EXAMPLE"
    assert result.processing_metadata.extraction_path == "hybrid"
    assert len(result.fields) == 4
    assert result.fields["institution_name"].confidence is None
    assert result.fields["council_seal_text"].confidence == 0.42
    assert result.fields["council_seal_text"].is_uncertain is True
    assert len(result.table_data) == 1


def test_schema_validates_synthetic_fixtures():
    """Verify single-document synthetic test fixtures conform to ExtractionResult."""
    fixtures_dir = PROJECT_ROOT / "test_cases" / "fixtures"

    for json_file in fixtures_dir.glob("*.json"):
        # tc05, tc06 and tc07 are partial/cross-doc payloads; test full ExtractionResult fixtures
        if any(skip in json_file.name for skip in ["tc05", "tc06", "tc07"]):
            continue

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        try:
            model = ExtractionResult.model_validate(data)
            assert model.document_id is not None
        except Exception as exc:
            pytest.fail(f"Fixture {json_file.name} failed schema validation: {exc}")

