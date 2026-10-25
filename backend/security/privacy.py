"""
backend/security/privacy.py - Privacy Gateway and PII Protection Layer for SIH26261.

Core Mandates:
1. Non-destructive: Original payloads and extraction evidence are never modified or overwritten.
2. Honest distinction: Clearly separates raw internal evidence (for validation) from
   masked/redacted views (for reviewers, logs, and public export).
3. Configurable sensitivity: Field-level masking rules with strict protection for non-maskable
   regulatory identifiers (application_id, permanent_institute_id, academic_year, etc.).
4. Conservative pattern redaction: Targets common PII (Aadhaar, PAN, phone, email) in free text
   without corrupting regulatory identifiers or dates.
5. Scoped, keyed HMAC tokenization: Deterministic, salt-based pseudonymization without
   reversible credential storage.
6. Safe logging: Minimized log sanitization that never leaks sensitive data in exceptions or logs.

Disclaimer:
Deterministic pattern matching and masking utilities are not a complete PII detector.
Utility helpers are not a substitute for authentication or authorization middleware.
Actual API boundaries and access policies must enforce role authorization.
"""

from copy import deepcopy
from enum import Enum
import hashlib
import hmac
import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. Enums and Purpose Definitions
# ==============================================================================


class PrivacyPurpose(str, Enum):
    """
    Distinguishes the operational purpose for accessing extraction payloads.
    - INTERNAL_VERIFICATION: Full unmasked raw evidence for deterministic validation and consistency rules.
    - REVIEWER_VIEW: Direct personal identifiers masked, regulatory institutional identifiers retained.
    - PUBLIC_EXPORT: Full redaction of all sensitive structured fields and free-text PII.
    - AUDIT_LOG: Scrubbed representation safe for log streams and metrics.
    """
    INTERNAL_VERIFICATION = "internal_verification"
    REVIEWER_VIEW = "reviewer_view"
    PUBLIC_EXPORT = "public_export"
    AUDIT_LOG = "audit_log"


class SensitivityLevel(str, Enum):
    """Classification levels for document fields."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED_PII = "restricted_pii"


# Regulatory identifiers and fields strictly required for validation & cross-document consistency.
# These MUST NOT be masked during standard reviewer or internal operations.
NON_MASKABLE_FIELDS: Set[str] = {
    "document_id",
    "application_id",
    "permanent_institute_id",
    "institution_name",
    "academic_year",
    "document_type",
    "course",
    "programme",
    "level",
    "approved_intake",
    "valid_from",
    "valid_to",
    "cgpa",
    "accreditation_grade",
}

# Known weak tokenization secrets that must be explicitly rejected
WEAK_SECRETS_BLACKLIST: Set[str] = {
    "secret",
    "changeme",
    "password",
    "12345678",
    "1234567890123456",
    "default_secret",
    "tokenization_secret",
    "admin123",
}

# ==============================================================================
# 2. Regular Expressions for Conservative Detection
# ==============================================================================

# UIDAI Aadhaar standard: 12 digits, first digit is [2-9] (never 0 or 1).
# Lookbehind/lookahead (?<![\w-]) and (?![\w-]) strictly prevents colliding with
# hyphenated identifiers like AICTE IDs ("1-46227285868") or date ranges ("2024-05-01").
AADHAAR_REGEX = re.compile(r"(?<![\w-])[2-9]\d{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}(?![\w-])")

# Indian Income Tax PAN: exactly 5 uppercase letters, 4 digits, 1 uppercase letter.
PAN_REGEX = re.compile(r"(?<![\w-])[A-Z]{5}[0-9]{4}[A-Z](?![\w-])")

# Indian Mobile Phone: optional +91, mobile digit [6-9], total 10 digits.
# Strictly bounded so it never matches 6-digit pin codes or substrings of portal IDs.
PHONE_REGEX = re.compile(r"(?<![\w-])(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?[0-9]{5}(?![\w-])")

# Standard RFC-compliant Email address.
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


# ==============================================================================
# 3. Deterministic Field-Specific Masking Utilities
# ==============================================================================


def mask_aadhaar(val: Optional[str]) -> str:
    """
    Mask a 12-digit Aadhaar number, preserving only the last 4 digits.
    Example: '2345 6789 0123' -> 'XXXX-XXXX-0123'
    Safe on malformed or empty inputs.
    """
    if not val:
        return ""
    digits = re.sub(r"\D", "", str(val))
    if len(digits) == 12:
        return f"XXXX-XXXX-{digits[-4:]}"
    if len(digits) > 4:
        return f"{'X' * (len(digits) - 4)}{digits[-4:]}"
    return "XXXX-XXXX-XXXX"


def mask_pan(val: Optional[str]) -> str:
    """
    Mask a 10-character Indian Permanent Account Number (PAN).
    Preserves first 2 and last 2 characters while masking middle 6.
    Example: 'ABCDE1234F' -> 'AB******4F'
    Safe on malformed or empty inputs.
    """
    if not val:
        return ""
    clean = str(val).strip().upper()
    if len(clean) == 10:
        return f"{clean[:2]}******{clean[-2:]}"
    if len(clean) > 4:
        return f"{clean[:2]}{'*' * (len(clean) - 3)}{clean[-1:]}"
    return "******"


def mask_phone(val: Optional[str]) -> str:
    """
    Mask an Indian telephone or mobile number, preserving only the last 4 digits.
    Example: '+91 98765 43210' -> '+91-XXXXX-3210' or '******3210'
    Safe on malformed or empty inputs.
    """
    if not val:
        return ""
    raw = str(val).strip()
    digits = re.sub(r"\D", "", raw)
    has_country_code = raw.startswith("+91") or digits.startswith("91") and len(digits) > 10
    if len(digits) >= 10:
        last4 = digits[-4:]
        return f"+91-XXXXX-{last4}" if has_country_code else f"******{last4}"
    if len(digits) >= 4:
        return f"******{digits[-4:]}"
    return "******"


def mask_email(val: Optional[str]) -> str:
    """
    Mask an email address while preserving domain structure and initial identifier character.
    Example: 'principal@kgec.edu.in' -> 'p***l@kgec.edu.in'
    Safe on malformed or empty inputs.
    """
    if not val:
        return ""
    raw = str(val).strip()
    if "@" not in raw:
        return mask_generic_text(raw)
    parts = raw.split("@", 1)
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = f"{user[0]}***" if user else "***"
    else:
        masked_user = f"{user[0]}***{user[-1]}"
    return f"{masked_user}@{domain}"


def mask_bank_account(val: Optional[str]) -> str:
    """
    Mask a bank account number, preserving only the last 4 digits.
    Example: '123456789012' -> 'XXXXXXXX9012'
    Safe on malformed or empty inputs.
    """
    if not val:
        return ""
    digits = re.sub(r"\D", "", str(val))
    if len(digits) >= 4:
        return f"{'X' * (len(digits) - 4)}{digits[-4:]}"
    return "XXXX-XXXX"


def mask_generic_text(
    val: Optional[str],
    show_first: int = 1,
    show_last: int = 1,
    mask_char: str = "*",
) -> str:
    """
    Generic masking utility preserving configurable leading/trailing characters.
    Safe on malformed or empty inputs.
    """
    if not val:
        return ""
    raw = str(val).strip()
    total = len(raw)
    if total <= (show_first + show_last):
        return mask_char * max(total, 4)
    middle_len = total - show_first - show_last
    return f"{raw[:show_first]}{mask_char * middle_len}{raw[-show_last:]}"


# Field name mapping to specific masking functions
FIELD_MASKERS: Dict[str, Callable[[Optional[str]], str]] = {
    "aadhaar": mask_aadhaar,
    "aadhaar_number": mask_aadhaar,
    "faculty_aadhaar": mask_aadhaar,
    "trustee_aadhaar": mask_aadhaar,
    "pan": mask_pan,
    "pan_number": mask_pan,
    "faculty_pan": mask_pan,
    "trustee_pan": mask_pan,
    "phone": mask_phone,
    "phone_number": mask_phone,
    "mobile": mask_phone,
    "mobile_number": mask_phone,
    "contact_number": mask_phone,
    "telephone": mask_phone,
    "telephone_number": mask_phone,
    "landline": mask_phone,
    "landline_number": mask_phone,
    "alt_phone": mask_phone,
    "email": mask_email,
    "email_id": mask_email,
    "contact_email": mask_email,
    "principal_email": mask_email,
    "alt_email": mask_email,
    "bank_account": mask_bank_account,
    "account_number": mask_bank_account,
    "bank_account_no": mask_bank_account,
    "account_no": mask_bank_account,
}


def get_masker_for_field(field_name: str) -> Optional[Callable[[Optional[str]], str]]:
    """Determine the appropriate masking function for a given field name."""
    clean_name = field_name.strip().lower()
    if clean_name in FIELD_MASKERS:
        return FIELD_MASKERS[clean_name]
    for key, masker in FIELD_MASKERS.items():
        if key in clean_name:
            return masker
    return None


# ==============================================================================
# 4. Conservative Free-Text Redaction
# ==============================================================================


def redact_text(text: Optional[str], replacement_mode: str = "placeholder") -> str:
    """
    Conservatively redact common sensitive patterns (Aadhaar, PAN, phone, email)
    from unstructured free text or OCR string snippets.

    Non-Destructive Guarantee:
    Does NOT match or alter AICTE application IDs ('1-46227285868'), permanent institute IDs,
    academic years ('2026-27'), standard ISO dates ('2024-05-01'), or 6-digit pin codes.

    Parameters:
        text: Free-text string to redact.
        replacement_mode: 'placeholder' (e.g. '[EMAIL_REDACTED]') or 'mask' (e.g. 'j***e@domain.com').

    Returns:
        Redacted string with sensitive patterns obscured.
    """
    if not text:
        return ""
    if not isinstance(text, str):
        return str(text)

    result = text

    # 1. Email Redaction
    if replacement_mode == "placeholder":
        result = EMAIL_REGEX.sub("[EMAIL_REDACTED]", result)
    else:
        result = EMAIL_REGEX.sub(lambda m: mask_email(m.group(0)), result)

    # 2. Aadhaar Redaction (UIDAI digits: starts with 2-9, 12 digits total)
    if replacement_mode == "placeholder":
        result = AADHAAR_REGEX.sub("[AADHAAR_REDACTED]", result)
    else:
        result = AADHAAR_REGEX.sub(lambda m: mask_aadhaar(m.group(0)), result)

    # 3. PAN Redaction (5 uppercase letters, 4 digits, 1 uppercase letter)
    if replacement_mode == "placeholder":
        result = PAN_REGEX.sub("[PAN_REDACTED]", result)
    else:
        result = PAN_REGEX.sub(lambda m: mask_pan(m.group(0)), result)

    # 4. Phone Redaction (starts with 6-9, 10 digits total)
    if replacement_mode == "placeholder":
        result = PHONE_REGEX.sub("[PHONE_REDACTED]", result)
    else:
        result = PHONE_REGEX.sub(lambda m: mask_phone(m.group(0)), result)

    return result


# ==============================================================================
# 5. Scoped, Keyed HMAC Tokenization
# ==============================================================================


def tokenize_identifier(
    value: Optional[str],
    secret: Optional[str] = None,
    scope: str = "default",
    min_secret_length: int = 16,
) -> Optional[str]:
    """
    Compute a deterministic, scoped HMAC-SHA256 token for an identifier.

    Guarantees:
    - Stable: identical value + same secret + same scope produces identical token.
    - Scope-separated: different scopes yield completely different tokens for the same input.
    - Non-reversible: does not store or leak plaintext credentials.
    - Rejects weak or missing tokenization secrets with ValueError.
    - Missing or empty inputs return None or empty string gracefully.

    Parameters:
        value: Identifier to tokenize (e.g. applicant session ID, faculty ID, phone number).
        secret: Cryptographic HMAC key. If None, reads from 'AICTE_PRIVACY_SALT' or 'TOKENIZATION_SECRET'.
        scope: Domain/entity scope prefix (e.g. 'applicant', 'aadhaar', 'mobile').
        min_secret_length: Minimum accepted secret character length (default 16).

    Returns:
        Token formatted as 'tok_<scope>_<digest16>', or None if input value is None/empty.
    """
    if value is None or str(value).strip() == "":
        return None

    # Retrieve secret from environment if not explicitly provided
    resolved_secret = secret or os.environ.get("AICTE_PRIVACY_SALT") or os.environ.get("TOKENIZATION_SECRET")

    if not resolved_secret or not resolved_secret.strip():
        raise ValueError("Tokenization secret cannot be empty or missing.")

    clean_secret = resolved_secret.strip()

    if len(clean_secret) < min_secret_length:
        raise ValueError(
            f"Tokenization secret too short ({len(clean_secret)} chars). Minimum length is {min_secret_length}."
        )

    if clean_secret.lower() in WEAK_SECRETS_BLACKLIST:
        raise ValueError("Weak or default tokenization secret rejected for security compliance.")

    clean_scope = scope.strip().lower() or "default"
    clean_val = str(value).strip()

    # Domain separation: scope is prefixed into the HMAC message
    message = f"{clean_scope}:{clean_val}".encode("utf-8")
    digest = hmac.new(clean_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    return f"tok_{clean_scope}_{digest[:16]}"


# ==============================================================================
# 6. Non-Destructive Payload & Evidence Masking
# ==============================================================================


def mask_field_evidence(
    evidence: Any,
    field_name: str = "",
    purpose: PrivacyPurpose = PrivacyPurpose.REVIEWER_VIEW,
    custom_masker: Optional[Callable[[Optional[str]], str]] = None,
) -> Any:
    """
    Non-destructively mask a FieldEvidence instance or dictionary.
    Preserves source page numbers, bounding boxes, honest confidence values,
    and extraction metadata, masking only the displayed raw and normalized values.

    Guarantees:
    - Never mutates the original evidence object (deep copy applied).
    - Preserves non-maskable fields during REVIEWER_VIEW and INTERNAL_VERIFICATION.
    """
    if evidence is None:
        return None

    # Internal verification needs 100% unaltered raw and normalized evidence
    if purpose == PrivacyPurpose.INTERNAL_VERIFICATION:
        return deepcopy(evidence)

    # Check non-maskable regulatory invariant
    clean_field = field_name.strip().lower()
    if clean_field in NON_MASKABLE_FIELDS and purpose != PrivacyPurpose.PUBLIC_EXPORT:
        return deepcopy(evidence)

    masker = custom_masker or get_masker_for_field(clean_field)
    if not masker:
        # In REVIEWER_VIEW and INTERNAL_VERIFICATION, non-sensitive fields (e.g. city, district, state)
        # must NOT be over-masked.
        if purpose in (PrivacyPurpose.INTERNAL_VERIFICATION, PrivacyPurpose.REVIEWER_VIEW):
            return deepcopy(evidence)
        # In PUBLIC_EXPORT or AUDIT_LOG, unclassified custom fields default to generic masking
        masker = lambda v: mask_generic_text(v)

    # Support both Pydantic FieldEvidence models and standard dictionaries
    if hasattr(evidence, "model_copy"):
        copied = evidence.model_copy(deep=True)
        raw_val = getattr(copied, "raw_value", None)
        norm_val = getattr(copied, "normalized_value", None)

        if raw_val is not None:
            setattr(copied, "raw_value", masker(str(raw_val)))
        if norm_val is not None and isinstance(norm_val, (str, int, float)):
            setattr(copied, "normalized_value", masker(str(norm_val)))

        return copied

    if isinstance(evidence, dict):
        copied_dict = deepcopy(evidence)
        if "raw_value" in copied_dict and copied_dict["raw_value"] is not None:
            copied_dict["raw_value"] = masker(str(copied_dict["raw_value"]))
        if "normalized_value" in copied_dict and copied_dict["normalized_value"] is not None:
            norm = copied_dict["normalized_value"]
            if isinstance(norm, (str, int, float)):
                copied_dict["normalized_value"] = masker(str(norm))
        return copied_dict

    # Scalar value fallback
    return masker(str(evidence))


def mask_extraction_payload(
    payload: Any,
    purpose: PrivacyPurpose = PrivacyPurpose.REVIEWER_VIEW,
    tokenization_secret: Optional[str] = None,
) -> Any:
    """
    Apply non-destructive privacy masking across an entire extraction payload
    (ExtractionResult Pydantic model or serialized JSON dict).

    Guarantees:
    - Original input payload remains completely unmodified.
    - Fields in NON_MASKABLE_FIELDS are protected from over-masking.
    - Structured fields are masked according to field sensitivity.
    - Free-text snippets in warnings or errors are conservatively redacted.
    - Missing, empty, or malformed payloads are handled without raising exceptions.
    """
    if payload is None:
        return None

    # Internal purpose returns deep copy without modifications
    if purpose == PrivacyPurpose.INTERNAL_VERIFICATION:
        return deepcopy(payload)

    # Work on a deep copy to prevent destructive mutations
    copied = deepcopy(payload)

    # Handle Pydantic ExtractionResult instance
    if hasattr(copied, "fields") and isinstance(copied.fields, dict):
        new_fields = {}
        for fname, fevidence in copied.fields.items():
            new_fields[fname] = mask_field_evidence(fevidence, field_name=fname, purpose=purpose)
        copied.fields = new_fields

        # Redact free text warnings/errors
        if hasattr(copied, "warnings") and isinstance(copied.warnings, list):
            copied.warnings = [redact_text(w) for w in copied.warnings]
        if hasattr(copied, "errors") and isinstance(copied.errors, list):
            copied.errors = [redact_text(e) for e in copied.errors]

        # Sanitize free text in table data for public/audit views
        if purpose in (PrivacyPurpose.PUBLIC_EXPORT, PrivacyPurpose.AUDIT_LOG):
            if hasattr(copied, "table_data") and isinstance(copied.table_data, list):
                for table in copied.table_data:
                    if hasattr(table, "rows") and isinstance(table.rows, list):
                        new_rows = []
                        for row in table.rows:
                            if isinstance(row, dict):
                                new_rows.append({k: (redact_text(v) if isinstance(v, str) else v) for k, v in row.items()})
                            else:
                                new_rows.append(row)
                        table.rows = new_rows

        return copied

    # Handle Dictionary payload
    if isinstance(copied, dict):
        if "fields" in copied and isinstance(copied["fields"], dict):
            new_fields = {}
            for fname, fevidence in copied["fields"].items():
                new_fields[fname] = mask_field_evidence(fevidence, field_name=fname, purpose=purpose)
            copied["fields"] = new_fields

        if "warnings" in copied and isinstance(copied["warnings"], list):
            copied["warnings"] = [redact_text(w) for w in copied["warnings"]]
        if "errors" in copied and isinstance(copied["errors"], list):
            copied["errors"] = [redact_text(e) for e in copied["errors"]]

        # Sanitize free text in table data for public/audit views
        if purpose in (PrivacyPurpose.PUBLIC_EXPORT, PrivacyPurpose.AUDIT_LOG):
            if "table_data" in copied and isinstance(copied["table_data"], list):
                for table in copied["table_data"]:
                    if isinstance(table, dict) and "rows" in table and isinstance(table["rows"], list):
                        table["rows"] = [
                            {k: (redact_text(v) if isinstance(v, str) else v) for k, v in row.items()}
                            if isinstance(row, dict) else row
                            for row in table["rows"]
                        ]

        return copied

    # Handle list of payloads or single scalar
    if isinstance(copied, list):
        return [mask_extraction_payload(item, purpose=purpose, tokenization_secret=tokenization_secret) for item in copied]

    return copied


# ==============================================================================
# 7. Role and Purpose Policy Helper
# ==============================================================================


def enforce_privacy_policy(
    payload: Any,
    role: str = "reviewer",
    tokenization_secret: Optional[str] = None,
) -> Any:
    """
    Convenience policy helper mapping role strings to PrivacyPurpose levels.

    Important Security Disclaimer:
    This utility helper is NOT a substitute for authentication or authorization middleware.
    Actual API boundaries, JWT validation, and RBAC authorization must be enforced
    at the API Gateway level (backend/api/routes.py).

    Role Mappings:
    - 'admin', 'system', 'internal': Full raw evidence (INTERNAL_VERIFICATION)
    - 'reviewer', 'evaluator': Masked personal PII, visible institutional data (REVIEWER_VIEW)
    - 'public', 'external', 'applicant': Full redaction (PUBLIC_EXPORT)
    - 'audit', 'logging': Log-scrubbed view (AUDIT_LOG)
    """
    clean_role = (role or "reviewer").strip().lower()

    if clean_role in {"admin", "system", "internal", "validator"}:
        purpose = PrivacyPurpose.INTERNAL_VERIFICATION
    elif clean_role in {"reviewer", "evaluator", "officer"}:
        purpose = PrivacyPurpose.REVIEWER_VIEW
    elif clean_role in {"audit", "auditor", "logger"}:
        purpose = PrivacyPurpose.AUDIT_LOG
    else:
        purpose = PrivacyPurpose.PUBLIC_EXPORT

    return mask_extraction_payload(payload, purpose=purpose, tokenization_secret=tokenization_secret)


# ==============================================================================
# 8. Safe Logging Utility
# ==============================================================================


def sanitize_log_message(message: str) -> str:
    """
    Sanitize an application log string by aggressively redacting sensitive patterns.
    Ensures debug statements, exception traces, or warning outputs never leak PII.
    """
    if not message:
        return ""
    return redact_text(str(message), replacement_mode="placeholder")

# ==============================================================================
# Phase 9: Dashboard PII Redaction & Masking Utilities (Person 4 Integration)
# ==============================================================================

try:
    from backend.common.models import ExtractionResult, FieldEvidence, ValidationFinding
except ImportError:
    pass

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
    doc: Any,
) -> Tuple[Any, int, List[Any]]:
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
    privacy_findings: List[Any] = []

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
