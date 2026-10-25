"""
backend/tests/test_findings.py - Comprehensive Unit Tests for Person 3 Unified Findings Engine.

Covers:
1. Normalization of existing Pydantic findings and compatible dictionaries.
2. Invalid, empty, and incomplete finding inputs.
3. Deduplication of identical findings.
4. Preservation of genuinely distinct findings with the same rule ID.
5. Evidence merging without losing source references.
6. Stable ordering and priority ranking across repeated runs.
7. Correct summary counters by severity and outcome.
8. Human-review aggregation.
9. Correct handling of INCONCLUSIVE vs FAIL results.
10. Non-destructive invariants: no mutation of source finding objects.
11. Privacy-safe report summaries (redaction of PII in explanations and evidence).
12. End-to-end compatibility with authenticity and cross-document validation reports.
13. Duplicate hash deduplication between upstream validation and authenticity modules.
"""

from copy import deepcopy
import pytest

from backend.security.findings import (
    UnifiedFindingsEngine,
    UnifiedFindingsReport,
    compute_dedup_key,
    deduplicate_findings,
    filter_report_for_privacy,
    normalize_finding,
    prioritize_findings,
    unify_findings,
)
from backend.security.authenticity import DocumentAuthenticityReport
from backend.security.privacy import PrivacyPurpose
from dataset.src.validators.schemas import ValidationFinding, DocumentValidationReport, CrossDocumentConsistencyReport


# ==============================================================================
# 1. Normalization Tests
# ==============================================================================


def test_normalize_pydantic_finding():
    """Verify clean normalization and deep-copying of a ValidationFinding instance."""
    original = ValidationFinding(
        rule_id="RULE_REQ_ACADEMIC_YEAR",
        rule_name="Mandatory Academic Year Presence",
        outcome="FAIL",
        severity="HIGH",
        explanation="Mandatory field 'academic_year' missing from document payload",
        affected_document_ids=["DOC_001"],
        affected_fields=["academic_year"],
        evidence_values={"academic_year": None},
        requires_human_review=True,
    )
    norm = normalize_finding(original)
    assert norm is not None
    assert norm.rule_id == original.rule_id
    assert norm.outcome == "FAIL"
    assert norm.severity == "HIGH"
    # Ensure it is a distinct copy
    assert norm is not original
    norm.explanation = "Modified"
    assert original.explanation != "Modified"


def test_normalize_dictionary_finding():
    """Verify conversion of compatible dictionary finding payloads."""
    payload = {
        "rule_id": "RULE_FORMAT_APP_ID",
        "rule_name": "Application ID Regex Format",
        "outcome": "fail",  # Lowercase normalized to uppercase
        "severity": "medium",
        "message": "Application ID 'INVALID' violates format",
        "affected_document_ids": "DOC_002",  # Single string coerced to list
        "affected_fields": "application_id",
        "evidence_values": {"raw": "INVALID"},
    }
    norm = normalize_finding(payload)
    assert norm is not None
    assert norm.rule_id == "RULE_FORMAT_APP_ID"
    assert norm.outcome == "FAIL"
    assert norm.severity == "MEDIUM"
    assert norm.affected_document_ids == ["DOC_002"]
    assert norm.affected_fields == ["application_id"]
    assert norm.requires_human_review is True  # FAIL automatically sets requires_human_review


def test_normalize_invalid_and_incomplete_inputs():
    """Verify graceful handling of None, empty dicts, and unexpected structures."""
    assert normalize_finding(None) is None

    empty_dict = normalize_finding({})
    assert empty_dict is not None
    assert empty_dict.rule_id == "RULE_UNKNOWN"
    assert empty_dict.outcome == "INCONCLUSIVE"
    assert empty_dict.requires_human_review is True

    # Unknown outcome or severity values fallback safely
    bad_enums = normalize_finding({"outcome": "UNKNOWN_VAL", "severity": "EXTREME"})
    assert bad_enums.outcome == "INCONCLUSIVE"
    assert bad_enums.severity == "MEDIUM"


# ==============================================================================
# 2. Deduplication & Evidence Merging Tests
# ==============================================================================


def test_deduplicate_identical_findings():
    """Verify that multiple emissions of the exact same finding collapse into one."""
    f1 = ValidationFinding(
        rule_id="RULE_INTEGRITY_DUPLICATE_HASH",
        rule_name="Duplicate Hash Check",
        outcome="FAIL",
        severity="MEDIUM",
        explanation="Identical hash detected between DOC_A and DOC_B",
        affected_document_ids=["DOC_A", "DOC_B"],
        affected_fields=[],
        evidence_values={"sha256": "abcdef0123456789"},
    )
    # Re-emitted by second pipeline pass
    f2 = deepcopy(f1)

    deduped = deduplicate_findings([f1, f2])
    assert len(deduped) == 1
    assert deduped[0].rule_id == "RULE_INTEGRITY_DUPLICATE_HASH"


def test_preserve_distinct_findings_with_same_rule_id():
    """
    CRITICAL: Verify that genuinely distinct issues sharing a rule_id are NOT merged.
    E.g., two distinct courses with intake violations in the same document bundle.
    """
    f_cse = ValidationFinding(
        rule_id="RULE_CROSS_INTAKE_MISMATCH",
        rule_name="Intake Quota Mismatch",
        outcome="FAIL",
        severity="HIGH",
        explanation="Intake for Computer Science exceeds quota: claimed 180, approved 120",
        affected_document_ids=["DOC_EOA", "DOC_DISCLOSURE"],
        affected_fields=["approved_courses_and_intake"],
        evidence_values={"programme": "Computer Science", "claimed": 180, "approved": 120},
    )
    f_ee = ValidationFinding(
        rule_id="RULE_CROSS_INTAKE_MISMATCH",
        rule_name="Intake Quota Mismatch",
        outcome="FAIL",
        severity="HIGH",
        explanation="Intake for Electrical Engineering exceeds quota: claimed 90, approved 60",
        affected_document_ids=["DOC_EOA", "DOC_DISCLOSURE"],
        affected_fields=["approved_courses_and_intake"],
        evidence_values={"programme": "Electrical Engineering", "claimed": 90, "approved": 60},
    )

    deduped = deduplicate_findings([f_cse, f_ee])
    assert len(deduped) == 2
    programmes = {d.evidence_values.get("programme") for d in deduped}
    assert "Computer Science" in programmes
    assert "Electrical Engineering" in programmes


def test_evidence_merging_on_equivalent_findings():
    """Verify that merging equivalent findings combines evidence values and takes highest severity."""
    f_early = ValidationFinding(
        rule_id="RULE_AUTH_PRODUCER_ANOMALY",
        rule_name="Producer Check",
        outcome="INCONCLUSIVE",
        severity="LOW",
        explanation="Short note",
        affected_document_ids=["DOC_001"],
        evidence_values={"tool": "Canva"},
    )
    f_later = ValidationFinding(
        rule_id="RULE_AUTH_PRODUCER_ANOMALY",
        rule_name="Producer Check",
        outcome="INCONCLUSIVE",
        severity="MEDIUM",  # Higher severity
        explanation="Longer explanation detailing suspicious generator in document metadata.",
        affected_document_ids=["DOC_001"],
        evidence_values={"version": "v2.5"},
    )

    deduped = deduplicate_findings([f_early, f_later])
    assert len(deduped) == 1
    m = deduped[0]
    assert m.severity == "MEDIUM"  # Kept higher severity
    assert "Canva" in m.evidence_values.values()
    assert "v2.5" in m.evidence_values.values()
    assert len(m.explanation) == len(f_later.explanation)


# ==============================================================================
# 3. Prioritization & Ordering Tests
# ==============================================================================


def test_prioritize_findings_order():
    """
    Verify strict priority ranking:
    1. Outcome: FAIL (0) > INCONCLUSIVE (1) > PASS (2)
    2. Severity: CRITICAL (0) > HIGH (1) > MEDIUM (2) > LOW (3) > INFO (4)
    3. Stable rule_id tie-breaker
    """
    f_pass = ValidationFinding(
        rule_id="RULE_SCHEMA_CONFORMANCE",
        rule_name="Schema",
        outcome="PASS",
        severity="INFO",
        explanation="Valid",
    )
    f_crit_fail = ValidationFinding(
        rule_id="RULE_CROSS_INSTITUTION_ID",
        rule_name="ID Mismatch",
        outcome="FAIL",
        severity="CRITICAL",
        explanation="Institution ID mismatch between EoA and Disclosure",
    )
    f_high_fail = ValidationFinding(
        rule_id="RULE_REQ_ACADEMIC_YEAR",
        rule_name="Year",
        outcome="FAIL",
        severity="HIGH",
        explanation="Missing academic year",
    )
    f_med_inconc = ValidationFinding(
        rule_id="RULE_OCR_CONFIDENCE",
        rule_name="OCR Score",
        outcome="INCONCLUSIVE",
        severity="MEDIUM",
        explanation="Low OCR score",
    )

    unordered = [f_pass, f_med_inconc, f_high_fail, f_crit_fail]
    ordered = prioritize_findings(unordered)

    # Order must be: f_crit_fail (FAIL/CRIT), f_high_fail (FAIL/HIGH), f_med_inconc (INCONC/MED), f_pass (PASS/INFO)
    assert ordered[0].rule_id == "RULE_CROSS_INSTITUTION_ID"
    assert ordered[1].rule_id == "RULE_REQ_ACADEMIC_YEAR"
    assert ordered[2].rule_id == "RULE_OCR_CONFIDENCE"
    assert ordered[3].rule_id == "RULE_SCHEMA_CONFORMANCE"


def test_prioritization_stability_across_repeated_runs():
    """Verify identical sorting output over multiple permutations."""
    f1 = ValidationFinding(rule_id="RULE_B", rule_name="B", outcome="FAIL", severity="HIGH", explanation="B")
    f2 = ValidationFinding(rule_id="RULE_A", rule_name="A", outcome="FAIL", severity="HIGH", explanation="A")
    f3 = ValidationFinding(rule_id="RULE_C", rule_name="C", outcome="PASS", severity="INFO", explanation="C")

    res1 = [f.rule_id for f in prioritize_findings([f1, f2, f3])]
    res2 = [f.rule_id for f in prioritize_findings([f3, f1, f2])]
    res3 = [f.rule_id for f in prioritize_findings([f2, f3, f1])]

    assert res1 == res2 == res3 == ["RULE_A", "RULE_B", "RULE_C"]


# ==============================================================================
# 4. Summary & Decision-Support Tests
# ==============================================================================


def test_summary_counters_and_human_review_flag():
    """Verify summary counters and overall outcome calculations."""
    findings = [
        ValidationFinding(rule_id="R1", rule_name="R1", outcome="PASS", severity="INFO", explanation="P1"),
        ValidationFinding(rule_id="R2", rule_name="R2", outcome="PASS", severity="INFO", explanation="P2"),
        ValidationFinding(rule_id="R3", rule_name="R3", outcome="INCONCLUSIVE", severity="LOW", explanation="I1"),
        ValidationFinding(rule_id="R4", rule_name="R4", outcome="FAIL", severity="HIGH", explanation="F1"),
    ]

    report = unify_findings(findings, application_id="APP_2026_TEST")
    assert report.application_id == "APP_2026_TEST"
    assert report.total_findings == 4
    assert report.overall_outcome == "FAIL"
    assert report.requires_human_review is True
    assert report.summary["pass"] == 2
    assert report.summary["fail"] == 1
    assert report.summary["inconclusive"] == 1
    assert report.summary["high"] == 1
    assert report.summary["low"] == 1
    assert report.summary["info"] == 2


def test_inconclusive_outcome_does_not_become_fail():
    """Verify that an inconclusive finding alone yields overall INCONCLUSIVE, not FAIL."""
    findings = [
        ValidationFinding(rule_id="R1", rule_name="R1", outcome="PASS", severity="INFO", explanation="P1"),
        ValidationFinding(rule_id="R2", rule_name="R2", outcome="INCONCLUSIVE", severity="MEDIUM", explanation="I1"),
    ]
    report = unify_findings(findings)
    assert report.overall_outcome == "INCONCLUSIVE"
    assert report.summary["fail"] == 0
    assert report.summary["inconclusive"] == 1
    assert report.requires_human_review is True


def test_all_pass_yields_overall_pass():
    """Verify that all PASS findings produce overall PASS with requires_human_review=False."""
    findings = [
        ValidationFinding(rule_id="R1", rule_name="R1", outcome="PASS", severity="INFO", explanation="P1"),
        ValidationFinding(rule_id="R2", rule_name="R2", outcome="PASS", severity="INFO", explanation="P2"),
    ]
    report = unify_findings(findings)
    assert report.overall_outcome == "PASS"
    assert report.requires_human_review is False
    assert any("Clear" in rec for rec in report.actionable_recommendations)


# ==============================================================================
# 5. Non-Destructive & Privacy Tests
# ==============================================================================


def test_non_destructive_invariants():
    """Verify compiling findings does NOT mutate original finding instances."""
    original = ValidationFinding(
        rule_id="RULE_TEST",
        rule_name="Test",
        outcome="FAIL",
        severity="HIGH",
        explanation="Original explanation",
        affected_document_ids=["DOC_1"],
        evidence_values={"key": "val1"},
    )
    copy_orig = deepcopy(original)

    report = unify_findings([original])
    assert original.model_dump() == copy_orig.model_dump()


def test_privacy_redacted_report_view():
    """Verify privacy filtering redacts PII from explanations, evidence, and recommendations."""
    finding = ValidationFinding(
        rule_id="RULE_PRIVACY_FLAG",
        rule_name="Personal Contact Flag",
        outcome="FAIL",
        severity="MEDIUM",
        explanation="Applicant contact info found: principal@college.ac.in, phone +91 98765 43210",
        evidence_values={
            "email": "principal@college.ac.in",
            "aadhaar": "2345 6789 0123",
            "nested_records": [
                {"officer": "Registrar", "direct_email": "reg@college.ac.in", "code": 101}
            ]
        },
    )
    report = unify_findings([finding])

    # Internal view preserves raw evidence
    raw_view = report.to_reviewer_view(purpose=PrivacyPurpose.INTERNAL_VERIFICATION)
    assert "principal@college.ac.in" in raw_view.findings[0].explanation
    assert raw_view.findings[0].evidence_values["nested_records"][0]["direct_email"] == "reg@college.ac.in"

    # Reviewer view redacts PII even in nested records
    redacted_view = report.to_reviewer_view(purpose=PrivacyPurpose.REVIEWER_VIEW)
    assert "[EMAIL_REDACTED]" in redacted_view.findings[0].explanation
    assert "[PHONE_REDACTED]" in redacted_view.findings[0].explanation
    assert "principal@college.ac.in" not in redacted_view.findings[0].explanation
    assert "[EMAIL_REDACTED]" in redacted_view.findings[0].evidence_values["email"]
    assert "[EMAIL_REDACTED]" in redacted_view.findings[0].evidence_values["nested_records"][0]["direct_email"]
    # Primitives preserved
    assert redacted_view.findings[0].evidence_values["nested_records"][0]["code"] == 101

    # Invariant: original report is still intact
    assert "principal@college.ac.in" in report.findings[0].explanation


# ==============================================================================
# 6. Cross-Module Compatibility Tests
# ==============================================================================


def test_compatibility_with_validation_and_authenticity_reports():
    """Verify ingestion across DocumentValidationReport, ConsistencyReport, and AuthenticityReport."""
    # 1. Validation Report from Person 2
    f_val = ValidationFinding(
        rule_id="RULE_REQ_ACADEMIC_YEAR",
        rule_name="Academic Year",
        outcome="PASS",
        severity="INFO",
        explanation="Year present",
        affected_document_ids=["DOC_001"],
    )
    val_rep = DocumentValidationReport.create("DOC_001", "aicte_eoa", [f_val])

    # 2. Consistency Report from Person 2
    f_cons = ValidationFinding(
        rule_id="RULE_CROSS_INSTITUTION_ID",
        rule_name="ID Alignment",
        outcome="FAIL",
        severity="CRITICAL",
        explanation="ID mismatch",
        affected_document_ids=["DOC_001", "DOC_002"],
    )
    cons_rep = CrossDocumentConsistencyReport.create(["DOC_001", "DOC_002"], [f_cons])

    # 3. Authenticity Report from Person 3
    f_auth = ValidationFinding(
        rule_id="RULE_AUTH_METADATA_VALID",
        rule_name="Metadata Check",
        outcome="PASS",
        severity="INFO",
        explanation="Clean metadata",
        affected_document_ids=["DOC_001"],
    )
    auth_rep = DocumentAuthenticityReport.create("DOC_001", "abcdef", 1024, True, [f_auth])

    # Unified Findings Engine ingests all three reports seamlessly
    unified = unify_findings(val_rep, cons_rep, auth_rep, application_id="APP_SIH_BUNDLE_01")

    assert unified.application_id == "APP_SIH_BUNDLE_01"
    assert unified.total_findings == 3
    assert unified.overall_outcome == "FAIL"  # Because f_cons is FAIL
    assert unified.summary["fail"] == 1
    assert unified.summary["pass"] == 2
    assert unified.summary["critical"] == 1
    assert unified.findings[0].rule_id == "RULE_CROSS_INSTITUTION_ID"  # Critical fail sorted first


def test_duplicate_hash_not_duplicated_between_validation_and_authenticity():
    """
    CRITICAL: Verify that when both the validation engine and the authenticity engine
    evaluate the same duplicate hash, only ONE unified duplicate finding appears.
    """
    dup_f_val = ValidationFinding(
        rule_id="RULE_INTEGRITY_DUPLICATE_HASH",
        rule_name="Deterministic Duplicate Document Hash Verification",
        outcome="FAIL",
        severity="MEDIUM",
        explanation="Document sha256 matches existing submission doc_id 'DOC_001'",
        affected_document_ids=["DOC_002", "DOC_001"],
        evidence_values={"sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"},
    )
    dup_f_auth = ValidationFinding(
        rule_id="RULE_INTEGRITY_DUPLICATE_HASH",
        rule_name="Deterministic Duplicate Document Hash Verification",
        outcome="FAIL",
        severity="MEDIUM",
        explanation="Document sha256 matches existing submission doc_id 'DOC_001'",
        affected_document_ids=["DOC_002", "DOC_001"],
        evidence_values={"sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"},
    )

    unified = unify_findings([dup_f_val], [dup_f_auth])
    # Must be deduplicated to exactly ONE finding
    assert unified.total_findings == 1
    assert unified.findings[0].rule_id == "RULE_INTEGRITY_DUPLICATE_HASH"
    assert unified.summary["fail"] == 1
