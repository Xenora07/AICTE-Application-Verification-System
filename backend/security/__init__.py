"""
backend.security - Security, Privacy Gateway, Authenticity, and Unified Findings.
"""

from backend.security.privacy import (
    PrivacyPurpose,
    SensitivityLevel,
    mask_aadhaar,
    mask_pan,
    mask_phone,
    mask_email,
    mask_bank_account,
    mask_generic_text,
    redact_text,
    tokenize_identifier,
    mask_field_evidence,
    mask_extraction_payload,
    enforce_privacy_policy,
    sanitize_log_message,
)
from backend.security.authenticity import (
    DocumentAuthenticityReport,
    DuplicateHashRegistry,
    compute_file_sha256,
    inspect_file_structure,
    inspect_pdf_metadata,
    assess_document_authenticity,
    verify_duplicate_via_validator,
)
from backend.security.findings import (
    UnifiedFindingsReport,
    UnifiedFindingsEngine,
    unify_findings,
    normalize_finding,
    deduplicate_findings,
    prioritize_findings,
    filter_report_for_privacy,
)

__all__ = [
    "PrivacyPurpose",
    "SensitivityLevel",
    "mask_aadhaar",
    "mask_pan",
    "mask_phone",
    "mask_email",
    "mask_bank_account",
    "mask_generic_text",
    "redact_text",
    "tokenize_identifier",
    "mask_field_evidence",
    "mask_extraction_payload",
    "enforce_privacy_policy",
    "sanitize_log_message",
    "DocumentAuthenticityReport",
    "DuplicateHashRegistry",
    "compute_file_sha256",
    "inspect_file_structure",
    "inspect_pdf_metadata",
    "assess_document_authenticity",
    "verify_duplicate_via_validator",
    "UnifiedFindingsReport",
    "UnifiedFindingsEngine",
    "unify_findings",
    "normalize_finding",
    "deduplicate_findings",
    "prioritize_findings",
    "filter_report_for_privacy",
]
