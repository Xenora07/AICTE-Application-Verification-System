"""
backend/tests/test_api_integration.py - Integration Test Suite for Phase 9 FastAPI Orchestration.
Tests health checks, upload validation, extraction pipeline, privacy masking,
authenticity detection, cross-document checks, and synthetic scenario execution.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.common.constants import (
    FIXTURES_DIR,
    REAL_DOCS_DIR,
)

client = TestClient(app)

SAMPLE_PDF = REAL_DOCS_DIR / "KGEC_AICTE_Approval_2026-27.pdf"
CORRUPT_BIN = FIXTURES_DIR / "tc09_malformed_unreadable.bin"


def test_root_health():
    """Verify /health returns 200 OK and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_v1_health():
    """Verify /api/v1/health returns detailed subsystem information."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "dataset_documents_available" in data
    assert "synthetic_test_cases_available" in data
    assert data["synthetic_test_cases_available"] == 10


def test_dataset_manifest_query():
    """Verify /api/v1/dataset/manifest returns the 18 cataloged documents."""
    response = client.get("/api/v1/dataset/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["total_documents"] >= 17
    assert len(data["documents"]) >= 17
    assert any(d["doc_id"] == "DOC_REAL_003" for d in data["documents"])


def test_list_synthetic_test_cases():
    """Verify /api/v1/test-cases returns all 10 synthetic test scenarios."""
    response = client.get("/api/v1/test-cases")
    assert response.status_code == 200
    data = response.json()
    assert data["total_test_cases"] == 10
    test_ids = [tc["test_id"] for tc in data["test_cases"]]
    assert "TC_SYNTH_001" in test_ids
    assert "TC_SYNTH_005" in test_ids
    assert "TC_SYNTH_010" in test_ids


def test_upload_invalid_extension():
    """Verify upload rejects non-PDF files with 400 Bad Request."""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_empty_file():
    """Verify upload rejects 0-byte files with 400 Bad Request."""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_upload_corrupt_binary():
    """Verify corrupt stream produces structured failure response instead of 500 error."""
    assert CORRUPT_BIN.exists()
    with open(CORRUPT_BIN, "rb") as f:
        content = f.read()

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("corrupt.pdf", content, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["processing_status"] == "EXTRACTION_ERROR"
    assert data["reviewer_summary"]["overall_status"] in ("ACTION_REQUIRED", "NEEDS_HUMAN_REVIEW")
    assert any(f["rule_id"] in ("AUTH_FORMAT_HEADER", "AUTH_STRUCTURAL_CORRUPT") for f in data["normalized_findings"])


def test_upload_valid_pdf_end_to_end():
    """Verify upload of real AICTE approval letter executes full pipeline cleanly."""
    assert SAMPLE_PDF.exists()
    with open(SAMPLE_PDF, "rb") as f:
        pdf_bytes = f.read()

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("KGEC_AICTE_Approval_2026-27.pdf", pdf_bytes, "application/pdf")},
        data={"document_type": "aicte_eoa", "enable_privacy_masking": "true"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["document_type"] == "aicte_eoa"
    assert data["processing_status"] in ("SUCCESS", "SUCCESS_WITH_WARNINGS", "SUCCESS_WITH_UNCERTAINTY")
    assert "application_id" in data["extracted_fields"]
    assert "institution_name" in data["extracted_fields"]

    # Verify Reviewer Summary structure
    summary = data["reviewer_summary"]
    assert summary["total_rules_evaluated"] > 0
    assert summary["passed_rules"] > 0
    assert summary["overall_status"] in ("VERIFIED", "NEEDS_HUMAN_REVIEW")


def test_verify_dataset_sample_endpoint():
    """Verify /api/v1/dataset/verify-sample/DOC_REAL_003 processes directly from disk."""
    response = client.post("/api/v1/dataset/verify-sample/DOC_REAL_003")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "DOC_REAL_003"
    assert data["document_type"] == "aicte_eoa"
    assert len(data["normalized_findings"]) > 0


def test_execute_synthetic_test_case_tc01():
    """Verify execution of TC_SYNTH_001 (Valid structured fields)."""
    response = client.post("/api/v1/test-cases/execute/TC_SYNTH_001")
    assert response.status_code == 200
    data = response.json()
    assert data["test_id"] == "TC_SYNTH_001"
    assert data["actual_outcome"] == "PASS"
    assert data["passed_expected_scenario"] is True


def test_execute_synthetic_test_case_tc05_cross_document():
    """Verify execution of TC_SYNTH_005 (Institution ID mismatch across documents)."""
    response = client.post("/api/v1/test-cases/execute/TC_SYNTH_005")
    assert response.status_code == 200
    data = response.json()
    assert data["test_id"] == "TC_SYNTH_005"
    assert data["actual_outcome"] in ("FAIL", "INCONCLUSIVE")
    assert data["passed_expected_scenario"] is True
    assert any(f["rule_id"] == "RULE_CROSS_INSTITUTION_ID" for f in data["normalized_findings"])
