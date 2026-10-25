"""
backend/security/authenticity.py - Authenticity & Anomaly Detection Gateway for SIH26261 (Person 3).
Inspects cryptographic integrity, detects duplicate submissions, and flags metadata anomalies.

Key Mandates:
1. Keep compliance findings strictly distinct from authenticity assessments.
2. Passing validation does NOT prove authenticity.
3. Suspected anomalies are flagged as 'NEEDS_HUMAN_REVIEW', NEVER labeled as confirmed fraud.
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pymupdf

from backend.common.models import ValidationFinding


def compute_file_sha256(file_path: Path) -> str:
    """Compute standard lowercase 64-char SHA-256 checksum."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


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
