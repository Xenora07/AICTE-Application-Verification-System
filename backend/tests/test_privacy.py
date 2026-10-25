"""
backend/tests/test_privacy.py - Comprehensive Unit Tests for Person 3 Privacy Gateway.

Covers:
1. Sensitive field masking (Aadhaar, PAN, phone, email, bank account, generic).
2. Common email and phone pattern redaction in free text.
3. Non-destructive transformation: preservation of original nested input and raw evidence.
4. Missing values, empty values, and malformed input handling.
5. Stable, scope-separated HMAC tokenization.
6. Rejection of weak or missing tokenization secrets.
7. Safe error handling (no sensitive data leaked).
8. Existing extraction and validation schemas remaining unaffected.
"""

from copy import deepcopy
import json
import os
import pytest

from backend.security.privacy import (
    NON_MASKABLE_FIELDS,
    PrivacyPurpose,
    enforce_privacy_policy,
    mask_aadhaar,
    mask_bank_account,
    mask_email,
    mask_extraction_payload,
    mask_field_evidence,
    mask_generic_text,
    mask_pan,
    mask_phone,
    redact_text,
    sanitize_log_message,
    tokenize_identifier,
)
from src.schemas.common import FieldEvidence
from src.schemas.extraction_result import ExtractionResult, ProcessingMetadata

VALID_TEST_SECRET = "production_grade_salt_key_2026_sih"


# ==============================================================================
# 1. Sensitive Field Masking Tests
# ==============================================================================


def test_mask_aadhaar():
    """Verify Aadhaar masking preserves only the last 4 digits."""
    assert mask_aadhaar("2345 6789 0123") == "XXXX-XXXX-0123"
    assert mask_aadhaar("2345-6789-0123") == "XXXX-XXXX-0123"
    assert mask_aadhaar("234567890123") == "XXXX-XXXX-0123"
    assert mask_aadhaar("") == ""
    assert mask_aadhaar(None) == ""
    # Malformed / partial digits
    assert mask_aadhaar("123") == "XXXX-XXXX-XXXX"
    assert mask_aadhaar("123456") == "XX3456"


def test_mask_pan():
    """Verify PAN masking preserves first 2 and last 2 characters."""
    assert mask_pan("ABCDE1234F") == "AB******4F"
    assert mask_pan("abcde1234f") == "AB******4F"
    assert mask_pan("") == ""
    assert mask_pan(None) == ""
    # Malformed / short PAN
    assert mask_pan("ABC") == "******"


def test_mask_phone():
    """Verify phone masking preserves last 4 digits and handles country code."""
    assert mask_phone("9876543210") == "******3210"
    assert mask_phone("+91 98765 43210") == "+91-XXXXX-3210"
    assert mask_phone("+91-9876543210") == "+91-XXXXX-3210"
    assert mask_phone("") == ""
    assert mask_phone(None) == ""
    # Malformed short phone
    assert mask_phone("123") == "******"


def test_mask_email():
    """Verify email masking preserves domain and boundary initials."""
    assert mask_email("principal@kgec.edu.in") == "p***l@kgec.edu.in"
    assert mask_email("ab@kgec.edu.in") == "a***@kgec.edu.in"
    assert mask_email("a@kgec.edu.in") == "a***@kgec.edu.in"
    assert mask_email("") == ""
    assert mask_email(None) == ""
    # Malformed (no @)
    assert mask_email("notanemail") == "n********l"


def test_mask_bank_account():
    """Verify bank account masks all but last 4 digits."""
    assert mask_bank_account("123456789012") == "XXXXXXXX9012"
    assert mask_bank_account("5678") == "5678"
    assert mask_bank_account("12") == "XXXX-XXXX"
    assert mask_bank_account(None) == ""


def test_mask_generic_text():
    """Verify generic text masking."""
    assert mask_generic_text("Confidential Note", show_first=1, show_last=1) == "C***************e"
    assert mask_generic_text("Hi", show_first=1, show_last=1) == "****"
    assert mask_generic_text(None) == ""


# ==============================================================================
# 2. Free Text Pattern Redaction & Conservatism Tests
# ==============================================================================


def test_redact_text_identifies_pii():
    """Verify conservative pattern redaction catches common PII in text snippets."""
    sample = (
        "Contact the Registrar at principal@college.ac.in or call +91 98765 43210. "
        "Aadhaar: 2345 6789 0123, PAN: ABCDE1234F."
    )
    redacted = redact_text(sample, replacement_mode="placeholder")
    assert "[EMAIL_REDACTED]" in redacted
    assert "[PHONE_REDACTED]" in redacted
    assert "[AADHAAR_REDACTED]" in redacted
    assert "[PAN_REDACTED]" in redacted
    assert "principal@college.ac.in" not in redacted
    assert "98765 43210" not in redacted
    assert "2345 6789 0123" not in redacted
    assert "ABCDE1234F" not in redacted


def test_redact_text_preserves_regulatory_identifiers():
    """
    CRITICAL CONSERVATISM TEST:
    Ensure free-text redaction does NOT corrupt AICTE Application IDs,
    Permanent Institute IDs, dates, academic years, or pincodes.
    """
    safe_sample = (
        "Application ID 1-46227285868 for Permanent Institute ID 1-4775731 "
        "submitted for Academic Year 2026-27 on 2024-05-01 with Pincode 741235."
    )
    redacted = redact_text(safe_sample, replacement_mode="placeholder")
    # All regulatory tokens MUST be preserved exactly
    assert "1-46227285868" in redacted
    assert "1-4775731" in redacted
    assert "2026-27" in redacted
    assert "2024-05-01" in redacted
    assert "741235" in redacted


# ==============================================================================
# 3. Preservation of Original Nested Input and Evidence Tests
# ==============================================================================


def test_non_destructive_field_evidence_masking():
    """Verify masking FieldEvidence returns a new copy without modifying original."""
    original_evidence = FieldEvidence(
        raw_value="+91 98765 43210",
        normalized_value="+91 98765 43210",
        page_number=1,
        bounding_box=[10.0, 20.0, 100.0, 40.0],
        confidence=0.95,
        extraction_method="digital",
        is_uncertain=False,
    )
    original_raw = original_evidence.raw_value
    original_norm = original_evidence.normalized_value

    masked = mask_field_evidence(
        original_evidence,
        field_name="phone_number",
        purpose=PrivacyPurpose.REVIEWER_VIEW,
    )

    # Output is masked
    assert masked.raw_value == "+91-XXXXX-3210"
    assert masked.normalized_value == "+91-XXXXX-3210"
    # Geometry and metadata preserved
    assert masked.page_number == 1
    assert masked.bounding_box == [10.0, 20.0, 100.0, 40.0]
    assert masked.confidence == 0.95

    # Original is COMPLETELY UNMODIFIED
    assert original_evidence.raw_value == original_raw
    assert original_evidence.normalized_value == original_norm


def test_non_destructive_extraction_payload_masking():
    """Verify masking ExtractionResult leaves the original payload unchanged."""
    meta = ProcessingMetadata(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        digital_pages=[1],
    )
    result = ExtractionResult(
        document_id="DOC_REAL_003",
        source_file="real_documents/test.pdf",
        document_type="aicte_eoa",
        processing_metadata=meta,
        fields={
            "application_id": FieldEvidence(
                raw_value="1-46227285868",
                normalized_value="1-46227285868",
                page_number=1,
            ),
            "contact_email": FieldEvidence(
                raw_value="principal@kgec.edu.in",
                normalized_value="principal@kgec.edu.in",
                page_number=1,
            ),
            "faculty_aadhaar": FieldEvidence(
                raw_value="2345 6789 0123",
                normalized_value="234567890123",
                page_number=1,
            ),
        },
        warnings=["Notice: Contact admin at support@aicte-india.org for updates"],
        errors=[],
    )

    masked_payload = mask_extraction_payload(result, purpose=PrivacyPurpose.REVIEWER_VIEW)

    # 1. Non-maskable regulatory field (application_id) is NOT masked
    assert masked_payload.fields["application_id"].raw_value == "1-46227285868"

    # 2. Sensitive fields ARE masked
    assert masked_payload.fields["contact_email"].raw_value == "p***l@kgec.edu.in"
    assert masked_payload.fields["faculty_aadhaar"].raw_value == "XXXX-XXXX-0123"

    # 3. Warnings have PII redacted
    assert "[EMAIL_REDACTED]" in masked_payload.warnings[0]

    # 4. Invariant: Original object is completely untouched
    assert result.fields["contact_email"].raw_value == "principal@kgec.edu.in"
    assert result.fields["faculty_aadhaar"].raw_value == "2345 6789 0123"
    assert "support@aicte-india.org" in result.warnings[0]


def test_non_sensitive_fields_not_overmasked_in_reviewer_view():
    """Verify non-sensitive fields (e.g. city, district, state) are NOT masked in REVIEWER_VIEW."""
    evidence = FieldEvidence(
        raw_value="Kalyani",
        normalized_value="Kalyani",
        page_number=1,
    )
    # Reviewer view must preserve non-sensitive fields
    masked_rev = mask_field_evidence(evidence, field_name="city", purpose=PrivacyPurpose.REVIEWER_VIEW)
    assert masked_rev.raw_value == "Kalyani"
    assert masked_rev.normalized_value == "Kalyani"

    # Public export masks unclassified fields
    masked_pub = mask_field_evidence(evidence, field_name="city", purpose=PrivacyPurpose.PUBLIC_EXPORT)
    assert masked_pub.raw_value != "Kalyani"


def test_internal_verification_purpose_retains_raw_data():
    """Verify that INTERNAL_VERIFICATION purpose performs no masking on payloads."""
    payload = {
        "fields": {
            "contact_email": {"raw_value": "dean@kgec.edu.in", "normalized_value": "dean@kgec.edu.in"},
            "application_id": {"raw_value": "1-46227285868", "normalized_value": "1-46227285868"},
        },
        "warnings": ["Direct email: dean@kgec.edu.in"],
    }
    unmasked = mask_extraction_payload(payload, purpose=PrivacyPurpose.INTERNAL_VERIFICATION)
    assert unmasked["fields"]["contact_email"]["raw_value"] == "dean@kgec.edu.in"
    assert unmasked["warnings"][0] == "Direct email: dean@kgec.edu.in"


# ==============================================================================
# 4. Missing Values, Empty Values, and Malformed Input Tests
# ==============================================================================


def test_malformed_and_missing_inputs():
    """Verify graceful handling of None, empty dicts, unexpected types."""
    assert mask_extraction_payload(None) is None
    assert mask_extraction_payload({}) == {}
    assert mask_extraction_payload([]) == []
    assert mask_extraction_payload("plain string") == "plain string"
    assert mask_field_evidence(None) is None

    # Dict with missing fields/keys
    partial_dict = {"fields": {"unknown_field": None}}
    masked = mask_extraction_payload(partial_dict)
    assert masked["fields"]["unknown_field"] is None


# ==============================================================================
# 5. Stable, Scope-Separated HMAC Tokenization Tests
# ==============================================================================


def test_tokenize_identifier_stability():
    """Verify same value + salt + scope produces identical token deterministically."""
    tok1 = tokenize_identifier("SESSION_98765", secret=VALID_TEST_SECRET, scope="applicant")
    tok2 = tokenize_identifier("SESSION_98765", secret=VALID_TEST_SECRET, scope="applicant")
    assert tok1 == tok2
    assert tok1.startswith("tok_applicant_")


def test_tokenize_identifier_scope_separation():
    """Verify different scopes yield distinct tokens for the same input value."""
    tok_app = tokenize_identifier("COMMON_ID", secret=VALID_TEST_SECRET, scope="applicant")
    tok_fac = tokenize_identifier("COMMON_ID", secret=VALID_TEST_SECRET, scope="faculty")
    assert tok_app != tok_fac
    assert tok_app.startswith("tok_applicant_")
    assert tok_fac.startswith("tok_faculty_")


def test_tokenize_identifier_salt_separation():
    """Verify different secrets yield distinct tokens."""
    tok1 = tokenize_identifier("ID_123", secret=VALID_TEST_SECRET, scope="applicant")
    tok2 = tokenize_identifier("ID_123", secret="alternative_secret_salt_9999", scope="applicant")
    assert tok1 != tok2


def test_tokenize_missing_or_empty_value():
    """Verify missing values return None without raising exceptions."""
    assert tokenize_identifier(None, secret=VALID_TEST_SECRET) is None
    assert tokenize_identifier("", secret=VALID_TEST_SECRET) is None
    assert tokenize_identifier("   ", secret=VALID_TEST_SECRET) is None


# ==============================================================================
# 6. Rejection of Weak or Missing Tokenization Secrets
# ==============================================================================


def test_reject_missing_tokenization_secret(monkeypatch):
    """Verify ValueError is raised if secret is missing from arg and env."""
    monkeypatch.delenv("AICTE_PRIVACY_SALT", raising=False)
    monkeypatch.delenv("TOKENIZATION_SECRET", raising=False)

    with pytest.raises(ValueError, match="Tokenization secret cannot be empty"):
        tokenize_identifier("USER_123", secret=None)

    with pytest.raises(ValueError, match="Tokenization secret cannot be empty"):
        tokenize_identifier("USER_123", secret="   ")


def test_reject_short_tokenization_secret():
    """Verify ValueError is raised for secrets shorter than minimum length (16)."""
    with pytest.raises(ValueError, match="too short"):
        tokenize_identifier("USER_123", secret="short_key_123")


def test_reject_known_weak_secrets():
    """Verify rejection of default or trivial secrets."""
    weak_candidates = ["secret", "changeme", "password", "1234567890123456"]
    for weak in weak_candidates:
        with pytest.raises(ValueError):
            tokenize_identifier("USER_123", secret=weak)


# ==============================================================================
# 7. Safe Error Handling & Logging Sanitization Tests
# ==============================================================================


def test_sanitize_log_message():
    """Verify log messages are sanitized without throwing errors."""
    msg = "User with Aadhaar 2345 6789 0123 and email test@aicte.gov.in logged in."
    clean = sanitize_log_message(msg)
    assert "[AADHAAR_REDACTED]" in clean
    assert "[EMAIL_REDACTED]" in clean
    assert "2345 6789 0123" not in clean
    assert "test@aicte.gov.in" not in clean


def test_sanitize_log_message_empty():
    """Verify empty/None log message handling."""
    assert sanitize_log_message("") == ""
    assert sanitize_log_message(None) == ""


# ==============================================================================
# 8. Policy Helper and Schema Compatibility Tests
# ==============================================================================


def test_enforce_privacy_policy_roles():
    """Verify role mapping helper operates cleanly across standard persona roles."""
    payload = {
        "fields": {
            "application_id": {"raw_value": "1-46227285868"},
            "phone_number": {"raw_value": "+91 98765 43210"},
        }
    }

    # Admin: sees unmasked
    admin_view = enforce_privacy_policy(payload, role="admin")
    assert admin_view["fields"]["phone_number"]["raw_value"] == "+91 98765 43210"

    # Reviewer: sees masked phone, unmasked application_id
    rev_view = enforce_privacy_policy(payload, role="reviewer")
    assert rev_view["fields"]["application_id"]["raw_value"] == "1-46227285868"
    assert rev_view["fields"]["phone_number"]["raw_value"] == "+91-XXXXX-3210"

    # Public: everything sensitive masked
    pub_view = enforce_privacy_policy(payload, role="public")
    assert pub_view["fields"]["phone_number"]["raw_value"] == "+91-XXXXX-3210"


def test_table_data_redaction_in_public_export():
    """Verify table row free text is redacted in PUBLIC_EXPORT but preserved in REVIEWER_VIEW."""
    payload = {
        "fields": {},
        "table_data": [
            {
                "table_name": "contact_table",
                "rows": [
                    {"faculty": "Dr. Sharma", "contact": "sharma@kgec.edu.in", "intake": 60}
                ]
            }
        ]
    }
    # Reviewer view preserves course/table data
    rev_payload = mask_extraction_payload(payload, purpose=PrivacyPurpose.REVIEWER_VIEW)
    assert rev_payload["table_data"][0]["rows"][0]["contact"] == "sharma@kgec.edu.in"

    # Public view redacts sensitive strings in table rows
    pub_payload = mask_extraction_payload(payload, purpose=PrivacyPurpose.PUBLIC_EXPORT)
    assert "[EMAIL_REDACTED]" in pub_payload["table_data"][0]["rows"][0]["contact"]
    # Intakes and numbers preserved
    assert pub_payload["table_data"][0]["rows"][0]["intake"] == 60


def test_existing_schemas_remain_unaffected():
    """Verify existing ExtractionResult validation passes cleanly on masked payloads."""
    meta = ProcessingMetadata(
        total_pages=1,
        processed_pages=1,
        extraction_path="digital",
        digital_pages=[1],
    )
    result = ExtractionResult(
        document_id="DOC_REAL_003",
        source_file="real_documents/KGEC_AICTE_Approval_2026-27.pdf",
        document_type="aicte_eoa",
        processing_metadata=meta,
        fields={
            "application_id": FieldEvidence(
                raw_value="1-46227285868",
                normalized_value="1-46227285868",
                page_number=1,
                bounding_box=[100.0, 100.0, 200.0, 120.0],
            ),
            "contact_email": FieldEvidence(
                raw_value="info@kgec.edu.in",
                normalized_value="info@kgec.edu.in",
                page_number=1,
            ),
        },
        warnings=[],
        errors=[],
    )

    masked = mask_extraction_payload(result, purpose=PrivacyPurpose.REVIEWER_VIEW)

    # Must remain a fully valid Pydantic ExtractionResult
    assert isinstance(masked, ExtractionResult)
    # Validates against Pydantic schema serialization
    json_export = masked.to_json()
    assert json_export is not None
    loaded = ExtractionResult.model_validate_json(json_export)
    assert loaded.document_id == "DOC_REAL_003"
    assert loaded.fields["contact_email"].raw_value == "i***o@kgec.edu.in"
