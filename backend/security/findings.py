"""
backend/security/findings.py - Normalized Findings Interface for SIH26261 (Person 3).
Normalizes and aggregates findings across Compliance, Authenticity, Privacy, and Consistency.
Consumed by Person 4 for reviewer dashboard and JSON responses.
"""

from typing import List, Literal, Optional
from backend.common.models import (
    DocumentValidationReport,
    NormalizedFinding,
    ReviewerSummary,
    ValidationFinding,
)


def normalize_finding(
    finding: ValidationFinding,
    category: Literal["COMPLIANCE", "AUTHENTICITY", "PRIVACY", "CONSISTENCY"] = "COMPLIANCE",
    prefix: str = "FINDING",
    index: int = 1,
) -> NormalizedFinding:
    """Transform a generic ValidationFinding into a standardized NormalizedFinding."""
    return NormalizedFinding(
        finding_id=f"{prefix}_{index:03d}_{finding.rule_id}",
        category=category,
        rule_id=finding.rule_id,
        rule_name=finding.rule_name,
        outcome=finding.outcome,
        severity=finding.severity,
        explanation=finding.explanation,
        affected_document_ids=finding.affected_document_ids,
        affected_fields=finding.affected_fields,
        evidence_values=finding.evidence_values,
        requires_human_review=finding.requires_human_review,
        timestamp_utc=finding.timestamp_utc,
    )


class FindingsNormalizer:
    """
    Orchestrates finding normalization and computes the high-level ReviewerSummary.
    """

    @classmethod
    def aggregate_and_normalize(
        cls,
        compliance_findings: Optional[List[ValidationFinding]] = None,
        authenticity_findings: Optional[List[ValidationFinding]] = None,
        privacy_findings: Optional[List[ValidationFinding]] = None,
        consistency_findings: Optional[List[ValidationFinding]] = None,
    ) -> List[NormalizedFinding]:
        """Merge and standardize findings from all pipeline phases."""
        normalized: List[NormalizedFinding] = []
        counter = 1

        for f in (compliance_findings or []):
            normalized.append(normalize_finding(f, category="COMPLIANCE", prefix="COMP", index=counter))
            counter += 1

        for f in (authenticity_findings or []):
            normalized.append(normalize_finding(f, category="AUTHENTICITY", prefix="AUTH", index=counter))
            counter += 1

        for f in (privacy_findings or []):
            normalized.append(normalize_finding(f, category="PRIVACY", prefix="PRIV", index=counter))
            counter += 1

        for f in (consistency_findings or []):
            normalized.append(normalize_finding(f, category="CONSISTENCY", prefix="CONS", index=counter))
            counter += 1

        return normalized

    @classmethod
    def compute_reviewer_summary(
        cls,
        normalized_findings: List[NormalizedFinding],
        validation_report: Optional[DocumentValidationReport] = None,
    ) -> ReviewerSummary:
        """Calculate executive statistics and status for the reviewer dashboard."""
        summary = ReviewerSummary()
        summary.total_rules_evaluated = len(normalized_findings)

        has_critical_or_fail = False
        has_inconclusive = False
        requires_review = False

        for f in normalized_findings:
            if f.outcome == "PASS":
                summary.passed_rules += 1
            elif f.outcome == "FAIL":
                summary.failed_rules += 1
                has_critical_or_fail = True
            elif f.outcome == "INCONCLUSIVE":
                summary.inconclusive_rules += 1
                has_inconclusive = True

            if f.severity == "CRITICAL":
                summary.critical_findings += 1
                has_critical_or_fail = True
            elif f.severity == "HIGH":
                summary.high_findings += 1
            elif f.severity == "MEDIUM":
                summary.medium_findings += 1
            elif f.severity == "LOW":
                summary.low_findings += 1
            elif f.severity == "INFO":
                summary.info_findings += 1

            if f.category == "AUTHENTICITY" and f.outcome != "PASS":
                summary.authenticity_signals_count += 1
            if f.category == "PRIVACY" and f.rule_id == "PRIV_PII_REDACTED":
                summary.privacy_redactions_count += 1

            if f.requires_human_review:
                requires_review = True

        if validation_report and validation_report.requires_human_review:
            requires_review = True

        # Determine Overall Status
        if has_critical_or_fail and summary.critical_findings > 0:
            summary.overall_status = "ACTION_REQUIRED"
        elif requires_review or has_inconclusive:
            summary.overall_status = "NEEDS_HUMAN_REVIEW"
        elif summary.failed_rules > 0:
            summary.overall_status = "ACTION_REQUIRED"
        else:
            summary.overall_status = "VERIFIED"

        summary.requires_human_review = requires_review
        return summary
