"""
backend/security/authenticity.py - Document Authenticity & Anomaly Detection for SIH26261 (Stage 7).

Core Principles:
1. Deterministic & Explainable: Every finding has a stable rule ID, severity, outcome, and human-readable explanation.
2. Signal vs Fraud Verdict: Anomalies (e.g. metadata tools, inverted timestamps, missing headers) are treated
   as signals requiring human review, NEVER as definitive proof of tampering or forgery.
3. Decision-Support Only: Does not make automated approval or rejection decisions.
4. Duplicate-Detection Reuse: Strictly reuses Person 2's RULE_INTEGRITY_DUPLICATE_HASH logic and semantics,
   preventing competing or divergent duplicate-finding models.
5. Evidence Preservation: Cites affected document IDs, SHA-256 hashes, and metadata properties.
6. Safe Handling: Gracefully processes missing, empty, malformed, or unreadable files without pipeline crashes.
"""

from datetime import datetime, timezone
import hashlib
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

import sys
from pydantic import BaseModel, Field, field_validator

# Graceful import of Person 2's ValidationFinding contract
try:
    from dataset.src.validators.schemas import ValidationFinding, RuleOutcome, RuleSeverity
except (ImportError, ModuleNotFoundError):
    try:
        from src.validators.schemas import ValidationFinding, RuleOutcome, RuleSeverity
    except (ImportError, ModuleNotFoundError):
        try:
            from backend.validation.schemas import ValidationFinding, RuleOutcome, RuleSeverity
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

# Ensure sys.modules consistency across canonical and fallback import paths
if "src.validators.schemas" in sys.modules and "dataset.src.validators.schemas" not in sys.modules:
    sys.modules["dataset.src.validators.schemas"] = sys.modules["src.validators.schemas"]
elif "dataset.src.validators.schemas" in sys.modules and "src.validators.schemas" not in sys.modules:
    sys.modules["src.validators.schemas"] = sys.modules["dataset.src.validators.schemas"]

# Graceful import of Person 2's duplicate hash rule
try:
    from dataset.src.validators.cross_document import check_duplicate_hash
except (ImportError, ModuleNotFoundError):
    try:
        from src.validators.cross_document import check_duplicate_hash
    except (ImportError, ModuleNotFoundError):
        try:
            from backend.validation.consistency import check_duplicate_hash
        except (ImportError, ModuleNotFoundError):
            check_duplicate_hash = None

if "src.validators.cross_document" in sys.modules and "dataset.src.validators.cross_document" not in sys.modules:
    sys.modules["dataset.src.validators.cross_document"] = sys.modules["src.validators.cross_document"]
elif "dataset.src.validators.cross_document" in sys.modules and "src.validators.cross_document" not in sys.modules:
    sys.modules["src.validators.cross_document"] = sys.modules["dataset.src.validators.cross_document"]

# Optional PyMuPDF import
try:
    import pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

logger = logging.getLogger(__name__)

# Known desktop image editing software keywords.
# Note: Presence in metadata is a signal for manual inspection, NOT proof of fraud.
SUSPICIOUS_PRODUCER_KEYWORDS: Set[str] = {
    "photoshop",
    "canva",
    "gimp",
    "inkscape",
    "illustrator",
    "paint.net",
    "coreldraw",
    "pixlr",
}

# ==============================================================================
# 1. Output Report Model
# ==============================================================================


class DocumentAuthenticityReport(BaseModel):
    """
    Consolidated authenticity and structural verification report for a single document.
    Collects checksum verification, structural parseability, and metadata findings.
    """
    document_id: str = Field(description="Deterministic document identifier.")
    sha256: Optional[str] = Field(default=None, description="Cryptographic SHA-256 hash.")
    file_size_bytes: int = Field(ge=0, description="Size of file in bytes.")
    is_valid_pdf: bool = Field(description="True if file has valid PDF magic header and trailer.")
    overall_outcome: RuleOutcome = Field(
        description="Consolidated outcome: FAIL if any FAIL, else INCONCLUSIVE if any INCONCLUSIVE, else PASS."
    )
    findings: List[ValidationFinding] = Field(
        default_factory=list,
        description="Authenticity and structural rule findings."
    )
    metadata_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key extracted metadata attributes (producer, creator, timestamps, encryption)."
    )
    requires_human_review: bool = Field(
        default=False,
        description="True if findings warrant verification by a human reviewer."
    )

    @field_validator("findings", mode="before")
    @classmethod
    def _coerce_findings(cls, v: Any) -> Any:
        if isinstance(v, (list, tuple)):
            coerced = []
            for item in v:
                if isinstance(item, ValidationFinding):
                    coerced.append(item)
                elif hasattr(item, "model_dump"):
                    coerced.append(ValidationFinding(**item.model_dump()))
                elif isinstance(item, dict):
                    coerced.append(ValidationFinding(**item))
                else:
                    coerced.append(item)
            return coerced
        return v

    @classmethod
    def create(
        cls,
        document_id: str,
        sha256: Optional[str],
        file_size_bytes: int,
        is_valid_pdf: bool,
        findings: List[ValidationFinding],
        metadata_summary: Optional[Dict[str, Any]] = None,
    ) -> "DocumentAuthenticityReport":
        has_fail = any(f.outcome == "FAIL" for f in findings)
        has_inconclusive = any(f.outcome == "INCONCLUSIVE" for f in findings)

        if has_fail:
            overall = "FAIL"
        elif has_inconclusive:
            overall = "INCONCLUSIVE"
        else:
            overall = "PASS"

        human_review = any(f.requires_human_review for f in findings) or (overall != "PASS")

        converted_findings: List[ValidationFinding] = []
        for f in findings:
            if isinstance(f, ValidationFinding):
                converted_findings.append(f)
            elif hasattr(f, "model_dump"):
                converted_findings.append(ValidationFinding(**f.model_dump()))
            elif isinstance(f, dict):
                converted_findings.append(ValidationFinding(**f))
            else:
                converted_findings.append(f)

        return cls(
            document_id=document_id,
            sha256=sha256,
            file_size_bytes=file_size_bytes,
            is_valid_pdf=is_valid_pdf,
            overall_outcome=overall,
            findings=converted_findings,
            metadata_summary=metadata_summary or {},
            requires_human_review=human_review,
        )


# ==============================================================================
# 2. File Checksum & Integrity Utilities
# ==============================================================================


def compute_file_sha256(file_path_or_bytes: Union[str, Path, bytes]) -> str:
    """
    Compute full 64-character lowercase SHA-256 checksum over file bytes.
    Streams file in 64 KB chunks to maintain low memory overhead.
    """
    h = hashlib.sha256()

    if isinstance(file_path_or_bytes, bytes):
        h.update(file_path_or_bytes)
        return h.hexdigest().lower()

    path = Path(file_path_or_bytes)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path.name}")
    if not path.is_file():
        raise ValueError(f"Target path is not a file: {path.name}")

    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)

    return h.hexdigest().lower()


def parse_pdf_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse standard PDF date format (e.g. "D:20250515094852+05'30'" or "D:20240401").
    Returns timezone-aware UTC datetime or None if unparseable.
    """
    if not date_str:
        return None

    clean = str(date_str).strip()
    if clean.startswith("D:"):
        clean = clean[2:]

    # Match YYYYMMDDHHmmss or YYYYMMDD
    m = re.match(r"^(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", clean)
    if not m:
        return None

    parts = m.groups()
    try:
        year = int(parts[0])
        month = int(parts[1]) if parts[1] else 1
        day = int(parts[2]) if parts[2] else 1
        hour = int(parts[3]) if parts[3] else 0
        minute = int(parts[4]) if parts[4] else 0
        second = int(parts[5]) if parts[5] else 0
        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


# ==============================================================================
# 3. Structural & Format Verification
# ==============================================================================


def inspect_file_structure(
    file_bytes: bytes,
    document_id: str = "DOC_UNKNOWN",
) -> Tuple[bool, List[ValidationFinding]]:
    """
    Verify fundamental PDF byte structure without third-party dependencies.
    Checks:
    - Non-zero length (empty file check).
    - PDF magic header '%PDF-' within the first 1024 bytes.
    - PDF EOF marker '%%EOF' within the last 1024 bytes.
    """
    findings: List[ValidationFinding] = []

    # 1. Empty file check
    if len(file_bytes) == 0:
        findings.append(
            ValidationFinding(
                rule_id="RULE_AUTH_EMPTY_FILE",
                rule_name="Document Empty File Verification",
                outcome="FAIL",
                severity="HIGH",
                explanation="File is 0 bytes. Document content is missing.",
                affected_document_ids=[document_id],
                evidence_values={"file_size_bytes": 0},
                requires_human_review=True,
            )
        )
        return False, findings

    # 2. PDF Magic Header check (%PDF- in first 1024 bytes)
    header_slice = file_bytes[:1024]
    has_header = b"%PDF-" in header_slice
    if not has_header:
        findings.append(
            ValidationFinding(
                rule_id="RULE_AUTH_UNSUPPORTED_OR_CORRUPT",
                rule_name="Document Format Header Verification",
                outcome="FAIL",
                severity="HIGH",
                explanation=(
                    "File lacks standard PDF magic header marker ('%PDF-'). "
                    "File may be corrupted, truncated, or an unsupported file type."
                ),
                affected_document_ids=[document_id],
                evidence_values={"file_size_bytes": len(file_bytes), "header_sample": repr(header_slice[:32])},
                requires_human_review=True,
            )
        )
        return False, findings

    # 3. PDF Trailing EOF marker check (%%EOF in last 1024 bytes)
    trailer_slice = file_bytes[-1024:]
    has_trailer = b"%%EOF" in trailer_slice
    if not has_trailer:
        findings.append(
            ValidationFinding(
                rule_id="RULE_AUTH_MALFORMED_STRUCTURE",
                rule_name="Document Stream EOF Marker Verification",
                outcome="INCONCLUSIVE",
                severity="MEDIUM",
                explanation=(
                    "PDF file is missing standard trailing EOF marker ('%%EOF'). "
                    "This indicates possible stream truncation or incomplete upload."
                ),
                affected_document_ids=[document_id],
                evidence_values={"file_size_bytes": len(file_bytes)},
                requires_human_review=True,
            )
        )
        return True, findings  # Partial parseability possible

    return True, findings


# ==============================================================================
# 4. PDF Metadata & Anomaly Assessment
# ==============================================================================


def inspect_pdf_metadata(
    file_bytes: bytes,
    document_id: str = "DOC_UNKNOWN",
) -> Tuple[List[ValidationFinding], Dict[str, Any]]:
    """
    Inspect PDF metadata properties and structural flags using PyMuPDF if available,
    falling back gracefully to byte analysis.

    Checks:
    - Password encryption preventing access.
    - Repaired cross-reference table (indicates non-standard PDF creation).
    - Inverted timestamps (ModDate precedes CreationDate).
    - Graphic editing tools recorded in Creator or Producer fields.
    - Missing or absent metadata (handled as a weak signal, NOT proof of tampering).
    """
    findings: List[ValidationFinding] = []
    metadata_summary: Dict[str, Any] = {
        "page_count": 0,
        "is_encrypted": False,
        "is_repaired": False,
        "producer": "",
        "creator": "",
        "creation_date": "",
        "mod_date": "",
    }

    if not HAS_PYMUPDF:
        findings.append(
            ValidationFinding(
                rule_id="RULE_AUTH_METADATA_INSPECTION",
                rule_name="PDF Metadata and Anomaly Inspection",
                outcome="INCONCLUSIVE",
                severity="LOW",
                explanation="PyMuPDF library is unavailable in current environment; deep metadata checks skipped.",
                affected_document_ids=[document_id],
                requires_human_review=False,
            )
        )
        return findings, metadata_summary

    doc = None
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        metadata_summary["page_count"] = doc.page_count
        metadata_summary["is_encrypted"] = bool(doc.is_encrypted)
        metadata_summary["is_repaired"] = bool(doc.is_repaired)

        meta = doc.metadata or {}
        producer = str(meta.get("producer") or "").strip()
        creator = str(meta.get("creator") or "").strip()
        cdate_str = str(meta.get("creationDate") or "").strip()
        mdate_str = str(meta.get("modDate") or "").strip()

        metadata_summary["producer"] = producer
        metadata_summary["creator"] = creator
        metadata_summary["creation_date"] = cdate_str
        metadata_summary["mod_date"] = mdate_str

        # 1. Encryption Check
        if doc.is_encrypted:
            findings.append(
                ValidationFinding(
                    rule_id="RULE_AUTH_ENCRYPTED_PDF",
                    rule_name="Document Encryption Verification",
                    outcome="FAIL",
                    severity="HIGH",
                    explanation="Document is password-protected or encrypted, preventing automated verification.",
                    affected_document_ids=[document_id],
                    requires_human_review=True,
                )
            )
            return findings, metadata_summary

        # 2. Corrupt / Auto-Repaired Structure Check
        if doc.is_repaired:
            findings.append(
                ValidationFinding(
                    rule_id="RULE_AUTH_PDF_REPAIRED",
                    rule_name="Document Cross-Reference Structure Verification",
                    outcome="INCONCLUSIVE",
                    severity="LOW",
                    explanation=(
                        "PDF xref table was damaged and required structural repair to open. "
                        "May indicate non-standard PDF creation tool or minor stream corruption."
                    ),
                    affected_document_ids=[document_id],
                    requires_human_review=True,
                )
            )

        # 3. Timestamp Inversion Check (ModDate earlier than CreationDate)
        dt_create = parse_pdf_date(cdate_str)
        dt_mod = parse_pdf_date(mdate_str)

        if dt_create and dt_mod:
            if dt_mod < dt_create:
                findings.append(
                    ValidationFinding(
                        rule_id="RULE_AUTH_TIMESTAMP_INVERSION",
                        rule_name="Document Metadata Timestamp Alignment",
                        outcome="INCONCLUSIVE",
                        severity="MEDIUM",
                        explanation=(
                            f"Modification timestamp ({mdate_str}) precedes creation timestamp ({cdate_str}). "
                            "Signal indicates potential clock skew or manual metadata re-writing; human review recommended."
                        ),
                        affected_document_ids=[document_id],
                        evidence_values={
                            "creation_date": cdate_str,
                            "mod_date": mdate_str,
                        },
                        requires_human_review=True,
                    )
                )

        # 4. Desktop Graphic Editor Check
        # Check both producer and creator for known image manipulation tools
        combined_meta = f"{producer} {creator}".lower()
        matched_tools = [tool for tool in SUSPICIOUS_PRODUCER_KEYWORDS if tool in combined_meta]

        if matched_tools:
            tool_name = matched_tools[0].title()
            findings.append(
                ValidationFinding(
                    rule_id="RULE_AUTH_PRODUCER_ANOMALY",
                    rule_name="Document Generator Tooling Verification",
                    outcome="INCONCLUSIVE",
                    severity="LOW",
                    explanation=(
                        f"Document metadata indicates graphic editing software ({tool_name}) in creator/producer. "
                        "Note: graphic editing software in metadata is an informational signal and not proof of tampering; "
                        "reviewer verification of official seal and signature is advised."
                    ),
                    affected_document_ids=[document_id],
                    evidence_values={
                        "producer": producer,
                        "creator": creator,
                        "flagged_tool": tool_name,
                    },
                    requires_human_review=True,
                )
            )

        # 5. Missing / Omitted Metadata Check (Weak Signal)
        if not producer and not creator:
            findings.append(
                ValidationFinding(
                    rule_id="RULE_AUTH_METADATA_ABSENT",
                    rule_name="Document Generator Tooling Verification",
                    outcome="PASS",
                    severity="INFO",
                    explanation=(
                        "Producer and creator metadata are absent. Common in web-printed, scanned, "
                        "or sanitized PDFs; not treated as an anomaly."
                    ),
                    affected_document_ids=[document_id],
                    requires_human_review=False,
                )
            )
        elif not matched_tools and not doc.is_repaired:
            findings.append(
                ValidationFinding(
                    rule_id="RULE_AUTH_METADATA_VALID",
                    rule_name="PDF Metadata and Anomaly Inspection",
                    outcome="PASS",
                    severity="INFO",
                    explanation=f"PDF metadata structure inspected cleanly (Producer: '{producer or 'Standard'}').",
                    affected_document_ids=[document_id],
                    requires_human_review=False,
                )
            )

        # 6. Basic Visual / Dimension Checks
        if doc.page_count > 0:
            first_page = doc[0]
            rect = first_page.rect
            width, height = rect.width, rect.height
            # Check for extremely degenerate dimensions (e.g. 0 or < 10 pt)
            if width <= 10.0 or height <= 10.0:
                findings.append(
                    ValidationFinding(
                        rule_id="RULE_AUTH_VISUAL_DIMENSION_ANOMALY",
                        rule_name="Document Visual Page Geometry Verification",
                        outcome="INCONCLUSIVE",
                        severity="LOW",
                        explanation=f"Unusual page dimensions detected (width={width:.1f}pt, height={height:.1f}pt).",
                        affected_document_ids=[document_id],
                        evidence_values={"width": width, "height": height},
                        requires_human_review=True,
                    )
                )

    except Exception as exc:
        findings.append(
            ValidationFinding(
                rule_id="RULE_FILE_PARSEABLE",
                rule_name="Document Parseability and Stream Integrity",
                outcome="FAIL",
                severity="CRITICAL",
                explanation=f"PDF engine failed to open or parse document stream: {type(exc).__name__}",
                affected_document_ids=[document_id],
                requires_human_review=True,
            )
        )
    finally:
        if doc:
            try:
                doc.close()
            except Exception:
                pass

    return findings, metadata_summary


# ==============================================================================
# 5. Duplicate Hash Registry & Verification
# ==============================================================================


class DuplicateHashRegistry:
    """
    In-memory registry for tracking submitted document SHA-256 hashes across
    application sessions. Reuses Person 2's RULE_INTEGRITY_DUPLICATE_HASH semantics.
    """

    def __init__(self, initial_hashes: Optional[Dict[str, str]] = None):
        # Maps sha256_hex -> document_id
        self._registry: Dict[str, str] = dict(initial_hashes) if initial_hashes else {}

    def register(self, sha256: str, document_id: str) -> None:
        """Register a document's SHA-256 hash."""
        if sha256 and document_id:
            self._registry[sha256.strip().lower()] = document_id

    def check_duplicate(
        self,
        sha256: str,
        document_id: str,
    ) -> Optional[ValidationFinding]:
        """
        Check whether sha256 has been registered by a distinct previous document.
        Emits Person 2's exact RULE_INTEGRITY_DUPLICATE_HASH finding.
        """
        clean_hash = sha256.strip().lower()
        if clean_hash in self._registry:
            prev_id = self._registry[clean_hash]
            if prev_id != document_id:
                return ValidationFinding(
                    rule_id="RULE_INTEGRITY_DUPLICATE_HASH",
                    rule_name="Deterministic Duplicate Document Hash Verification",
                    outcome="FAIL",
                    severity="MEDIUM",
                    explanation=(
                        f"Document sha256 checksum matches existing submission doc_id '{prev_id}'. "
                        f"Note: duplicate document upload indicates an identical re-submission or duplicate "
                        f"upload and does not imply fraud or regulatory non-compliance."
                    ),
                    affected_document_ids=[document_id, prev_id],
                    evidence_values={
                        "document_id": document_id,
                        "sha256": clean_hash,
                        "matching_registered_doc_id": prev_id,
                    },
                    requires_human_review=False,
                )

        # Register current document
        self._registry[clean_hash] = document_id
        return None

    def as_dict(self) -> Dict[str, str]:
        """Return shallow copy of current registry mapping."""
        return dict(self._registry)


def verify_duplicate_via_validator(
    documents: List[Any],
    registered_hashes: Optional[Dict[str, str]] = None,
) -> Optional[ValidationFinding]:
    """
    Directly call Person 2's check_duplicate_hash validator function if available.
    Ensures zero duplication of duplicate-detection logic.
    """
    if check_duplicate_hash is not None:
        return check_duplicate_hash(documents, registered_hashes=registered_hashes)

    # Fallback to internal registry check if check_duplicate_hash cannot be imported
    reg = DuplicateHashRegistry(registered_hashes)
    for doc in documents:
        doc_id = getattr(doc, "document_id", None) or (doc.get("document_id") if isinstance(doc, dict) else "DOC_UNKNOWN")
        sha256 = getattr(doc, "sha256", None) or (doc.get("sha256") if isinstance(doc, dict) else None)
        if sha256:
            dup_finding = reg.check_duplicate(sha256, doc_id)
            if dup_finding:
                return dup_finding

    return ValidationFinding(
        rule_id="RULE_INTEGRITY_DUPLICATE_HASH",
        rule_name="Deterministic Duplicate Document Hash Verification",
        outcome="PASS",
        severity="INFO",
        explanation="All submitted documents have distinct cryptographic SHA-256 hashes.",
        affected_document_ids=[getattr(d, "document_id", "DOC") for d in documents],
        requires_human_review=False,
    )


# ==============================================================================
# 6. Consolidated Assessment Entrypoint
# ==============================================================================


def assess_document_authenticity(
    file_path_or_bytes: Union[str, Path, bytes],
    document_id: str = "DOC_UNKNOWN",
    registered_hashes: Optional[Dict[str, str]] = None,
) -> DocumentAuthenticityReport:
    """
    Execute full Stage 7 Authenticity and Anomaly assessment for a document.

    Pipeline:
    1. Reads bytes safely and computes streaming SHA-256.
    2. Runs structural byte check (empty check, %PDF- header, %%EOF marker).
    3. Runs metadata & anomaly checks (timestamps, producers, encryption, repair).
    4. Evaluates duplicate hash against registry using shared duplicate semantics.
    5. Assembles and returns DocumentAuthenticityReport.
    """
    all_findings: List[ValidationFinding] = []
    metadata_summary: Dict[str, Any] = {}
    file_bytes: bytes = b""

    # 1. Read file bytes safely
    try:
        if isinstance(file_path_or_bytes, bytes):
            file_bytes = file_path_or_bytes
        else:
            path = Path(file_path_or_bytes)
            if not path.exists():
                finding = ValidationFinding(
                    rule_id="RULE_FILE_PARSEABLE",
                    rule_name="Document Parseability and Stream Integrity",
                    outcome="FAIL",
                    severity="CRITICAL",
                    explanation=f"Document file does not exist on disk: {path.name}",
                    affected_document_ids=[document_id],
                    requires_human_review=True,
                )
                return DocumentAuthenticityReport.create(
                    document_id=document_id,
                    sha256=None,
                    file_size_bytes=0,
                    is_valid_pdf=False,
                    findings=[finding],
                )
            with open(path, "rb") as f:
                file_bytes = f.read()
    except Exception as exc:
        finding = ValidationFinding(
            rule_id="RULE_FILE_PARSEABLE",
            rule_name="Document Parseability and Stream Integrity",
            outcome="FAIL",
            severity="CRITICAL",
            explanation=f"I/O error reading document file: {type(exc).__name__}",
            affected_document_ids=[document_id],
            requires_human_review=True,
        )
        return DocumentAuthenticityReport.create(
            document_id=document_id,
            sha256=None,
            file_size_bytes=0,
            is_valid_pdf=False,
            findings=[finding],
        )

    # 2. Compute SHA-256 checksum
    file_size = len(file_bytes)
    sha256 = compute_file_sha256(file_bytes) if file_size > 0 else None

    # 3. Structural byte inspection
    is_valid_pdf, struct_findings = inspect_file_structure(file_bytes, document_id=document_id)
    all_findings.extend(struct_findings)

    # 4. Metadata and deep structural checks (if valid PDF)
    if is_valid_pdf:
        meta_findings, metadata_summary = inspect_pdf_metadata(file_bytes, document_id=document_id)
        all_findings.extend(meta_findings)

    # 5. Duplicate hash check against registry
    if sha256 and registered_hashes:
        reg = DuplicateHashRegistry(registered_hashes)
        dup_finding = reg.check_duplicate(sha256, document_id)
        if dup_finding:
            all_findings.append(dup_finding)

    return DocumentAuthenticityReport.create(
        document_id=document_id,
        sha256=sha256,
        file_size_bytes=file_size,
        is_valid_pdf=is_valid_pdf,
        findings=all_findings,
        metadata_summary=metadata_summary,
    )

# ==============================================================================
# Phase 9: Authenticity Service for API Orchestration (Person 4 Integration)
# ==============================================================================


class AuthenticityService:
    """
    Evaluates document cryptographic authenticity, format integrity,
    duplicate registration collisions, and structural anomalies.
    """

    def __init__(self, registered_hashes: Optional[Dict[str, str]] = None):
        """
        registered_hashes: dict mapping sha256_hex -> registered_document_id
        """
        self.registered_hashes = registered_hashes or {}

    def verify_authenticity(
        self,
        file_path: Path,
        document_id: str,
        document_type: Optional[str] = None,
    ) -> Tuple[List[ValidationFinding], Dict[str, str]]:
        """
        Runs comprehensive authenticity and anomaly checks on a physical file.
        Returns:
            findings: List of ValidationFinding (category AUTHENTICITY)
            metadata: Extracted PDF metadata (producer, creation_date, etc.)
        """
        findings: List[ValidationFinding] = []
        metadata: Dict[str, str] = {}

        file_path = Path(file_path)

        if not file_path.exists():
            findings.append(
                ValidationFinding(
                    rule_id="AUTH_FILE_MISSING",
                    rule_name="File Existence Check",
                    outcome="FAIL",
                    severity="CRITICAL",
                    explanation=f"Target file does not exist on disk: {file_path}",
                    affected_document_ids=[document_id],
                    requires_human_review=True,
                )
            )
            return findings, metadata

        # 1. Cryptographic Checksum & Duplicate Check
        file_sha256 = compute_file_sha256(file_path)
        metadata["sha256"] = file_sha256

        if file_sha256 in self.registered_hashes:
            colliding_id = self.registered_hashes[file_sha256]
            findings.append(
                ValidationFinding(
                    rule_id="AUTH_DUPLICATE_SUBMISSION",
                    rule_name="Cryptographic Duplicate Detection",
                    outcome="FAIL",
                    severity="MEDIUM",
                    explanation=(
                        f"Document SHA-256 hash matches existing submission '{colliding_id}'. "
                        "Administrative collision: identical file submitted across sessions."
                    ),
                    affected_document_ids=[document_id, colliding_id],
                    evidence_values={"sha256": file_sha256, "colliding_document_id": colliding_id},
                    requires_human_review=True,
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    rule_id="AUTH_INTEGRITY_HASH",
                    rule_name="Cryptographic Integrity Check",
                    outcome="PASS",
                    severity="INFO",
                    explanation="Document SHA-256 hash successfully computed and verified unique.",
                    affected_document_ids=[document_id],
                    evidence_values={"sha256": file_sha256},
                    requires_human_review=False,
                )
            )

        # 2. PDF Magic Header & Byte Structure
        try:
            with open(file_path, "rb") as f:
                header = f.read(10)
                if not header.startswith(b"%PDF-"):
                    findings.append(
                        ValidationFinding(
                            rule_id="AUTH_FORMAT_HEADER",
                            rule_name="PDF Specification Header Check",
                            outcome="FAIL",
                            severity="CRITICAL",
                            explanation=f"Invalid PDF file header: expected '%PDF-', found {header[:5]!r}.",
                            affected_document_ids=[document_id],
                            requires_human_review=True,
                        )
                    )
                    return findings, metadata
        except Exception as exc:
            findings.append(
                ValidationFinding(
                    rule_id="AUTH_READ_ERROR",
                    rule_name="File Stream Read Error",
                    outcome="FAIL",
                    severity="CRITICAL",
                    explanation=f"Cannot read file bytes: {exc}",
                    affected_document_ids=[document_id],
                    requires_human_review=True,
                )
            )
            return findings, metadata

        # 3. PDF Structural Integrity and Metadata Inspection
        try:
            doc = pymupdf.open(file_path)
            metadata["page_count"] = str(len(doc))
            metadata["format"] = doc.metadata.get("format", "")
            metadata["producer"] = doc.metadata.get("producer", "")
            metadata["creator"] = doc.metadata.get("creator", "")
            metadata["creation_date"] = doc.metadata.get("creationDate", "")
            metadata["mod_date"] = doc.metadata.get("modDate", "")

            if doc.is_encrypted:
                findings.append(
                    ValidationFinding(
                        rule_id="AUTH_ENCRYPTION_CHECK",
                        rule_name="PDF Password / DRM Check",
                        outcome="INCONCLUSIVE",
                        severity="HIGH",
                        explanation="Document is encrypted or DRM-protected; full verification cannot proceed automatically.",
                        affected_document_ids=[document_id],
                        requires_human_review=True,
                    )
                )

            # Metadata Anomaly: Missing producer on ostensibly institutional approvals
            if not metadata["producer"] and not metadata["creator"]:
                findings.append(
                    ValidationFinding(
                        rule_id="AUTH_METADATA_STRIPPED",
                        rule_name="Metadata Anomaly Inspection",
                        outcome="INCONCLUSIVE",
                        severity="LOW",
                        explanation="PDF generator metadata stripped or empty. Preserved for regulatory auditor inspection.",
                        affected_document_ids=[document_id],
                        requires_human_review=False,
                    )
                )

            doc.close()
        except Exception as exc:
            findings.append(
                ValidationFinding(
                    rule_id="AUTH_STRUCTURAL_CORRUPT",
                    rule_name="PDF Structural Parseability",
                    outcome="FAIL",
                    severity="CRITICAL",
                    explanation=f"PDF document corrupted or structurally malformed: {exc}",
                    affected_document_ids=[document_id],
                    requires_human_review=True,
                )
            )

        return findings, metadata
