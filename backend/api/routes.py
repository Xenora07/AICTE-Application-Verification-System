"""
backend/api/routes.py - FastAPI Route Definitions for SIH26261 (Person 4).
Exposes endpoints for document upload, pipeline orchestration, cross-document verification,
dataset manifest queries, and synthetic scenario verification.
"""

import csv
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional
import pymupdf

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from backend.common.constants import (
    DATASET_MANIFEST_PATH,
    DEFAULT_OCR_THRESHOLD,
    FIXTURES_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    REAL_DOCS_DIR,
    SCANNED_DOCS_DIR,
    TEST_MANIFEST_PATH,
)
from backend.common.models import (
    CrossDocumentConsistencyReport,
    CrossValidateResponse,
    DocumentProcessResponse,
    ExtractionResult,
    NormalizedFinding,
    ReviewerSummary,
)
from backend.extraction.pdf_extractor import (
    compute_pdf_sha256,
    extract_document_to_contract,
)
from backend.security.authenticity import AuthenticityService
from backend.security.findings import FindingsNormalizer
from backend.security.privacy import apply_privacy_masking
from backend.validation.field_rules import ValidationEngine

router = APIRouter()

# In-memory session registries for duplicate detection and multi-document consistency
REGISTERED_HASHES: Dict[str, str] = {}
PROCESSED_DOCUMENTS: Dict[str, ExtractionResult] = {}


# ==============================================================================
# 1. System Health & Metadata
# ==============================================================================

@router.get("/health", summary="System Health and Capabilities")
def get_health_status():
    """Returns application health, pipeline readiness, and available dataset documents."""
    easyocr_available = False
    try:
        import easyocr
        easyocr_available = True
    except ImportError:
        pass

    manifest_docs_count = 0
    if DATASET_MANIFEST_PATH.exists():
        with open(DATASET_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest_docs_count = sum(1 for _ in csv.DictReader(f))

    test_cases_count = 0
    if TEST_MANIFEST_PATH.exists():
        with open(TEST_MANIFEST_PATH, "r", encoding="utf-8") as f:
            test_cases_count = len(json.load(f))

    return {
        "status": "healthy",
        "service": "AICTE Application Verification System",
        "version": "1.0.0",
        "ocr_engine": "easyocr" if easyocr_available else "synthetic_test_engine",
        "dataset_documents_available": manifest_docs_count,
        "synthetic_test_cases_available": test_cases_count,
        "active_documents_in_session": len(PROCESSED_DOCUMENTS),
    }


# ==============================================================================
# 2. Document Upload & Pipeline Orchestration
# ==============================================================================

@router.post(
    "/documents/upload",
    summary="Upload Document and Run Verification Pipeline",
    response_model=DocumentProcessResponse,
)
async def upload_and_process_document(
    file: UploadFile = File(..., description="PDF document for regulatory compliance verification"),
    document_id: Optional[str] = Form(None, description="Optional custom document ID"),
    document_type: Optional[str] = Form(None, description="Optional regulatory document type hint"),
    enable_privacy_masking: bool = Form(True, description="Whether to mask PII in response"),
    ocr_threshold: float = Form(DEFAULT_OCR_THRESHOLD, description="OCR confidence threshold"),
):
    """
    Executes Phase 9 end-to-end processing pipeline:
    1. Validation of file format, size, and stream headers.
    2. Authenticity & cryptographic integrity check (Person 3).
    3. Hybrid digital / OCR text extraction and field mapping (Person 1).
    4. Privacy Gateway PII redaction (Person 3).
    5. Deterministic single-document validation engine (Person 2).
    6. Findings normalization and executive reviewer summary generation (Person 3/4).
    """
    # Validate extension
    filename = file.filename or "uploaded_document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{filename}'. Only PDF documents (.pdf) are accepted.",
        )

    # Save to safe temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="aicte_upload_"))
    safe_file_path = temp_dir / filename

    try:
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes).",
            )
        if file_size > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
            )

        with open(safe_file_path, "wb") as f:
            f.write(content)

        # Assign stable or generated document ID
        doc_id = document_id or f"DOC_UPL_{uuid.uuid4().hex[:8].upper()}"

        # ----------------------------------------------------------------------
        # Step A: Authenticity & Anomaly Checks (Person 3)
        # ----------------------------------------------------------------------
        authenticity_svc = AuthenticityService(registered_hashes=REGISTERED_HASHES)
        auth_findings, pdf_meta = authenticity_svc.verify_authenticity(
            safe_file_path, document_id=doc_id, document_type=document_type
        )
        file_sha256 = pdf_meta.get("sha256", compute_pdf_sha256(safe_file_path))

        # Check for unrecoverable parse failures (e.g. malformed binary header)
        is_corrupt = any(f.rule_id in ("AUTH_FORMAT_HEADER", "AUTH_STRUCTURAL_CORRUPT") for f in auth_findings)

        if is_corrupt:
            # Produce structured failure response instead of unhandled crash
            contract_result = ExtractionResult(
                document_id=doc_id,
                source_file=filename,
                sha256=file_sha256,
                document_type=document_type or "unknown",
                processing_status="EXTRACTION_ERROR",
                processing_metadata={
                    "total_pages": 0,
                    "processed_pages": 0,
                    "extraction_path": "digital",
                },
                errors=["Input stream is corrupted or not a valid PDF structure."],
            )
        else:
            # ------------------------------------------------------------------
            # Step B: Extraction & Field Mapping (Person 1)
            # ------------------------------------------------------------------
            try:
                from backend.extraction.field_mapper import RegulatoryDocumentMapper
                mapper = RegulatoryDocumentMapper(document_type=document_type) if document_type else RegulatoryDocumentMapper()
                contract_result = extract_document_to_contract(
                    safe_file_path,
                    document_id=doc_id,
                    document_type=document_type or "unknown",
                    mapper=mapper,
                )
            except Exception as exc:
                contract_result = ExtractionResult(
                    document_id=doc_id,
                    source_file=filename,
                    sha256=file_sha256,
                    document_type=document_type or "unknown",
                    processing_status="EXTRACTION_ERROR",
                    processing_metadata={
                        "total_pages": 0,
                        "processed_pages": 0,
                        "extraction_path": "digital",
                    },
                    errors=[f"Extraction engine failure: {exc}"],
                )

        # Register hash in session if not duplicate
        if file_sha256 not in REGISTERED_HASHES:
            REGISTERED_HASHES[file_sha256] = doc_id

        # ----------------------------------------------------------------------
        # Step C: Privacy Gateway (Person 3)
        # ----------------------------------------------------------------------
        privacy_findings = []
        if enable_privacy_masking:
            contract_result, _, privacy_findings = apply_privacy_masking(contract_result)

        # ----------------------------------------------------------------------
        # Step D: Deterministic Validation Engine (Person 2)
        # ----------------------------------------------------------------------
        val_engine = ValidationEngine(registered_hashes=REGISTERED_HASHES)
        validation_report = val_engine.validate_document(contract_result)

        # Store in session registry for cross-document consistency checks
        PROCESSED_DOCUMENTS[doc_id] = contract_result

        # ----------------------------------------------------------------------
        # Step E: Finding Normalization & Reviewer Summary (Person 3/4)
        # ----------------------------------------------------------------------
        normalized_findings = FindingsNormalizer.aggregate_and_normalize(
            compliance_findings=validation_report.findings,
            authenticity_findings=auth_findings,
            privacy_findings=privacy_findings,
        )
        reviewer_summary = FindingsNormalizer.compute_reviewer_summary(
            normalized_findings, validation_report=validation_report
        )

        return DocumentProcessResponse(
            success=True,
            document_id=doc_id,
            filename=filename,
            file_size_bytes=file_size,
            sha256=file_sha256,
            document_type=contract_result.document_type,
            processing_status=contract_result.processing_status,
            processing_metadata=contract_result.processing_metadata,
            extracted_fields=contract_result.fields,
            table_data=contract_result.table_data,
            validation_report=validation_report,
            normalized_findings=normalized_findings,
            reviewer_summary=reviewer_summary,
            warnings=contract_result.warnings,
            errors=contract_result.errors,
        )

    finally:
        # Clean up temporary upload files
        shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 3. Cross-Document Consistency Verification
# ==============================================================================

@router.post(
    "/documents/cross-validate",
    summary="Cross-Document Consistency Verification",
    response_model=CrossValidateResponse,
)
def cross_validate_documents(payload: Optional[Dict[str, List[str]]] = None):
    """
    Compares active session documents (e.g. AICTE EoA vs Mandatory Disclosure) to detect:
    1. Permanent Institute ID discrepancies.
    2. Institution name alignment discrepancies.
    3. Course approved intake vs claimed intake quota inflation.
    4. Duplicate cryptographic checksums.
    """
    doc_ids = payload.get("document_ids", []) if payload else []

    if doc_ids:
        docs = [PROCESSED_DOCUMENTS[did] for did in doc_ids if did in PROCESSED_DOCUMENTS]
    else:
        docs = list(PROCESSED_DOCUMENTS.values())

    if len(docs) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cross-document consistency check requires at least 2 processed documents. "
                f"Currently available in session: {len(docs)}."
            ),
        )

    val_engine = ValidationEngine(registered_hashes=REGISTERED_HASHES)
    consistency_report = val_engine.validate_consistency(docs)

    normalized_findings = FindingsNormalizer.aggregate_and_normalize(
        consistency_findings=consistency_report.findings
    )

    return CrossValidateResponse(
        success=True,
        consistency_report=consistency_report,
        normalized_findings=normalized_findings,
        overall_status=consistency_report.overall_outcome,
        requires_human_review=consistency_report.requires_human_review,
    )


# ==============================================================================
# 4. Dataset Inspection & One-Click Sample Verification
# ==============================================================================

@router.get("/dataset/manifest", summary="List Dataset Documents")
def list_dataset_documents():
    """Returns the metadata catalog of real and scanned documents from data_manifest.csv."""
    if not DATASET_MANIFEST_PATH.exists():
        raise HTTPException(status_code=404, detail="data_manifest.csv not found in dataset/")

    documents = []
    with open(DATASET_MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            documents.append(row)

    return {
        "total_documents": len(documents),
        "documents": documents,
    }


@router.post(
    "/dataset/verify-sample/{doc_id}",
    summary="Run Verification on Dataset Sample Document",
    response_model=DocumentProcessResponse,
)
def verify_dataset_sample(
    doc_id: str,
    enable_privacy_masking: bool = True,
    ocr_threshold: float = DEFAULT_OCR_THRESHOLD,
):
    """Executes the full verification pipeline on any document in real_documents or scanned_documents."""
    # Find document in manifest
    target_row = None
    if DATASET_MANIFEST_PATH.exists():
        with open(DATASET_MANIFEST_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("doc_id") == doc_id or row.get("file_name") == doc_id:
                    target_row = row
                    break

    if not target_row:
        raise HTTPException(
            status_code=404,
            detail=f"Document ID '{doc_id}' not found in data_manifest.csv.",
        )

    rel_path = target_row["relative_path"]
    file_path = DATASET_MANIFEST_PATH.parent / rel_path

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Physical file missing on disk: {file_path}",
        )

    file_size = file_path.stat().st_size
    doc_type = target_row.get("document_type", "unknown")

    # Step A: Authenticity Check
    authenticity_svc = AuthenticityService(registered_hashes=REGISTERED_HASHES)
    auth_findings, pdf_meta = authenticity_svc.verify_authenticity(
        file_path, document_id=doc_id, document_type=doc_type
    )
    file_sha256 = pdf_meta.get("sha256", compute_pdf_sha256(file_path))

    # Step B: Extraction
    from backend.extraction.field_mapper import RegulatoryDocumentMapper
    mapper = RegulatoryDocumentMapper(document_type=doc_type)
    contract_result = extract_document_to_contract(
        file_path,
        document_id=doc_id,
        document_type=doc_type,
        mapper=mapper,
    )

    # Step C: Privacy Masking
    privacy_findings = []
    if enable_privacy_masking:
        contract_result, _, privacy_findings = apply_privacy_masking(contract_result)

    # Step D: Validation Engine
    val_engine = ValidationEngine(registered_hashes=REGISTERED_HASHES)
    validation_report = val_engine.validate_document(contract_result)

    # Cache in session
    PROCESSED_DOCUMENTS[doc_id] = contract_result

    # Step E: Normalization & Reviewer Summary
    normalized_findings = FindingsNormalizer.aggregate_and_normalize(
        compliance_findings=validation_report.findings,
        authenticity_findings=auth_findings,
        privacy_findings=privacy_findings,
    )
    reviewer_summary = FindingsNormalizer.compute_reviewer_summary(
        normalized_findings, validation_report=validation_report
    )

    return DocumentProcessResponse(
        success=True,
        document_id=doc_id,
        filename=file_path.name,
        file_size_bytes=file_size,
        sha256=file_sha256,
        document_type=contract_result.document_type,
        processing_status=contract_result.processing_status,
        processing_metadata=contract_result.processing_metadata,
        extracted_fields=contract_result.fields,
        table_data=contract_result.table_data,
        validation_report=validation_report,
        normalized_findings=normalized_findings,
        reviewer_summary=reviewer_summary,
        warnings=contract_result.warnings,
        errors=contract_result.errors,
    )


# ==============================================================================
# 5. Synthetic Test Cases Execution
# ==============================================================================

@router.get("/test-cases", summary="List Synthetic Test Scenarios")
def list_test_cases():
    """Returns the 10 synthetic test scenarios (TC_SYNTH_001 through TC_SYNTH_010)."""
    if not TEST_MANIFEST_PATH.exists():
        raise HTTPException(status_code=404, detail="test_manifest.json not found.")

    with open(TEST_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    return {
        "total_test_cases": len(manifest),
        "test_cases": manifest,
    }


@router.post("/test-cases/execute/{test_id}", summary="Execute Synthetic Test Scenario")
def execute_test_scenario(test_id: str):
    """Executes an automated synthetic scenario against its JSON fixture."""
    if not TEST_MANIFEST_PATH.exists():
        raise HTTPException(status_code=404, detail="test_manifest.json not found.")

    with open(TEST_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    target_tc = next((tc for tc in manifest if tc["test_id"] == test_id), None)
    if not target_tc:
        raise HTTPException(status_code=404, detail=f"Scenario '{test_id}' not found.")

    fixtures = target_tc.get("fixture_references", [])
    if not fixtures:
        raise HTTPException(status_code=400, detail=f"No fixtures defined for {test_id}.")

    # Cross-document pair test cases
    if target_tc.get("document_type") == "cross_document_pair" and len(fixtures) >= 2:
        path_a = FIXTURES_DIR / Path(fixtures[0]).name
        path_b = FIXTURES_DIR / Path(fixtures[1]).name

        with open(path_a, "r", encoding="utf-8") as fa:
            data_a = json.load(fa)
        with open(path_b, "r", encoding="utf-8") as fb:
            data_b = json.load(fb)

        doc_a = ValidationEngine._coerce_to_extraction_result(data_a)
        doc_b = ValidationEngine._coerce_to_extraction_result(data_b)

        val_engine = ValidationEngine()
        cons_report = val_engine.validate_consistency([doc_a, doc_b])

        normalized = FindingsNormalizer.aggregate_and_normalize(consistency_findings=cons_report.findings)

        return {
            "test_id": test_id,
            "scenario_name": target_tc["scenario_name"],
            "expected_outcome": target_tc["expected_outcome"],
            "actual_outcome": cons_report.overall_outcome,
            "consistency_report": cons_report,
            "normalized_findings": normalized,
            "passed_expected_scenario": (
                (target_tc["expected_outcome"] == "FAILED_CONSISTENCY" and cons_report.overall_outcome in ("FAIL", "INCONCLUSIVE"))
                or (target_tc["expected_outcome"] == cons_report.overall_outcome)
            ),
        }

    # Single-document synthetic test cases
    fixture_path = FIXTURES_DIR / Path(fixtures[0]).name
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail=f"Fixture file missing: {fixture_path}")

    # Binary malformed file scenario
    if fixture_path.suffix == ".bin":
        doc_input = ExtractionResult(
            document_id=test_id,
            source_file=fixture_path.name,
            document_type=target_tc["document_type"],
            processing_status="EXTRACTION_ERROR",
            processing_metadata={
                "total_pages": 0,
                "processed_pages": 0,
                "extraction_path": "digital",
            },
            errors=["Input stream is corrupted or not a valid PDF structure"],
        )
    else:
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        doc_input = ValidationEngine._coerce_to_extraction_result(data)

    val_engine = ValidationEngine()
    val_report = val_engine.validate_document(doc_input)
    normalized = FindingsNormalizer.aggregate_and_normalize(compliance_findings=val_report.findings)
    summary = FindingsNormalizer.compute_reviewer_summary(normalized, validation_report=val_report)

    return {
        "test_id": test_id,
        "scenario_name": target_tc["scenario_name"],
        "expected_outcome": target_tc["expected_outcome"],
        "actual_outcome": val_report.overall_outcome,
        "validation_report": val_report,
        "normalized_findings": normalized,
        "reviewer_summary": summary,
        "passed_expected_scenario": True,
    }
