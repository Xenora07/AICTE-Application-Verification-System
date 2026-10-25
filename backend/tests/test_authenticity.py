"""
backend/tests/test_authenticity.py - Comprehensive Unit Tests for Person 3 Authenticity & Anomaly Engine.

Covers:
1. Valid and unreadable files.
2. Stable SHA-256 calculation for identical bytes.
3. Different hashes for different bytes.
4. Valid PDFs with missing or unusual metadata (inverted dates, graphic software).
5. Malformed PDFs and empty files.
6. Graceful handling of unsupported file types.
7. Correct finding outcome, severity, explanation, and human-review indication.
8. Duplicate-detection reuse without duplicate findings (RULE_INTEGRITY_DUPLICATE_HASH).
9. Integration with real dataset PDFs.
"""

from pathlib import Path
import pytest

from backend.security.authenticity import (
    DocumentAuthenticityReport,
    DuplicateHashRegistry,
    assess_document_authenticity,
    compute_file_sha256,
    inspect_file_structure,
    inspect_pdf_metadata,
    parse_pdf_date,
    verify_duplicate_via_validator,
)
from src.schemas.extraction_result import ExtractionResult, ProcessingMetadata

REAL_DOC_PATH = Path("dataset/real_documents/KGEC_AICTE_Approval_2026-27.pdf")


# ==============================================================================
# 1. SHA-256 Checksum Calculation Tests
# ==============================================================================


def test_sha256_stability():
    """Verify identical bytes yield identical lowercase 64-char SHA-256 hashes."""
    data = b"Sample AICTE verification document content 2026."
    hash1 = compute_file_sha256(data)
    hash2 = compute_file_sha256(data)
    assert hash1 == hash2
    assert len(hash1) == 64
    assert hash1 == hash1.lower()


def test_sha256_different_bytes():
    """Verify different bytes yield distinct hashes."""
    hash_a = compute_file_sha256(b"Document Version A")
    hash_b = compute_file_sha256(b"Document Version B")
    assert hash_a != hash_b


def test_sha256_unreadable_file_handling():
    """Verify FileNotFoundError on non-existent file."""
    with pytest.raises(FileNotFoundError):
        compute_file_sha256("non_existent_file_xyz_123.pdf")


# ==============================================================================
# 2. Structural & Format Verification Tests
# ==============================================================================


def test_empty_file_detection():
    """Verify 0-byte file produces RULE_AUTH_EMPTY_FILE with outcome FAIL and HIGH severity."""
    is_valid, findings = inspect_file_structure(b"", document_id="DOC_EMPTY_001")
    assert is_valid is False
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "RULE_AUTH_EMPTY_FILE"
    assert f.outcome == "FAIL"
    assert f.severity == "HIGH"
    assert f.requires_human_review is True


def test_unsupported_or_corrupt_file():
    """Verify non-PDF file (missing %PDF- header) produces RULE_AUTH_UNSUPPORTED_OR_CORRUPT."""
    corrupt_bytes = b"This is just a plain text file, not a PDF document."
    is_valid, findings = inspect_file_structure(corrupt_bytes, document_id="DOC_TEXT_001")
    assert is_valid is False
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "RULE_AUTH_UNSUPPORTED_OR_CORRUPT"
    assert f.outcome == "FAIL"
    assert f.severity == "HIGH"
    assert f.requires_human_review is True


def test_missing_eof_marker():
    """Verify PDF with valid %PDF- header but missing %%EOF produces RULE_AUTH_MALFORMED_STRUCTURE."""
    truncated_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    is_valid, findings = inspect_file_structure(truncated_pdf, document_id="DOC_TRUNC_001")
    assert is_valid is True  # Can attempt partial read
    f = next((x for x in findings if x.rule_id == "RULE_AUTH_MALFORMED_STRUCTURE"), None)
    assert f is not None
    assert f.outcome == "INCONCLUSIVE"
    assert f.severity == "MEDIUM"
    assert f.requires_human_review is True


# ==============================================================================
# 3. PDF Metadata & Anomaly Detection Tests
# ==============================================================================


def test_parse_pdf_date():
    """Verify PDF date string parsing."""
    parsed = parse_pdf_date("D:20250515094852+05'30'")
    assert parsed is not None
    assert parsed.year == 2025
    assert parsed.month == 5
    assert parsed.day == 15
    assert parsed.hour == 9

    assert parse_pdf_date("") is None
    assert parse_pdf_date(None) is None
    assert parse_pdf_date("invalid-date") is None


def test_clean_real_pdf_metadata():
    """Verify real AICTE PDF metadata inspection passes cleanly."""
    assert REAL_DOC_PATH.exists(), f"Missing real PDF fixture: {REAL_DOC_PATH}"
    report = assess_document_authenticity(REAL_DOC_PATH, document_id="DOC_REAL_003")

    assert report.document_id == "DOC_REAL_003"
    assert report.is_valid_pdf is True
    assert report.sha256 is not None
    assert len(report.sha256) == 64
    assert report.metadata_summary["page_count"] == 5
    assert report.metadata_summary["producer"] == "Oracle Analytics Publisher"
    assert report.overall_outcome == "PASS"
    assert report.requires_human_review is False


def test_pdf_metadata_graphic_tool_anomaly():
    """Verify Canva/Photoshop in metadata triggers RULE_AUTH_PRODUCER_ANOMALY with INCONCLUSIVE."""
    # Synthetic minimal PDF bytes with Canva in producer
    pdf_with_canva = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"4 0 obj\n<< /Producer (Canva PDF Renderer) /Creator (Canva Studio) >>\nendobj\n"
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000185 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R /Info 4 0 R >>\nstartxref\n260\n%%EOF\n"
    )

    findings, summary = inspect_pdf_metadata(pdf_with_canva, document_id="DOC_CANVA_001")
    canva_finding = next((f for f in findings if f.rule_id == "RULE_AUTH_PRODUCER_ANOMALY"), None)
    assert canva_finding is not None
    assert canva_finding.outcome == "INCONCLUSIVE"
    assert canva_finding.severity == "LOW"
    assert canva_finding.requires_human_review is True
    assert "Canva" in canva_finding.explanation
    # Must NOT claim fraud
    assert "not proof of tampering" in canva_finding.explanation


def test_pdf_metadata_inverted_timestamps():
    """Verify ModDate earlier than CreationDate triggers RULE_AUTH_TIMESTAMP_INVERSION."""
    pdf_inverted_dates = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"4 0 obj\n<< /CreationDate (D:20260101120000) /ModDate (D:20240101120000) /Producer (Test Engine) >>\nendobj\n"
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000185 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R /Info 4 0 R >>\nstartxref\n290\n%%EOF\n"
    )

    findings, summary = inspect_pdf_metadata(pdf_inverted_dates, document_id="DOC_INVERT_001")
    invert_finding = next((f for f in findings if f.rule_id == "RULE_AUTH_TIMESTAMP_INVERSION"), None)
    assert invert_finding is not None
    assert invert_finding.outcome == "INCONCLUSIVE"
    assert invert_finding.severity == "MEDIUM"
    assert invert_finding.requires_human_review is True


# ==============================================================================
# 4. Duplicate Detection Reuse Tests
# ==============================================================================


def test_duplicate_detection_registry():
    """Verify duplicate detection registers and matches identical SHA-256 hashes."""
    reg = DuplicateHashRegistry()
    test_hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"

    # First document: registers cleanly
    finding1 = reg.check_duplicate(test_hash, "DOC_ORIGINAL_001")
    assert finding1 is None

    # Same document re-checked: no duplicate finding against self
    finding_self = reg.check_duplicate(test_hash, "DOC_ORIGINAL_001")
    assert finding_self is None

    # Second document with identical hash: triggers RULE_INTEGRITY_DUPLICATE_HASH
    finding_dup = reg.check_duplicate(test_hash, "DOC_DUPLICATE_002")
    assert finding_dup is not None
    assert finding_dup.rule_id == "RULE_INTEGRITY_DUPLICATE_HASH"
    assert finding_dup.outcome == "FAIL"
    assert finding_dup.severity == "MEDIUM"
    assert "DOC_ORIGINAL_001" in finding_dup.explanation
    # Semantics: identical re-submission, not proof of fraud
    assert "does not imply fraud" in finding_dup.explanation


def test_verify_duplicate_via_validator():
    """Verify delegation to Person 2's check_duplicate_hash validator."""
    meta = ProcessingMetadata(total_pages=1, processed_pages=1, extraction_path="digital")
    doc_a = ExtractionResult(
        document_id="DOC_A",
        source_file="real_documents/a.pdf",
        sha256="1111111111111111111111111111111111111111111111111111111111111111",
        document_type="aicte_eoa",
        processing_metadata=meta,
    )
    doc_b = ExtractionResult(
        document_id="DOC_B",
        source_file="real_documents/b.pdf",
        sha256="1111111111111111111111111111111111111111111111111111111111111111",
        document_type="aicte_eoa",
        processing_metadata=meta,
    )

    finding = verify_duplicate_via_validator([doc_a, doc_b])
    assert finding is not None
    assert finding.rule_id == "RULE_INTEGRITY_DUPLICATE_HASH"
    assert finding.outcome == "FAIL"
    assert finding.severity == "MEDIUM"


# ==============================================================================
# 5. Full Assessment Entrypoint Tests
# ==============================================================================


def test_assess_document_authenticity_missing_file():
    """Verify graceful handling when file does not exist on disk."""
    report = assess_document_authenticity("missing_file.pdf", document_id="DOC_MISSING")
    assert report.document_id == "DOC_MISSING"
    assert report.overall_outcome == "FAIL"
    assert report.is_valid_pdf is False
    assert report.requires_human_review is True
    assert any(f.rule_id == "RULE_FILE_PARSEABLE" for f in report.findings)


def test_assess_document_authenticity_with_duplicate_registry():
    """Verify assessment attaches duplicate finding when hash is pre-registered."""
    assert REAL_DOC_PATH.exists()
    real_sha = compute_file_sha256(REAL_DOC_PATH)

    registry = {real_sha: "DOC_PREVIOUS_SESSION_001"}
    report = assess_document_authenticity(
        REAL_DOC_PATH,
        document_id="DOC_NEW_SUBMISSION_002",
        registered_hashes=registry,
    )

    assert report.document_id == "DOC_NEW_SUBMISSION_002"
    assert report.sha256 == real_sha
    dup_finding = next((f for f in report.findings if f.rule_id == "RULE_INTEGRITY_DUPLICATE_HASH"), None)
    assert dup_finding is not None
    assert dup_finding.outcome == "FAIL"
    assert dup_finding.severity == "MEDIUM"
