"""
backend/security/privacy.py - Privacy Gateway and PII Redaction for SIH26261 (Person 3).
Masks sensitive contact details and personal identifiers prior to external dashboard rendering.
"""

import copy
import re
from typing import List, Tuple
from backend.common.models import ExtractionResult, FieldEvidence, ValidationFinding


PHONE_PATTERN = re.compile(r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
BANK_ACCOUNT_PATTERN = re.compile(r"(?:A/C|Account(?:\s+No)?|Acct)[\s.:#]*([0-9]{9,18})", re.IGNORECASE)


def mask_pii_text(text: str) -> Tuple[str, int]:
    """
    Masks recognized PII patterns in string content.
    Returns:
        masked_text: Sanitized text with redacted placeholders
        redactions_count: Total count of PII entities masked
    """
    if not text:
        return text, 0

    count = 0

    def phone_sub(m):
        nonlocal count
        count += 1
        return "[REDACTED_PHONE]"

    def email_sub(m):
        nonlocal count
        count += 1
        return "[REDACTED_EMAIL]"

    def aadhaar_sub(m):
        nonlocal count
        count += 1
        return "[REDACTED_AADHAAR]"

    def pan_sub(m):
        nonlocal count
        count += 1
        return "[REDACTED_PAN]"

    def bank_sub(m):
        nonlocal count
        count += 1
        return "Account: [REDACTED_BANK_AC]"

    sanitized = PHONE_PATTERN.sub(phone_sub, text)
    sanitized = EMAIL_PATTERN.sub(email_sub, sanitized)
    sanitized = AADHAAR_PATTERN.sub(aadhaar_sub, sanitized)
    sanitized = PAN_PATTERN.sub(pan_sub, sanitized)
    sanitized = BANK_ACCOUNT_PATTERN.sub(bank_sub, sanitized)

    return sanitized, count


def apply_privacy_masking(
    doc: ExtractionResult,
) -> Tuple[ExtractionResult, int, List[ValidationFinding]]:
    """
    Applies privacy redaction to an ExtractionResult payload.
    Creates a deep copy so original raw extraction is preserved if needed.
    Returns:
        masked_doc: ExtractionResult with masked field raw_values and string fields
        redactions_count: Total redactions performed
        findings: List of ValidationFinding records for privacy audit trail
    """
    masked_doc = doc.model_copy(deep=True)
    total_redactions = 0
    privacy_findings: List[ValidationFinding] = []

    for field_name, evidence in masked_doc.fields.items():
        if evidence.raw_value and isinstance(evidence.raw_value, str):
            masked_raw, count = mask_pii_text(evidence.raw_value)
            if count > 0:
                total_redactions += count
                evidence.raw_value = masked_raw
                # If normalized_value is string, mask it as well if it contains PII
                if isinstance(evidence.normalized_value, str):
                    masked_norm, _ = mask_pii_text(evidence.normalized_value)
                    evidence.normalized_value = masked_norm

                privacy_findings.append(
                    ValidationFinding(
                        rule_id="PRIV_PII_REDACTED",
                        rule_name="PII Redaction Applied",
                        outcome="PASS",
                        severity="INFO",
                        explanation=f"Sensitive PII pattern redacted in field '{field_name}'.",
                        affected_document_ids=[doc.document_id],
                        affected_fields=[field_name],
                        evidence_values={"redactions": count},
                        requires_human_review=False,
                    )
                )

    if total_redactions == 0:
        privacy_findings.append(
            ValidationFinding(
                rule_id="PRIV_CLEAN_DOCUMENT",
                rule_name="Privacy Scan Passed",
                outcome="PASS",
                severity="INFO",
                explanation="No exposed sensitive personal contact details detected in extracted fields.",
                affected_document_ids=[doc.document_id],
                requires_human_review=False,
            )
        )

    return masked_doc, total_redactions, privacy_findings
