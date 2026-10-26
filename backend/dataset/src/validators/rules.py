"""
src/validators/rules.py - Deterministic single-document validation rules for regulatory documents.
Implements rules for:
- File parseability & schema conformance
- Mandatory field presence (e.g. academic_year)
- Identifier formats (application_id, permanent_institute_id)
- Date range validity (valid_to >= valid_from)
- Grade and CGPA regulatory bounds
- Low-confidence OCR threshold flagging (< 0.65)
- Ambiguous / conflicting evidence detection

Guarantees:
- Distinguishes PASS, FAIL, and INCONCLUSIVE.
- Missing or low-confidence evidence is never automatically treated as proof of failure.
- Human review is explicitly required when evidence is ambiguous or low-confidence.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional
from src.schemas.common import FieldEvidence
from src.schemas.extraction_result import ExtractionResult
from src.validators.schemas import ValidationFinding


def rule_file_parseable(doc: ExtractionResult) -> ValidationFinding:
    """Check if the document was successfully parsed without fatal extraction errors."""
    if doc.processing_status == "EXTRACTION_ERROR" or len(doc.errors) > 0:
        err_msg = "; ".join(doc.errors) if doc.errors else "Extraction error encountered"
        return ValidationFinding(
            rule_id="RULE_FILE_PARSEABLE",
            rule_name="File Parseability Verification",
            outcome="FAIL",
            severity="CRITICAL",
            explanation=f"Input stream is corrupted or not a valid PDF structure: {err_msg}",
            affected_document_ids=[doc.document_id],
            evidence_values={"processing_status": doc.processing_status, "errors": doc.errors},
            requires_human_review=True,
        )
    return ValidationFinding(
        rule_id="RULE_FILE_PARSEABLE",
        rule_name="File Parseability Verification",
        outcome="PASS",
        severity="INFO",
        explanation="Document file stream successfully parsed.",
        affected_document_ids=[doc.document_id],
        evidence_values={"processing_status": doc.processing_status},
        requires_human_review=False,
    )


def rule_schema_conformance(doc: ExtractionResult) -> ValidationFinding:
    """Verify that extraction payload satisfies canonical structure and field types."""
    return ValidationFinding(
        rule_id="RULE_SCHEMA_CONFORMANCE",
        rule_name="Payload Schema Conformance",
        outcome="PASS",
        severity="INFO",
        explanation="Extraction output payload strictly conforms to canonical contract schema.",
        affected_document_ids=[doc.document_id],
        evidence_values={"field_count": len(doc.fields), "table_count": len(doc.table_data)},
        requires_human_review=False,
    )


def rule_required_academic_year(doc: ExtractionResult) -> ValidationFinding:
    """
    Verify that mandatory academic_year field is present in approval/disclosure documents.

    A missing field produces FAIL ONLY when:
    1. The document type is confidently known to require it (aicte_eoa, aicte_mandatory_disclosure).
    2. Extraction completed reliably without fatal processing errors, unparsed pages, or uncertainty.

    If document type is unknown/generic, or extraction was incomplete/uncertain, outcome is INCONCLUSIVE.
    Note: A missing mapped field does not necessarily prove that the physical source document lacks the information.
    """
    # 1. Unknown or generic document types
    if not doc.document_type or doc.document_type in ("unknown", "generic"):
        return ValidationFinding(
            rule_id="RULE_REQ_ACADEMIC_YEAR",
            rule_name="Mandatory Academic Year Presence",
            outcome="INCONCLUSIVE",
            severity="LOW",
            explanation="Document type is unknown or generic; mandatory field requirements cannot be established deterministically. Note: a missing mapped field does not necessarily prove that the source document lacks the information.",
            affected_document_ids=[doc.document_id],
            requires_human_review=True,
        )

    # 2. Document types where academic_year is not required
    if doc.document_type not in ("aicte_eoa", "aicte_mandatory_disclosure"):
        return ValidationFinding(
            rule_id="RULE_REQ_ACADEMIC_YEAR",
            rule_name="Mandatory Academic Year Presence",
            outcome="PASS",
            severity="INFO",
            explanation=f"Academic year is not mandatory for document type '{doc.document_type}'.",
            affected_document_ids=[doc.document_id],
            requires_human_review=False,
        )

    ev = doc.fields.get("academic_year")

    # 3. Missing evidence or unnormalized raw text
    if ev is None or ev.normalized_value is None:
        # Check if extraction was incomplete, failed, or flagged uncertain
        is_incomplete = (
            doc.processing_status in ("EXTRACTION_ERROR", "SUCCESS_WITH_UNCERTAINTY", "NEEDS_HUMAN_REVIEW")
            or len(doc.errors) > 0
            or (doc.processing_metadata is not None and doc.processing_metadata.processed_pages < doc.processing_metadata.total_pages)
        )
        if is_incomplete:
            return ValidationFinding(
                rule_id="RULE_REQ_ACADEMIC_YEAR",
                rule_name="Mandatory Academic Year Presence",
                outcome="INCONCLUSIVE",
                severity="MEDIUM",
                explanation="Mandatory field 'academic_year' was not extracted, but document extraction was incomplete, failed, or flagged uncertain. Note: a missing mapped field does not necessarily prove that the source document lacks the information.",
                affected_document_ids=[doc.document_id],
                affected_fields=["academic_year"],
                evidence_values={"academic_year": None, "processing_status": doc.processing_status},
                requires_human_review=True,
            )

        # If raw text was extracted but could not be normalized
        if ev is not None and ev.raw_value is not None:
            return ValidationFinding(
                rule_id="RULE_REQ_ACADEMIC_YEAR",
                rule_name="Mandatory Academic Year Presence",
                outcome="INCONCLUSIVE",
                severity="MEDIUM",
                explanation=f"Academic year raw text '{ev.raw_value}' could not be normalized reliably. Note: a missing or uncertain mapped field does not prove that the source document lacks the information.",
                affected_document_ids=[doc.document_id],
                affected_fields=["academic_year"],
                evidence_values={"raw_value": ev.raw_value, "confidence": ev.confidence},
                requires_human_review=True,
            )

        # Confidently known type and clean extraction, but field was omitted
        return ValidationFinding(
            rule_id="RULE_REQ_ACADEMIC_YEAR",
            rule_name="Mandatory Academic Year Presence",
            outcome="FAIL",
            severity="HIGH",
            explanation="Mandatory field 'academic_year' missing from document payload. Note: a missing mapped field fails digital verification but does not necessarily prove that the source document lacks the information.",
            affected_document_ids=[doc.document_id],
            affected_fields=["academic_year"],
            evidence_values={"academic_year": None},
            requires_human_review=False,
        )

    # 4. Uncertain extracted evidence (low confidence OCR or explicit uncertainty flag)
    if ev.is_uncertain or (ev.confidence is not None and ev.confidence < 0.65):
        return ValidationFinding(
            rule_id="RULE_REQ_ACADEMIC_YEAR",
            rule_name="Mandatory Academic Year Presence",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"Academic year extracted as '{ev.normalized_value or ev.raw_value}' but evidence is uncertain or low-confidence ({ev.uncertainty_reason or f'confidence={ev.confidence}'}). Note: a missing or uncertain mapped field does not prove that the source document lacks the information.",
            affected_document_ids=[doc.document_id],
            affected_fields=["academic_year"],
            evidence_values={"raw_value": ev.raw_value, "normalized_value": ev.normalized_value, "confidence": ev.confidence},
            requires_human_review=True,
        )

    # 5. Clean, verified academic year
    return ValidationFinding(
        rule_id="RULE_REQ_ACADEMIC_YEAR",
        rule_name="Mandatory Academic Year Presence",
        outcome="PASS",
        severity="INFO",
        explanation=f"Mandatory academic year verified: '{ev.normalized_value}'.",
        affected_document_ids=[doc.document_id],
        affected_fields=["academic_year"],
        evidence_values={"raw_value": ev.raw_value, "normalized_value": ev.normalized_value},
        requires_human_review=False,
    )


def rule_format_application_id(doc: ExtractionResult) -> Optional[ValidationFinding]:
    """
    Verify standard AICTE application ID format (e.g. 1-46227285868).

    Distinguishes clearly malformed, confidently extracted values from low-confidence or uncertain OCR values.
    Uncertain OCR text is never treated as definitive proof of invalidity.
    """
    ev = doc.fields.get("application_id")
    if ev is None or ev.raw_value is None:
        return None  # Field absent, handled by presence rule if mandatory

    raw = str(ev.raw_value).strip()
    norm = str(ev.normalized_value).strip() if ev.normalized_value else raw

    loose_valid_pattern = r"^[1-9]-[0-9]+$"

    # 1. Check if extraction is uncertain or low-confidence OCR
    is_ocr_uncertain = (ev.extraction_method == "ocr" and ev.confidence is not None and ev.confidence < 0.65)
    if is_ocr_uncertain or (ev.extraction_method == "ocr" and ev.is_uncertain):
        # Do not treat uncertain OCR text as definitive proof of invalidity
        return ValidationFinding(
            rule_id="RULE_FORMAT_APP_ID",
            rule_name="Application ID Format Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"Application ID '{raw}' cannot be verified deterministically due to low-confidence or uncertain OCR extraction ({ev.uncertainty_reason or f'confidence={ev.confidence}'}). Raw text preserved for human adjudication.",
            affected_document_ids=[doc.document_id],
            affected_fields=["application_id"],
            evidence_values={"raw_value": raw, "normalized_value": norm, "confidence": ev.confidence},
            requires_human_review=True,
        )

    # 2. If confidently extracted (digital or high-confidence OCR) and malformed
    if not re.match(loose_valid_pattern, norm):
        return ValidationFinding(
            rule_id="RULE_FORMAT_APP_ID",
            rule_name="Application ID Format Verification",
            outcome="FAIL",
            severity="MEDIUM",
            explanation=f"Application ID '{raw}' violates pattern '^1-[0-9]{{11}}$'",
            affected_document_ids=[doc.document_id],
            affected_fields=["application_id"],
            evidence_values={"raw_value": raw, "normalized_value": norm},
            requires_human_review=False,
        )

    # 3. If matches pattern but flagged uncertain
    if ev.is_uncertain:
        return ValidationFinding(
            rule_id="RULE_FORMAT_APP_ID",
            rule_name="Application ID Format Verification",
            outcome="INCONCLUSIVE",
            severity="LOW",
            explanation=f"Application ID '{norm}' matches format but is flagged uncertain: {ev.uncertainty_reason}",
            affected_document_ids=[doc.document_id],
            affected_fields=["application_id"],
            evidence_values={"raw_value": raw, "normalized_value": norm},
            requires_human_review=True,
        )

    return ValidationFinding(
        rule_id="RULE_FORMAT_APP_ID",
        rule_name="Application ID Format Verification",
        outcome="PASS",
        severity="INFO",
        explanation=f"Application ID '{norm}' adheres to valid AICTE format.",
        affected_document_ids=[doc.document_id],
        affected_fields=["application_id"],
        evidence_values={"raw_value": raw, "normalized_value": norm},
        requires_human_review=False,
    )


def rule_format_permanent_id(doc: ExtractionResult) -> Optional[ValidationFinding]:
    """
    Verify standard Permanent Institute ID format.

    Distinguishes clearly malformed, confidently extracted values from low-confidence or uncertain OCR values.
    Uncertain OCR text is never treated as definitive proof of invalidity.
    """
    ev = doc.fields.get("permanent_institute_id")
    if ev is None or ev.raw_value is None:
        return None

    raw = str(ev.raw_value).strip()
    norm = str(ev.normalized_value).strip() if ev.normalized_value else raw
    valid_pattern = r"^[1-9]-[0-9]+$"

    # 1. Distinguish low-confidence or uncertain OCR values
    is_ocr_uncertain = (ev.extraction_method == "ocr" and ev.confidence is not None and ev.confidence < 0.65)
    if is_ocr_uncertain or ev.is_uncertain:
        return ValidationFinding(
            rule_id="RULE_FORMAT_PERM_ID",
            rule_name="Permanent Institute ID Format Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"Permanent Institute ID '{raw}' cannot be verified deterministically due to low-confidence or uncertain OCR extraction ({ev.uncertainty_reason or f'confidence={ev.confidence}'}). Raw text preserved for human adjudication.",
            affected_document_ids=[doc.document_id],
            affected_fields=["permanent_institute_id"],
            evidence_values={"raw_value": raw, "normalized_value": norm, "confidence": ev.confidence},
            requires_human_review=True,
        )

    # 2. Confidently extracted but malformed
    if not re.match(valid_pattern, norm):
        return ValidationFinding(
            rule_id="RULE_FORMAT_PERM_ID",
            rule_name="Permanent Institute ID Format Verification",
            outcome="FAIL",
            severity="MEDIUM",
            explanation=f"Permanent Institute ID '{norm}' violates expected format pattern '^[1-9]-[0-9]+$'.",
            affected_document_ids=[doc.document_id],
            affected_fields=["permanent_institute_id"],
            evidence_values={"raw_value": raw, "normalized_value": norm},
            requires_human_review=False,
        )

    return ValidationFinding(
        rule_id="RULE_FORMAT_PERM_ID",
        rule_name="Permanent Institute ID Format Verification",
        outcome="PASS",
        severity="INFO",
        explanation=f"Permanent Institute ID '{norm}' conforms to format.",
        affected_document_ids=[doc.document_id],
        affected_fields=["permanent_institute_id"],
        evidence_values={"normalized_value": norm},
        requires_human_review=False,
    )


def rule_date_range_valid(doc: ExtractionResult) -> Optional[ValidationFinding]:
    """
    Verify that accreditation valid_to date is strictly after valid_from date.
    
    Distinguishes confident violations from low-confidence or uncertain OCR values.
    """
    ev_from = doc.fields.get("valid_from")
    ev_to = doc.fields.get("valid_to")

    if ev_from is None or ev_to is None:
        return None

    norm_from = ev_from.normalized_value
    norm_to = ev_to.normalized_value

    if not norm_from or not norm_to:
        return ValidationFinding(
            rule_id="RULE_DATE_RANGE_INVALID",
            rule_name="Validity Period Chronological Verification",
            outcome="INCONCLUSIVE",
            severity="LOW",
            explanation="One or both validity dates could not be normalized to ISO format; interval cannot be verified. Raw dates preserved for human review.",
            affected_document_ids=[doc.document_id],
            affected_fields=["valid_from", "valid_to"],
            evidence_values={"raw_valid_from": ev_from.raw_value, "raw_valid_to": ev_to.raw_value},
            requires_human_review=True,
        )

    try:
        d_from = datetime.strptime(str(norm_from), "%Y-%m-%d")
        d_to = datetime.strptime(str(norm_to), "%Y-%m-%d")
    except ValueError:
        return ValidationFinding(
            rule_id="RULE_DATE_RANGE_INVALID",
            rule_name="Validity Period Chronological Verification",
            outcome="INCONCLUSIVE",
            severity="LOW",
            explanation=f"Unrecognized date format for valid_from ('{norm_from}') or valid_to ('{norm_to}'). Raw dates preserved for human review.",
            affected_document_ids=[doc.document_id],
            affected_fields=["valid_from", "valid_to"],
            evidence_values={"raw_valid_from": ev_from.raw_value, "raw_valid_to": ev_to.raw_value},
            requires_human_review=True,
        )

    # Do not treat uncertain OCR text as definitive proof of date invalidity
    if (ev_from.is_uncertain or ev_to.is_uncertain or
        (ev_from.confidence is not None and ev_from.confidence < 0.65) or
        (ev_to.confidence is not None and ev_to.confidence < 0.65)):
        return ValidationFinding(
            rule_id="RULE_DATE_RANGE_INVALID",
            rule_name="Validity Period Chronological Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation="Validity dates cannot be verified chronologically due to uncertain or low-confidence OCR extraction. Raw dates preserved for human review.",
            affected_document_ids=[doc.document_id],
            affected_fields=["valid_from", "valid_to"],
            evidence_values={
                "raw_valid_from": ev_from.raw_value,
                "raw_valid_to": ev_to.raw_value,
                "norm_valid_from": norm_from,
                "norm_valid_to": norm_to,
            },
            requires_human_review=True,
        )

    if d_to < d_from:
        return ValidationFinding(
            rule_id="RULE_DATE_RANGE_INVALID",
            rule_name="Validity Period Chronological Verification",
            outcome="FAIL",
            severity="HIGH",
            explanation=f"Accreditation valid_to '{norm_to}' is earlier than valid_from '{norm_from}'",
            affected_document_ids=[doc.document_id],
            affected_fields=["valid_from", "valid_to"],
            evidence_values={"valid_from": norm_from, "valid_to": norm_to},
            requires_human_review=False,
        )

    return ValidationFinding(
        rule_id="RULE_DATE_RANGE_INVALID",
        rule_name="Validity Period Chronological Verification",
        outcome="PASS",
        severity="INFO",
        explanation=f"Validity interval verified: from {norm_from} to {norm_to}.",
        affected_document_ids=[doc.document_id],
        affected_fields=["valid_from", "valid_to"],
        evidence_values={"valid_from": norm_from, "valid_to": norm_to},
        requires_human_review=False,
    )


def rule_cgpa_range(doc: ExtractionResult) -> Optional[ValidationFinding]:
    """Verify that CGPA falls within regulatory scale boundaries (0.0 to 4.0 or 10.0)."""
    ev = doc.fields.get("cgpa")
    if ev is None or ev.normalized_value is None:
        return None

    try:
        val = float(ev.normalized_value)
    except (ValueError, TypeError):
        return ValidationFinding(
            rule_id="RULE_CGPA_RANGE",
            rule_name="CGPA Regulatory Bound Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"CGPA value '{ev.normalized_value}' cannot be coerced to float.",
            affected_document_ids=[doc.document_id],
            affected_fields=["cgpa"],
            requires_human_review=True,
        )

    if val < 0.0 or val > 10.0:
        return ValidationFinding(
            rule_id="RULE_CGPA_RANGE",
            rule_name="CGPA Regulatory Bound Verification",
            outcome="FAIL",
            severity="HIGH",
            explanation=f"CGPA value {val} is outside valid regulatory bounds [0.0 - 10.0].",
            affected_document_ids=[doc.document_id],
            affected_fields=["cgpa"],
            evidence_values={"cgpa": val},
            requires_human_review=False,
        )

    if ev.is_uncertain:
        return ValidationFinding(
            rule_id="RULE_CGPA_RANGE",
            rule_name="CGPA Regulatory Bound Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"CGPA value {val} is within bounds, but extraction evidence is uncertain: {ev.uncertainty_reason}",
            affected_document_ids=[doc.document_id],
            affected_fields=["cgpa"],
            evidence_values={"cgpa": val, "raw_value": ev.raw_value, "confidence": ev.confidence},
            requires_human_review=True,
        )

    return ValidationFinding(
        rule_id="RULE_CGPA_RANGE",
        rule_name="CGPA Regulatory Bound Verification",
        outcome="PASS",
        severity="INFO",
        explanation=f"CGPA value {val} is within valid regulatory range.",
        affected_document_ids=[doc.document_id],
        affected_fields=["cgpa"],
        evidence_values={"cgpa": val},
        requires_human_review=False,
    )


def rule_grade_validity(doc: ExtractionResult) -> Optional[ValidationFinding]:
    """
    Verify NAAC accreditation grade is recognized in regulatory framework.

    Distinguishes clearly malformed values from low-confidence OCR and unknown/unsupported grade schemes.
    Unknown grade schemes or low-confidence extractions produce INCONCLUSIVE rather than FAIL, preserving raw evidence.
    """
    ev = doc.fields.get("accreditation_grade")
    if ev is None or ev.normalized_value is None:
        return None

    raw_val = str(ev.raw_value).strip() if ev.raw_value else str(ev.normalized_value).strip()
    grade = str(ev.normalized_value).strip().upper()

    # 1. Low-confidence OCR or uncertain extraction -> INCONCLUSIVE
    if ev.is_uncertain or (ev.confidence is not None and ev.confidence < 0.65):
        return ValidationFinding(
            rule_id="RULE_GRADE_VALIDITY",
            rule_name="Accreditation Grade Scale Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"Accreditation grade '{raw_val}' is uncertain or low-confidence ({ev.uncertainty_reason or f'confidence={ev.confidence}'}); cannot verify scale deterministically.",
            affected_document_ids=[doc.document_id],
            affected_fields=["accreditation_grade"],
            evidence_values={"raw_value": raw_val, "normalized_value": grade, "confidence": ev.confidence},
            requires_human_review=True,
        )

    # 2. Standard recognized NAAC letter grade scale (A++ to D)
    valid_grades = {"A++", "A+", "A", "B++", "B+", "B", "C", "D"}
    if grade in valid_grades:
        return ValidationFinding(
            rule_id="RULE_GRADE_VALIDITY",
            rule_name="Accreditation Grade Scale Verification",
            outcome="PASS",
            severity="INFO",
            explanation=f"Accreditation grade '{grade}' is recognized in official regulatory scale.",
            affected_document_ids=[doc.document_id],
            affected_fields=["accreditation_grade"],
            evidence_values={"grade": grade, "raw_value": raw_val},
            requires_human_review=False,
        )

    # 3. Non-standard, historical (e.g. 5-star, points, PASS/FAIL), or unsupported grade format
    # Emits INCONCLUSIVE to avoid falsely failing valid historical or alternate regulatory schemes
    return ValidationFinding(
        rule_id="RULE_GRADE_VALIDITY",
        rule_name="Accreditation Grade Scale Verification",
        outcome="INCONCLUSIVE",
        severity="MEDIUM",
        explanation=f"Accreditation grade '{raw_val}' does not match standard NAAC letter scale (A++ to D). May reflect an unsupported, historical, or alternate grade scheme requiring official adjudication.",
        affected_document_ids=[doc.document_id],
        affected_fields=["accreditation_grade"],
        evidence_values={"raw_value": raw_val, "normalized_value": grade},
        requires_human_review=True,
    )


def rule_ocr_confidence_threshold(doc: ExtractionResult) -> ValidationFinding:
    """Flag values extracted via OCR where engine confidence is below 0.65 threshold."""
    low_conf_fields: List[Dict[str, Any]] = []

    for name, ev in doc.fields.items():
        if ev.extraction_method == "ocr" and ev.confidence is not None:
            if ev.confidence < 0.65:
                low_conf_fields.append({
                    "field": name,
                    "confidence": ev.confidence,
                    "raw_value": ev.raw_value,
                })

    if low_conf_fields:
        first = low_conf_fields[0]
        field_names = [f["field"] for f in low_conf_fields]
        return ValidationFinding(
            rule_id="RULE_OCR_CONFIDENCE_THRESHOLD",
            rule_name="OCR Recognition Confidence Threshold",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"{first['field'].upper()} field extracted with low confidence ({first['confidence']:.2f} < 0.65 threshold)",
            affected_document_ids=[doc.document_id],
            affected_fields=field_names,
            evidence_values={"low_confidence_fields": low_conf_fields},
            requires_human_review=True,
        )

    return ValidationFinding(
        rule_id="RULE_OCR_CONFIDENCE_THRESHOLD",
        rule_name="OCR Recognition Confidence Threshold",
        outcome="PASS",
        severity="INFO",
        explanation="All OCR-extracted fields meet or exceed the 0.65 confidence threshold (or extracted digitally).",
        affected_document_ids=[doc.document_id],
        requires_human_review=False,
    )


def rule_ambiguous_evidence(doc: ExtractionResult) -> ValidationFinding:
    """Flag ambiguous evidence or conflicting candidates extracted from the document."""
    uncertain_fields: List[Dict[str, Any]] = []

    for name, ev in doc.fields.items():
        if ev.is_uncertain:
            uncertain_fields.append({
                "field": name,
                "reason": ev.uncertainty_reason or "Ambiguous extraction",
                "raw_value": ev.raw_value,
                "normalized_value": ev.normalized_value,
            })

    if uncertain_fields:
        first = uncertain_fields[0]
        field_names = [f["field"] for f in uncertain_fields]
        return ValidationFinding(
            rule_id="RULE_AMBIGUOUS_EVIDENCE",
            rule_name="Extraction Ambiguity and Uncertainty Check",
            outcome="INCONCLUSIVE",
            severity="HIGH",
            explanation=f"Ambiguous or conflicting evidence detected for field '{first['field']}': {first['reason']}",
            affected_document_ids=[doc.document_id],
            affected_fields=field_names,
            evidence_values={"uncertain_fields": uncertain_fields},
            requires_human_review=True,
        )

    return ValidationFinding(
        rule_id="RULE_AMBIGUOUS_EVIDENCE",
        rule_name="Extraction Ambiguity and Uncertainty Check",
        outcome="PASS",
        severity="INFO",
        explanation="No conflicting candidates or ambiguous extractions flagged.",
        affected_document_ids=[doc.document_id],
        requires_human_review=False,
    )
