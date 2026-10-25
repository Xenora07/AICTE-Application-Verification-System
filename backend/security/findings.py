"""
backend/security/findings.py - Unified Findings Engine for SIH26261 (Stage 8).

Core Principles:
1. Normalization: Ingests findings from deterministic validation, cross-document consistency,
   authenticity/anomaly checks, and privacy gateways, normalizing them into the shared ValidationFinding contract.
2. Deterministic Deduplication: Collapses repeated reports of the exact same underlying issue
   using a stable composite key without merging genuinely distinct issues sharing a rule ID.
3. Prioritization: Ranks findings deterministically by outcome (FAIL > INCONCLUSIVE > PASS)
   and severity (CRITICAL > HIGH > MEDIUM > LOW > INFO) with stable tie-breaking.
4. Decision Support & Summarization: Provides count summaries, human-review flags, and actionable
   reviewer-friendly next steps based strictly on available evidence (never automated approval/rejection).
5. Evidence & Privacy: Preserves evidence traceability without leaking secrets or unmasked PII into summaries.
6. Non-Destructive: Original findings and evidence dictionaries are never mutated.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

import sys

# Reuse existing shared validation finding schema and enums
try:
    from dataset.src.validators.schemas import (
        ValidationFinding,
        RuleOutcome,
        RuleSeverity,
        DocumentValidationReport,
        CrossDocumentConsistencyReport,
    )
except (ImportError, ModuleNotFoundError):
    try:
        from src.validators.schemas import (
            ValidationFinding,
            RuleOutcome,
            RuleSeverity,
            DocumentValidationReport,
            CrossDocumentConsistencyReport,
        )
    except (ImportError, ModuleNotFoundError):
        try:
            from backend.validation.schemas import (
                ValidationFinding,
                RuleOutcome,
                RuleSeverity,
                DocumentValidationReport,
                CrossDocumentConsistencyReport,
            )
        except (ImportError, ModuleNotFoundError):
            RuleOutcome = Literal["PASS", "FAIL", "INCONCLUSIVE"]
            RuleSeverity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

            class ValidationFinding(BaseModel):  # type: ignore[no-redef]
                rule_id: str
                rule_name: str
                outcome: RuleOutcome
                severity: RuleSeverity
                explanation: str
                affected_document_ids: List[str] = Field(default_factory=list)
                affected_fields: List[str] = Field(default_factory=list)
                evidence_values: Dict[str, Any] = Field(default_factory=dict)
                requires_human_review: bool = False
                timestamp_utc: str = Field(
                    default_factory=lambda: datetime.now(timezone.utc).isoformat()
                )

            DocumentValidationReport = None  # type: ignore[misc]
            CrossDocumentConsistencyReport = None  # type: ignore[misc]

# Ensure sys.modules consistency across canonical and fallback import paths
if "src.validators.schemas" in sys.modules and "dataset.src.validators.schemas" not in sys.modules:
    sys.modules["dataset.src.validators.schemas"] = sys.modules["src.validators.schemas"]
elif "dataset.src.validators.schemas" in sys.modules and "src.validators.schemas" not in sys.modules:
    sys.modules["src.validators.schemas"] = sys.modules["dataset.src.validators.schemas"]

# Privacy gateway integration
from backend.security.privacy import PrivacyPurpose, redact_text

logger = logging.getLogger(__name__)

# Outcome and Severity weight mappings for deterministic sorting (lower value = higher priority)
OUTCOME_WEIGHTS: Dict[str, int] = {
    "FAIL": 0,
    "INCONCLUSIVE": 1,
    "PASS": 2,
}

SEVERITY_WEIGHTS: Dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "INFO": 4,
}

# ==============================================================================
# 1. Unified Findings Report Model
# ==============================================================================


class UnifiedFindingsReport(BaseModel):
    """
    Consolidated, deduplicated, and prioritized application verification report.
    Presents a complete audit trail for regulatory reviewers.
    """
    application_id: Optional[str] = Field(
        default=None,
        description="Application or institution bundle identifier."
    )
    overall_outcome: RuleOutcome = Field(
        description="Overall verification outcome: FAIL if any FAIL, else INCONCLUSIVE if any INCONCLUSIVE, else PASS."
    )
    total_findings: int = Field(ge=0, description="Total count of deduplicated findings.")
    summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Aggregated counters for outcomes (pass, fail, inconclusive) and severities (critical, high, etc.)."
    )
    requires_human_review: bool = Field(
        default=False,
        description="True if any finding indicates discrepancies, uncertainties, or anomalies requiring human adjudication."
    )
    findings: List[ValidationFinding] = Field(
        default_factory=list,
        description="Prioritized and deduplicated list of validation, consistency, authenticity, and privacy findings."
    )
    actionable_recommendations: List[str] = Field(
        default_factory=list,
        description="Evidence-based recommendations and next steps for the regulatory review officer."
    )
    generated_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of report generation."
    )

    def to_reviewer_view(
        self,
        purpose: PrivacyPurpose = PrivacyPurpose.REVIEWER_VIEW,
    ) -> "UnifiedFindingsReport":
        """
        Produce a non-destructive, privacy-safe copy of this report with sensitive evidence
        and explanations redacted for reviewer dashboard presentation or logging.
        """
        return filter_report_for_privacy(self, purpose=purpose)


# ==============================================================================
# 2. Normalization Logic
# ==============================================================================


def _normalize_validation_finding(item: Any) -> Optional[ValidationFinding]:
    """
    Safely convert a finding instance, report object, or dictionary into a canonical ValidationFinding.
    Never mutates input objects. Handles missing or malformed fields safely with robust defaults.
    """
    if item is None:
        return None

    # Already a ValidationFinding instance
    if isinstance(item, ValidationFinding):
        return deepcopy(item)

    # Duck-typed object with attributes
    if hasattr(item, "rule_id") and hasattr(item, "outcome"):
        try:
            return ValidationFinding(
                rule_id=str(getattr(item, "rule_id", "RULE_UNKNOWN")),
                rule_name=str(getattr(item, "rule_name", "Unknown Verification Rule")),
                outcome=getattr(item, "outcome", "INCONCLUSIVE"),
                severity=getattr(item, "severity", "MEDIUM"),
                explanation=str(getattr(item, "explanation", "No explanation provided.")),
                affected_document_ids=list(getattr(item, "affected_document_ids", []) or []),
                affected_fields=list(getattr(item, "affected_fields", []) or []),
                evidence_values=deepcopy(getattr(item, "evidence_values", {}) or {}),
                requires_human_review=bool(getattr(item, "requires_human_review", False)),
                timestamp_utc=str(getattr(item, "timestamp_utc", datetime.now(timezone.utc).isoformat())),
            )
        except Exception as exc:
            logger.warning(f"Error converting duck-typed finding: {exc}")

    # Dictionary input
    if isinstance(item, dict):
        try:
            # Normalize outcome
            outcome_val = str(item.get("outcome", "INCONCLUSIVE")).upper()
            if outcome_val not in ("PASS", "FAIL", "INCONCLUSIVE"):
                outcome_val = "INCONCLUSIVE"

            # Normalize severity
            severity_val = str(item.get("severity", "MEDIUM")).upper()
            if severity_val not in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
                severity_val = "MEDIUM"

            rule_id = str(item.get("rule_id") or "RULE_UNKNOWN").strip()
            rule_name = str(item.get("rule_name") or f"Rule {rule_id}").strip()
            explanation = str(item.get("explanation") or item.get("message") or "Verification finding recorded.")

            doc_ids = item.get("affected_document_ids") or []
            if isinstance(doc_ids, str):
                doc_ids = [doc_ids]
            elif not isinstance(doc_ids, (list, tuple)):
                doc_ids = []

            fields = item.get("affected_fields") or []
            if isinstance(fields, str):
                fields = [fields]
            elif not isinstance(fields, (list, tuple)):
                fields = []

            evidence = item.get("evidence_values") or item.get("evidence_refs") or {}
            if not isinstance(evidence, dict):
                evidence = {"raw_evidence": str(evidence)}

            human_review = bool(item.get("requires_human_review", outcome_val != "PASS"))

            return ValidationFinding(
                rule_id=rule_id,
                rule_name=rule_name,
                outcome=outcome_val,  # type: ignore[arg-type]
                severity=severity_val,  # type: ignore[arg-type]
                explanation=explanation,
                affected_document_ids=[str(d) for d in doc_ids],
                affected_fields=[str(f) for f in fields],
                evidence_values=deepcopy(evidence),
                requires_human_review=human_review,
                timestamp_utc=str(item.get("timestamp_utc") or datetime.now(timezone.utc).isoformat()),
            )
        except Exception as exc:
            logger.warning(f"Error normalizing dictionary finding: {exc}")
            return ValidationFinding(
                rule_id="RULE_MALFORMED_INPUT",
                rule_name="Malformed Finding Input Error",
                outcome="INCONCLUSIVE",
                severity="MEDIUM",
                explanation=f"Received malformed finding payload: {type(exc).__name__}",
                requires_human_review=True,
            )

    return None


def extract_findings_from_source(source: Any) -> List[ValidationFinding]:
    """
    Recursively extract and normalize findings from any container:
    - Single finding or dict
    - List or tuple of findings/dicts
    - DocumentValidationReport or CrossDocumentConsistencyReport
    - DocumentAuthenticityReport
    """
    if source is None:
        return []

    # Container reports with .findings attribute
    if hasattr(source, "findings") and isinstance(source.findings, (list, tuple)):
        result = []
        for f in source.findings:
            normalized = _normalize_validation_finding(f)
            if normalized:
                result.append(normalized)
        return result

    # Iterable of items
    if isinstance(source, (list, tuple, set)):
        result = []
        for item in source:
            result.extend(extract_findings_from_source(item))
        return result

    # Single finding item
    single = _normalize_validation_finding(source)
    return [single] if single else []


# ==============================================================================
# 3. Deduplication Logic
# ==============================================================================


def _canonical_evidence_signature(evidence: Dict[str, Any]) -> str:
    """
    Extract a stable, canonical string signature of discriminating evidence keys.
    Discriminates between distinct course/programme violations or distinct file collisions
    while ignoring non-functional metadata (timestamps, log flags).
    """
    if not evidence:
        return ""

    # Specific functional discriminator keys in AICTE verification
    discriminators = [
        "programme",
        "programme_raw",
        "course",
        "sha256",
        "matching_registered_doc_id",
        "first_seen_doc_id",
        "conflicting_ids",
        "claimed_intake",
        "approved_intake",
    ]

    parts = []
    for k in discriminators:
        if k in evidence and evidence[k] is not None:
            val = evidence[k]
            if isinstance(val, (list, tuple)):
                parts.append(f"{k}={'|'.join(sorted(str(x) for x in val))}")
            else:
                parts.append(f"{k}={str(val).strip()}")

    return ";".join(sorted(parts))


def compute_dedup_key(finding: ValidationFinding) -> Tuple[str, Tuple[str, ...], Tuple[str, ...], str]:
    """
    Compute a deterministic deduplication key for a finding.
    Key components:
    1. rule_id (e.g. 'RULE_CROSS_INTAKE_MISMATCH')
    2. sorted affected document IDs (e.g. ('DOC_001', 'DOC_002'))
    3. sorted affected fields (e.g. ('approved_courses_and_intake',))
    4. canonical evidence signature (e.g. 'programme=Computer Science')

    Guarantees:
    - Genuinely distinct findings sharing a rule ID (e.g. two courses with quota violations)
      have distinct evidence signatures and will NOT be collapsed.
    - Repeated emissions of the exact same finding (e.g. duplicate hash check run twice)
      have identical keys and are merged cleanly.
    """
    rule_id = finding.rule_id.strip()
    docs = tuple(sorted(str(d).strip() for d in finding.affected_document_ids))
    fields = tuple(sorted(str(f).strip() for f in finding.affected_fields))
    evidence_sig = _canonical_evidence_signature(finding.evidence_values)

    return (rule_id, docs, fields, evidence_sig)


def merge_equivalent_findings(f1: ValidationFinding, f2: ValidationFinding) -> ValidationFinding:
    """
    Merge two equivalent findings into a single enriched finding.
    Preserves all evidence, highest severity, most severe outcome, and human review flags.
    Never mutates the inputs.
    """
    # 1. Outcome: FAIL (0) > INCONCLUSIVE (1) > PASS (2)
    w_out1 = OUTCOME_WEIGHTS.get(f1.outcome, 9)
    w_out2 = OUTCOME_WEIGHTS.get(f2.outcome, 9)
    merged_outcome = f1.outcome if w_out1 <= w_out2 else f2.outcome

    # 2. Severity: CRITICAL (0) > HIGH (1) > MEDIUM (2) > LOW (3) > INFO (4)
    w_sev1 = SEVERITY_WEIGHTS.get(f1.severity, 9)
    w_sev2 = SEVERITY_WEIGHTS.get(f2.severity, 9)
    merged_severity = f1.severity if w_sev1 <= w_sev2 else f2.severity

    # 3. Documents & Fields (Union preserving order)
    docs = list(dict.fromkeys(f1.affected_document_ids + f2.affected_document_ids))
    fields = list(dict.fromkeys(f1.affected_fields + f2.affected_fields))

    # 4. Evidence Values (Merged dictionary)
    merged_evidence = deepcopy(f1.evidence_values)
    merged_evidence.update(deepcopy(f2.evidence_values))

    # 5. Explanation: preserve longer/more descriptive text
    merged_explanation = f1.explanation if len(f1.explanation) >= len(f2.explanation) else f2.explanation

    # 6. Human review flag
    human_review = f1.requires_human_review or f2.requires_human_review

    # 7. Earliest timestamp
    earliest_time = min(f1.timestamp_utc, f2.timestamp_utc)

    return ValidationFinding(
        rule_id=f1.rule_id,
        rule_name=f1.rule_name or f2.rule_name,
        outcome=merged_outcome,
        severity=merged_severity,
        explanation=merged_explanation,
        affected_document_ids=docs,
        affected_fields=fields,
        evidence_values=merged_evidence,
        requires_human_review=human_review,
        timestamp_utc=earliest_time,
    )


def deduplicate_findings(findings: List[ValidationFinding]) -> List[ValidationFinding]:
    """
    Deduplicate a list of findings using the deterministic deduplication key.
    Merges equivalent findings while preserving genuinely distinct ones.
    """
    merged_map: Dict[Tuple[str, Tuple[str, ...], Tuple[str, ...], str], ValidationFinding] = {}

    for f in findings:
        key = compute_dedup_key(f)
        if key in merged_map:
            merged_map[key] = merge_equivalent_findings(merged_map[key], f)
        else:
            merged_map[key] = deepcopy(f)

    return list(merged_map.values())


# ==============================================================================
# 4. Prioritization Logic
# ==============================================================================


def finding_sort_key(f: ValidationFinding) -> Tuple[int, int, str, str, str]:
    """
    Deterministic sort key for ranking findings:
    1. Outcome: FAIL (0) -> INCONCLUSIVE (1) -> PASS (2)
    2. Severity: CRITICAL (0) -> HIGH (1) -> MEDIUM (2) -> LOW (3) -> INFO (4)
    3. Stable rule_id alphabetically
    4. Affected document IDs
    5. Explanation string
    """
    out_rank = OUTCOME_WEIGHTS.get(f.outcome, 9)
    sev_rank = SEVERITY_WEIGHTS.get(f.severity, 9)
    rule_str = f.rule_id.strip()
    docs_str = ",".join(sorted(f.affected_document_ids))
    return (out_rank, sev_rank, rule_str, docs_str, f.explanation)


def prioritize_findings(findings: List[ValidationFinding]) -> List[ValidationFinding]:
    """
    Return a new list of findings sorted deterministically by priority.
    Does not mutate input list.
    """
    return sorted(deepcopy(findings), key=finding_sort_key)


# ==============================================================================
# 5. Reviewer Recommendations Generator
# ==============================================================================


def generate_recommendations(findings: List[ValidationFinding]) -> List[str]:
    """
    Generate evidence-based, actionable recommendations for regulatory review officers.
    Strictly avoids automated pass/fail decisions or unverified fraud accusations.
    """
    recommendations: List[str] = []
    seen_categories: Set[str] = set()

    for f in findings:
        rid = f.rule_id

        # 1. Duplicate Submissions
        if "DUPLICATE" in rid and f.outcome == "FAIL" and "duplicate" not in seen_categories:
            seen_categories.add("duplicate")
            recommendations.append(
                "Administrative Duplicate Check: Identical document hash detected across submissions. "
                "Verify whether this represents an intentional resubmission or redundant file upload."
            )

        # 2. Intake Quota Discrepancy
        elif "INTAKE_MISMATCH" in rid and f.outcome == "FAIL" and "intake" not in seen_categories:
            seen_categories.add("intake")
            recommendations.append(
                "Intake Quota Verification: Claimed course intake in Mandatory Disclosure exceeds approved quota in AICTE EoA. "
                "Request formal institute justification or official quota amendment order."
            )

        # 3. Institution ID Mismatch
        elif "CROSS_INSTITUTION_ID" in rid and f.outcome == "FAIL" and "inst_id" not in seen_categories:
            seen_categories.add("inst_id")
            recommendations.append(
                "Institutional Identity Conflict: Permanent Institute ID mismatch between submitted documents. "
                "Verify portal registration records to confirm correct parent institute."
            )

        # 4. Mandatory Field Absence
        elif "REQ_" in rid and f.outcome == "FAIL" and "missing_field" not in seen_categories:
            seen_categories.add("missing_field")
            recommendations.append(
                f"Missing Mandatory Fields: {f.explanation} Review physical document pages to verify whether field was omitted."
            )

        # 5. Metadata Anomaly
        elif ("PRODUCER_ANOMALY" in rid or "TIMESTAMP_INVERSION" in rid) and "metadata" not in seen_categories:
            seen_categories.add("metadata")
            recommendations.append(
                "Document Metadata Anomaly: Non-standard creation software or timestamp skew detected. "
                "Perform physical verification of authorized signatory and official council stamp."
            )

        # 6. Low OCR / Ambiguous Evidence
        elif f.outcome == "INCONCLUSIVE" and ("OCR" in rid or "AMBIGUOUS" in rid) and "ocr" not in seen_categories:
            seen_categories.add("ocr")
            recommendations.append(
                "Uncertain Recognition: Extraction confidence below acceptance threshold. "
                "Adjudicate flagged field values directly from source PDF page."
            )

    if not recommendations:
        if any(f.outcome == "FAIL" for f in findings):
            recommendations.append("Manual Adjudication: One or more validation rules failed. Inspect flagged evidence values.")
        elif any(f.outcome == "INCONCLUSIVE" for f in findings):
            recommendations.append("Evidence Verification: Uncertain fields require visual confirmation against original filings.")
        else:
            recommendations.append("Automated Verification Clear: All deterministic rules and integrity checks passed cleanly.")

    return recommendations


# ==============================================================================
# 6. Privacy Redaction Helper
# ==============================================================================


def _redact_nested_value(val: Any) -> Any:
    """Recursively redact sensitive strings from nested dicts, lists, and primitives."""
    if isinstance(val, str):
        return redact_text(val)
    if isinstance(val, dict):
        return {k: _redact_nested_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        redacted_list = [_redact_nested_value(item) for item in val]
        return type(val)(redacted_list)
    return val


def filter_report_for_privacy(
    report: UnifiedFindingsReport,
    purpose: PrivacyPurpose = PrivacyPurpose.REVIEWER_VIEW,
) -> UnifiedFindingsReport:
    """
    Produce a non-destructive privacy-redacted copy of a UnifiedFindingsReport.
    Sanitizes explanations, evidence values, and recommendations.
    Original report remains completely untouched.
    """
    copied = report.model_copy(deep=True)

    # In internal verification, retain 100% unmasked evidence
    if purpose == PrivacyPurpose.INTERNAL_VERIFICATION:
        return copied

    # Redact sensitive patterns in finding explanations and evidence values
    redacted_findings: List[ValidationFinding] = []
    for f in copied.findings:
        f_copy = f.model_copy(deep=True)
        # Redact explanation text
        f_copy.explanation = redact_text(f_copy.explanation)

        # Recursively redact evidence dictionary values while preserving nested structures
        clean_evidence = {}
        for k, v in f_copy.evidence_values.items():
            clean_evidence[k] = _redact_nested_value(v)
        f_copy.evidence_values = clean_evidence
        redacted_findings.append(f_copy)

    copied.findings = redacted_findings

    # Redact recommendations
    copied.actionable_recommendations = [redact_text(rec) for rec in copied.actionable_recommendations]

    return copied


# ==============================================================================
# 7. Unified Findings Engine & Entrypoint
# ==============================================================================


class UnifiedFindingsEngine:
    """
    Engine class for accumulating, normalizing, deduplicating, and compiling
    findings across all verification pipeline stages.
    """

    def __init__(self, application_id: Optional[str] = None):
        self.application_id = application_id
        self._raw_findings: List[ValidationFinding] = []

    def ingest(self, *sources: Any) -> "UnifiedFindingsEngine":
        """
        Ingest findings from one or more sources (ValidationFinding, reports, dictionaries, lists).
        """
        for source in sources:
            self._raw_findings.extend(extract_findings_from_source(source))
        return self

    def compile(self) -> UnifiedFindingsReport:
        """
        Compile accumulated findings into a deduplicated, prioritized UnifiedFindingsReport.
        """
        # 1. Deduplicate
        deduped = deduplicate_findings(self._raw_findings)

        # 2. Prioritize
        prioritized = prioritize_findings(deduped)

        # 3. Overall Outcome & Summary Counters
        has_fail = any(f.outcome == "FAIL" for f in prioritized)
        has_inconclusive = any(f.outcome == "INCONCLUSIVE" for f in prioritized)

        if has_fail:
            overall = "FAIL"
        elif has_inconclusive:
            overall = "INCONCLUSIVE"
        else:
            overall = "PASS"

        summary = {
            "total_rules": len(prioritized),
            "pass": sum(1 for f in prioritized if f.outcome == "PASS"),
            "fail": sum(1 for f in prioritized if f.outcome == "FAIL"),
            "inconclusive": sum(1 for f in prioritized if f.outcome == "INCONCLUSIVE"),
            "critical": sum(1 for f in prioritized if f.severity == "CRITICAL"),
            "high": sum(1 for f in prioritized if f.severity == "HIGH"),
            "medium": sum(1 for f in prioritized if f.severity == "MEDIUM"),
            "low": sum(1 for f in prioritized if f.severity == "LOW"),
            "info": sum(1 for f in prioritized if f.severity == "INFO"),
        }

        human_review = any(f.requires_human_review for f in prioritized) or (overall != "PASS")
        recommendations = generate_recommendations(prioritized)

        return UnifiedFindingsReport(
            application_id=self.application_id,
            overall_outcome=overall,
            total_findings=len(prioritized),
            summary=summary,
            requires_human_review=human_review,
            findings=prioritized,
            actionable_recommendations=recommendations,
        )


def unify_findings(*sources: Any, application_id: Optional[str] = None) -> UnifiedFindingsReport:
    """
    Convenience function to ingest sources and compile a UnifiedFindingsReport in one call.

    Usage:
        report = unify_findings(
            validation_report,
            consistency_report,
            authenticity_report,
            application_id="APP_2026_001"
        )
    """
    engine = UnifiedFindingsEngine(application_id=application_id)
    engine.ingest(*sources)
    return engine.compile()

# ==============================================================================
# Phase 9: Dashboard Finding Normalization & Reviewer Summary (Person 4 Integration)
# ==============================================================================

try:
    from backend.common.models import (
        NormalizedFinding,
        ReviewerSummary,
    )
except ImportError:
    NormalizedFinding = Any  # type: ignore[misc, assignment]
    ReviewerSummary = Any  # type: ignore[misc, assignment]


def normalize_finding(
    item: Any,
    category: Optional[Literal["COMPLIANCE", "AUTHENTICITY", "PRIVACY", "CONSISTENCY"]] = None,
    prefix: str = "FINDING",
    index: int = 1,
) -> Any:
    """
    Dual-purpose normalization function:
    1. If called with a single argument (raw finding dict/model):
       Converts/normalizes the input into a canonical ValidationFinding instance (Person 3 contract).
    2. If called with 'category' (Person 4 Phase 9 dashboard contract):
       Converts the input ValidationFinding into a NormalizedFinding for the reviewer UI.
    """
    if category is not None:
        return NormalizedFinding(
            finding_id=f"{prefix}_{index:03d}_{getattr(item, 'rule_id', 'UNKNOWN')}",
            category=category,
            rule_id=getattr(item, "rule_id", "UNKNOWN"),
            rule_name=getattr(item, "rule_name", "Unknown Rule"),
            outcome=getattr(item, "outcome", "INCONCLUSIVE"),
            severity=getattr(item, "severity", "MEDIUM"),
            explanation=getattr(item, "explanation", ""),
            affected_document_ids=getattr(item, "affected_document_ids", []),
            affected_fields=getattr(item, "affected_fields", []),
            evidence_values=getattr(item, "evidence_values", {}),
            requires_human_review=getattr(item, "requires_human_review", False),
            timestamp_utc=getattr(item, "timestamp_utc", datetime.now(timezone.utc).isoformat()),
        )
    return _normalize_validation_finding(item)


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
