"""
src/validators/schemas.py - Pydantic models for deterministic validation findings and reports.
Adheres to SIH26261 decision-support requirements:
- Distinguishes PASS, FAIL, and INCONCLUSIVE outcomes.
- Never treats missing or uncertain evidence as definitive proof of failure.
- Every finding includes stable rule ID, severity, clear explanation, document/field references, and evidence values.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

RuleOutcome = Literal["PASS", "FAIL", "INCONCLUSIVE"]
RuleSeverity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


class ValidationFinding(BaseModel):
    """
    Individual deterministic rule finding emitted during document validation
    or cross-document consistency checks.
    """
    rule_id: str = Field(description="Stable rule identifier (e.g. 'RULE_REQ_ACADEMIC_YEAR').")
    rule_name: str = Field(description="Human-readable rule title.")
    outcome: RuleOutcome = Field(description="Evaluation result: PASS, FAIL, or INCONCLUSIVE.")
    severity: RuleSeverity = Field(description="Finding severity level: INFO, LOW, MEDIUM, HIGH, CRITICAL.")
    explanation: str = Field(description="Detailed human-readable explanation of why this finding was produced.")
    affected_document_ids: List[str] = Field(
        default_factory=list,
        description="List of document IDs evaluated by this rule."
    )
    affected_fields: List[str] = Field(
        default_factory=list,
        description="Names of specific fields evaluated or flagged (e.g. 'academic_year', 'application_id')."
    )
    evidence_values: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value dictionary capturing the exact extracted/normalized evidence values evaluated."
    )
    requires_human_review: bool = Field(
        default=False,
        description="True if finding requires adjudication by a human regulatory official."
    )
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of rule evaluation in ISO 8601 format."
    )


class DocumentValidationReport(BaseModel):
    """
    Comprehensive validation report for a single document.
    Collects all field-level and document-level rule evaluation findings.
    """
    document_id: str = Field(description="ID of the validated document.")
    document_type: str = Field(description="Type of the validated document (e.g. 'aicte_eoa').")
    overall_outcome: RuleOutcome = Field(description="Consolidated outcome: FAIL if any FAIL, else INCONCLUSIVE if any INCONCLUSIVE, else PASS.")
    findings: List[ValidationFinding] = Field(default_factory=list, description="List of rule findings.")
    summary: Dict[str, int] = Field(default_factory=dict, description="Summary counters for outcomes and severities.")
    requires_human_review: bool = Field(
        default=False,
        description="True if any finding indicates a need for manual human review."
    )

    @classmethod
    def create(
        cls,
        document_id: str,
        document_type: str,
        findings: List[ValidationFinding],
    ) -> "DocumentValidationReport":
        has_fail = any(f.outcome == "FAIL" for f in findings)
        has_inconclusive = any(f.outcome == "INCONCLUSIVE" for f in findings)

        if has_fail:
            overall = "FAIL"
        elif has_inconclusive:
            overall = "INCONCLUSIVE"
        else:
            overall = "PASS"

        summary = {
            "total_rules": len(findings),
            "pass": sum(1 for f in findings if f.outcome == "PASS"),
            "fail": sum(1 for f in findings if f.outcome == "FAIL"),
            "inconclusive": sum(1 for f in findings if f.outcome == "INCONCLUSIVE"),
            "critical": sum(1 for f in findings if f.severity == "CRITICAL"),
            "high": sum(1 for f in findings if f.severity == "HIGH"),
            "medium": sum(1 for f in findings if f.severity == "MEDIUM"),
            "low": sum(1 for f in findings if f.severity == "LOW"),
            "info": sum(1 for f in findings if f.severity == "INFO"),
        }
        human_review = any(f.requires_human_review for f in findings) or (overall != "PASS")

        return cls(
            document_id=document_id,
            document_type=document_type,
            overall_outcome=overall,
            findings=findings,
            summary=summary,
            requires_human_review=human_review,
        )


class CrossDocumentConsistencyReport(BaseModel):
    """
    Consolidated report for multi-document consistency comparisons.
    Collects cross-document identity, timeline, and intake consistency findings.
    """
    compared_document_ids: List[str] = Field(description="List of document IDs involved in consistency checks.")
    overall_outcome: RuleOutcome = Field(description="Consolidated consistency outcome: FAIL, INCONCLUSIVE, or PASS.")
    findings: List[ValidationFinding] = Field(default_factory=list, description="Cross-document rule findings.")
    summary: Dict[str, int] = Field(default_factory=dict, description="Summary counters.")
    requires_human_review: bool = Field(
        default=False,
        description="True if any cross-document finding requires human adjudication."
    )

    @classmethod
    def create(
        cls,
        compared_document_ids: List[str],
        findings: List[ValidationFinding],
    ) -> "CrossDocumentConsistencyReport":
        has_fail = any(f.outcome == "FAIL" for f in findings)
        has_inconclusive = any(f.outcome == "INCONCLUSIVE" for f in findings)

        if has_fail:
            overall = "FAIL"
        elif has_inconclusive:
            overall = "INCONCLUSIVE"
        else:
            overall = "PASS"

        summary = {
            "total_checks": len(findings),
            "pass": sum(1 for f in findings if f.outcome == "PASS"),
            "fail": sum(1 for f in findings if f.outcome == "FAIL"),
            "inconclusive": sum(1 for f in findings if f.outcome == "INCONCLUSIVE"),
            "critical": sum(1 for f in findings if f.severity == "CRITICAL"),
            "high": sum(1 for f in findings if f.severity == "HIGH"),
            "medium": sum(1 for f in findings if f.severity == "MEDIUM"),
            "low": sum(1 for f in findings if f.severity == "LOW"),
            "info": sum(1 for f in findings if f.severity == "INFO"),
        }
        human_review = any(f.requires_human_review for f in findings) or (overall != "PASS")

        return cls(
            compared_document_ids=compared_document_ids,
            overall_outcome=overall,
            findings=findings,
            summary=summary,
            requires_human_review=human_review,
        )
