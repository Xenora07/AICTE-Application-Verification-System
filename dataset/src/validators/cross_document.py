"""
src/validators/cross_document.py - Deterministic cross-document consistency checks for regulatory documents.
Implements consistency checks across multiple submitted documents:
- Permanent Institute ID alignment (RULE_CROSS_INSTITUTION_ID)
- Institution name alignment (RULE_CROSS_INSTITUTION_NAME)
- Academic year alignment (RULE_CROSS_ACADEMIC_YEAR)
- Programme approved vs claimed intake quota check (RULE_CROSS_INTAKE_MISMATCH)
- Duplicate submission detection via SHA-256 hash matching (RULE_INTEGRITY_DUPLICATE_HASH)

Adheres to:
- Missing or low-confidence evidence is INCONCLUSIVE, never assumed to be failure.
- Failures require concrete conflicting evidence.
- Human review is flagged whenever critical discrepancies or uncertainties arise.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from src.mappers.normalizers import COMMON_ACRONYMS
from src.schemas.extraction_result import ExtractionResult
from src.validators.schemas import ValidationFinding


def check_cross_institution_id(docs: List[ExtractionResult]) -> Optional[ValidationFinding]:
    """
    Verify that Permanent Institute ID is identical across all documents
    belonging to the same institution.
    """
    id_records: List[Dict[str, Any]] = []

    for doc in docs:
        ev = doc.fields.get("permanent_institute_id")
        if ev and ev.normalized_value:
            id_records.append({
                "doc_id": doc.document_id,
                "doc_type": doc.document_type,
                "perm_id": str(ev.normalized_value).strip(),
                "is_uncertain": ev.is_uncertain,
                "reason": ev.uncertainty_reason,
            })

    if len(id_records) < 2:
        return None  # Cannot compare fewer than two recorded IDs

    # Check for uncertainty
    uncertain_records = [r for r in id_records if r["is_uncertain"]]
    if uncertain_records:
        u_doc = uncertain_records[0]["doc_id"]
        return ValidationFinding(
            rule_id="RULE_CROSS_INSTITUTION_ID",
            rule_name="Cross-Document Institution ID Alignment",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"Cannot verify Institution ID consistency: ID in document '{u_doc}' is uncertain.",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["permanent_institute_id"],
            evidence_values={"id_records": id_records},
            requires_human_review=True,
        )

    # Check for mismatch
    distinct_ids = {r["perm_id"] for r in id_records}
    if len(distinct_ids) > 1:
        # Format explanation to clearly cite conflicting documents
        doc_a = id_records[0]
        # Select doc_b as the first record whose ID differs from doc_a
        doc_b = next(r for r in id_records[1:] if r["perm_id"] != doc_a["perm_id"])

        def _doc_label(r: Dict[str, Any]) -> str:
            dt = r["doc_type"].lower()
            if "eoa" in dt:
                return "EoA"
            elif "disclosure" in dt:
                return "Disclosure"
            return r["doc_id"]

        label_a = _doc_label(doc_a)
        label_b = _doc_label(doc_b)
        if label_a == label_b:
            label_a = f"{label_a} ({doc_a['doc_id']})"
            label_b = f"{label_b} ({doc_b['doc_id']})"

        return ValidationFinding(
            rule_id="RULE_CROSS_INSTITUTION_ID",
            rule_name="Cross-Document Institution ID Alignment",
            outcome="FAIL",
            severity="CRITICAL",
            explanation=f"Permanent Institute ID mismatch between {label_a} ({doc_a['perm_id']}) and {label_b} ({doc_b['perm_id']})",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["permanent_institute_id"],
            evidence_values={"id_records": id_records, "conflicting_ids": list(distinct_ids)},
            requires_human_review=True,
        )

    matched_id = id_records[0]["perm_id"]
    return ValidationFinding(
        rule_id="RULE_CROSS_INSTITUTION_ID",
        rule_name="Cross-Document Institution ID Alignment",
        outcome="PASS",
        severity="INFO",
        explanation=f"Permanent Institute ID '{matched_id}' is consistent across all {len(id_records)} compared documents.",
        affected_document_ids=[doc.document_id for doc in docs],
        affected_fields=["permanent_institute_id"],
        evidence_values={"permanent_institute_id": matched_id},
        requires_human_review=False,
    )


def _compute_acronym(name: str) -> str:
    """Generate acronym from non-stop words of an institution name."""
    words = re.findall(r"[A-Za-z0-9]+", name)
    stop = {"of", "and", "the", "for", "in", "at", "to", "on", "de"}
    sig_words = [w for w in words if w.lower() not in stop]
    return "".join(w[0].upper() for w in sig_words)


def _is_reliable_acronym_match(name_a: str, name_b: str) -> bool:
    """Check if one name is a reliable acronym of the other."""
    clean_a = re.sub(r"[,\-\.]", " ", name_a).strip()
    clean_b = re.sub(r"[,\-\.]", " ", name_b).strip()

    tokens_a = clean_a.split()
    tokens_b = clean_b.split()

    if len(tokens_a) == 1 and len(tokens_b) > 1:
        short_tok, full_name = tokens_a[0].upper(), clean_b
    elif len(tokens_b) == 1 and len(tokens_a) > 1:
        short_tok, full_name = tokens_b[0].upper(), clean_a
    else:
        return False

    derived = _compute_acronym(full_name)
    if short_tok == derived and (short_tok in COMMON_ACRONYMS or len(short_tok) >= 3):
        return True
    return False


def check_cross_institution_name(docs: List[ExtractionResult]) -> Optional[ValidationFinding]:
    """Verify that institution names across documents correspond to the same institution."""
    name_records: List[Dict[str, Any]] = []

    for doc in docs:
        ev = doc.fields.get("institution_name")
        if ev and ev.normalized_value:
            name_records.append({
                "doc_id": doc.document_id,
                "doc_type": doc.document_type,
                "name": str(ev.normalized_value).strip(),
                "is_uncertain": ev.is_uncertain,
            })

    if len(name_records) < 2:
        return None

    uncertain_records = [r for r in name_records if r["is_uncertain"]]
    if uncertain_records:
        return ValidationFinding(
            rule_id="RULE_CROSS_INSTITUTION_NAME",
            rule_name="Cross-Document Institution Name Alignment",
            outcome="INCONCLUSIVE",
            severity="LOW",
            explanation=f"Institution name in document '{uncertain_records[0]['doc_id']}' is flagged uncertain.",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["institution_name"],
            requires_human_review=True,
        )

    # Simplified token-overlap consistency check
    names = [r["name"].lower() for r in name_records]
    tokens_list = [set(n.split()) for n in names]
    common_tokens = set.intersection(*tokens_list) if tokens_list else set()

    # Filter out generic stop words
    generic = {"college", "institute", "technology", "engineering", "sciences", "of", "and", "the", "for"}
    distinctive_common = common_tokens - generic

    # 1. Distinctive tokens overlap -> PASS
    if distinctive_common:
        return ValidationFinding(
            rule_id="RULE_CROSS_INSTITUTION_NAME",
            rule_name="Cross-Document Institution Name Alignment",
            outcome="PASS",
            severity="INFO",
            explanation=f"Institution names across compared documents align: '{name_records[0]['name']}'.",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["institution_name"],
            evidence_values={"matched_institution_name": name_records[0]["name"]},
            requires_human_review=False,
        )

    # 2. Reliable acronym equivalence (e.g. KGEC vs Kalyani Government Engineering College)
    all_align_acronym = True
    for i in range(len(name_records) - 1):
        if not _is_reliable_acronym_match(name_records[i]["name"], name_records[i + 1]["name"]):
            all_align_acronym = False
            break

    if all_align_acronym and len(name_records) >= 2:
        return ValidationFinding(
            rule_id="RULE_CROSS_INSTITUTION_NAME",
            rule_name="Cross-Document Institution Name Alignment",
            outcome="PASS",
            severity="INFO",
            explanation=f"Institution names across compared documents align via verified acronym equivalence: '{name_records[0]['name']}' and '{name_records[1]['name']}'.",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["institution_name"],
            evidence_values={"names": [r["name"] for r in name_records]},
            requires_human_review=False,
        )

    # 3. Possible acronym or short name that could not be reliably verified -> INCONCLUSIVE
    has_short_name = any(len(r["name"].split()) == 1 for r in name_records)
    if has_short_name:
        return ValidationFinding(
            rule_id="RULE_CROSS_INSTITUTION_NAME",
            rule_name="Cross-Document Institution Name Alignment",
            outcome="INCONCLUSIVE",
            severity="LOW",
            explanation=f"Institution names across documents cannot be deterministically aligned: '{name_records[0]['name']}' vs '{name_records[1]['name']}'. Possible abbreviation or alternate name requires human review.",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["institution_name"],
            evidence_values={"names": [r["name"] for r in name_records]},
            requires_human_review=True,
        )

    # 4. Definitively unrelated multi-token names -> FAIL
    return ValidationFinding(
        rule_id="RULE_CROSS_INSTITUTION_NAME",
        rule_name="Cross-Document Institution Name Alignment",
        outcome="FAIL",
        severity="HIGH",
        explanation=f"Institution name discrepancy across documents: '{name_records[0]['name']}' vs '{name_records[1]['name']}'.",
        affected_document_ids=[doc.document_id for doc in docs],
        affected_fields=["institution_name"],
        evidence_values={"names": [r["name"] for r in name_records]},
        requires_human_review=True,
    )


def _normalize_programme_name(name: str) -> str:
    """
    Safely normalize programme/course title for deterministic comparison.
    Standardizes whitespace, casing, common abbreviations, and degree prefixes.
    """
    if not name:
        return ""
    s = name.strip().upper()
    # Replace & with AND
    s = s.replace("&", " AND ")
    # Replace separators with space
    s = re.sub(r"[\/\-\,\(\)\[\]]", " ", s)
    # Strip degree qualifiers and noisy shift/qualification labels
    noise_patterns = [
        r"\bBACHELOR OF TECHNOLOGY IN\b",
        r"\bBACHELOR OF ENGINEERING IN\b",
        r"\bMASTER OF TECHNOLOGY IN\b",
        r"\bB\.?TECH(\s+IN)?\b",
        r"\bB\.?E\.?(\s+IN)?\b",
        r"\bM\.?TECH(\s+IN)?\b",
        r"\bM\.?E\.?(\s+IN)?\b",
        r"\bUNDER GRADUATE\b",
        r"\bPOST GRADUATE\b",
        r"\bUG\b",
        r"\bPG\b",
        r"\b1ST SHIFT\b",
        r"\b2ND SHIFT\b",
        r"\bFIRST SHIFT\b",
        r"\bSECOND SHIFT\b",
    ]
    for np in noise_patterns:
        s = re.sub(np, " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Canonical dictionary of standardized acronyms
    standard_aliases = {
        "CSE": "COMPUTER SCIENCE AND ENGINEERING",
        "IT": "INFORMATION TECHNOLOGY",
        "ECE": "ELECTRONICS AND COMMUNICATION ENGINEERING",
        "EE": "ELECTRICAL ENGINEERING",
        "ME": "MECHANICAL ENGINEERING",
        "CE": "CIVIL ENGINEERING",
    }
    return standard_aliases.get(s, s)


def _extract_shift_identifier(row: Dict[str, Any], raw_prog: str) -> Optional[str]:
    """Extract normalized shift or division identifier from row data or raw programme title."""
    for key in ("shift", "shift_or_level", "division", "section"):
        val = str(row.get(key) or "").strip().upper()
        if val and val not in ("NONE", "NULL", "N/A", "-", "REGULAR", "GENERAL"):
            if "1" in val or "FIRST" in val:
                return "1ST SHIFT"
            if "2" in val or "SECOND" in val:
                return "2ND SHIFT"
            return val
    # Check embedded shift in raw_prog
    m = re.search(r"\b(1ST\s+SHIFT|2ND\s+SHIFT|FIRST\s+SHIFT|SECOND\s+SHIFT)\b", raw_prog, re.IGNORECASE)
    if m:
        token = m.group(1).upper()
        if "1" in token or "FIRST" in token:
            return "1ST SHIFT"
        if "2" in token or "SECOND" in token:
            return "2ND SHIFT"
        return token
    return None


def _extract_level_identifier(row: Dict[str, Any], raw_prog: str) -> Optional[str]:
    """Extract course level (e.g. UG vs PG) from row or raw title."""
    level = str(row.get("level") or "").strip().upper()
    if level and level not in ("NONE", "NULL", "N/A", "-"):
        if "POST" in level or "PG" in level or "MASTER" in level:
            return "PG"
        if "UNDER" in level or "UG" in level or "BACHELOR" in level:
            return "UG"
        return level
    if re.search(r"\b(M\.?TECH|M\.?E\.?|MASTER|POST\s+GRADUATE|PG)\b", raw_prog, re.IGNORECASE):
        return "PG"
    if re.search(r"\b(B\.?TECH|B\.?E\.?|BACHELOR|UNDER\s+GRADUATE|UG)\b", raw_prog, re.IGNORECASE):
        return "UG"
    return None


def _resolve_programme_intake(
    prog_rows: List[Dict[str, Any]],
    doc_type_label: str,
) -> Tuple[Optional[int], Optional[str], List[Dict[str, Any]]]:
    """
    Resolve aggregate intake capacity across one or more rows for a single normalized programme.
    Returns (aggregate_intake, ambiguity_reason, preserved_row_details).
    - If single row: aggregate_intake = row['intake'].
    - If multiple rows with distinct, additive shifts and compatible qualification levels:
      aggregate_intake = sum(row['intake']).
    - If duplicate rows, conflicting qualification levels, or ambiguous shift identity:
      aggregate_intake = None, ambiguity_reason is returned.
    """
    if not prog_rows:
        return None, "No rows", []

    if len(prog_rows) == 1:
        r = prog_rows[0]
        return r["intake"], None, [dict(r)]

    # Check qualification levels
    levels = {r["level"] for r in prog_rows if r["level"]}
    if len(levels) > 1:
        return None, f"Conflicting qualification levels ({', '.join(sorted(levels))}) across multiple rows in {doc_type_label}", prog_rows

    # Check shift distinctness
    shifts = [r["shift"] for r in prog_rows]
    # Genuinely distinct shifts: all non-None and all unique
    if all(s is not None for s in shifts) and len(set(shifts)) == len(prog_rows):
        total = sum(r["intake"] for r in prog_rows)
        return total, None, prog_rows

    # If any shifts are missing or duplicate
    if any(s is None for s in shifts):
        return None, f"Multiple rows detected in {doc_type_label} without distinct shift differentiation; cannot aggregate capacity reliably without double-counting", prog_rows

    return None, f"Duplicate shift entries ({', '.join(shifts)}) detected in {doc_type_label}; cannot aggregate capacity to avoid inflating quota", prog_rows


def check_cross_intake_mismatch(docs: List[ExtractionResult]) -> Optional[ValidationFinding]:
    """
    Compare approved intake in AICTE EoA table against claimed intake in Mandatory Disclosure table.

    Adheres to:
    - Does not compare quotas unless programme identity and both intake values are supported by reliable evidence.
    - If names differ and equivalence cannot be established deterministically, emits INCONCLUSIVE instead of FAIL or a potentially incorrect PASS.
    - Emits FAIL only when programme identity is deterministically established and claimed intake exceeds approved intake.
    """
    eoa_docs = [d for d in docs if "eoa" in d.document_type]
    disclosure_docs = [d for d in docs if "disclosure" in d.document_type]

    if not eoa_docs or not disclosure_docs:
        return None

    # 1. Extract approved quotas from EoA
    eoa_rows_by_prog: Dict[str, List[Dict[str, Any]]] = {}
    missing_approved_intake: List[Dict[str, Any]] = []

    for doc in eoa_docs:
        for tbl in doc.table_data:
            for row in tbl.rows:
                raw_prog = str(row.get("course") or row.get("programme") or "").strip()
                if not raw_prog or raw_prog.upper() in ("COURSE", "PROGRAMME", "PROGRAM", "NAME"):
                    continue
                norm_prog = _normalize_programme_name(raw_prog)
                if not norm_prog:
                    continue

                raw_intake = row.get("approved_intake") if "approved_intake" in row else row.get("intake")
                if raw_intake is None or str(raw_intake).strip().upper() in ("NONE", "NULL", "N/A", "TBD", ""):
                    missing_approved_intake.append({"raw_prog": raw_prog, "doc_id": doc.document_id})
                    continue

                try:
                    intake_int = int(raw_intake)
                    if intake_int < 0:
                        missing_approved_intake.append({"raw_prog": raw_prog, "doc_id": doc.document_id})
                    else:
                        shift_id = _extract_shift_identifier(row, raw_prog)
                        level_id = _extract_level_identifier(row, raw_prog)
                        eoa_rows_by_prog.setdefault(norm_prog, []).append({
                            "raw": raw_prog,
                            "intake": intake_int,
                            "shift": shift_id,
                            "level": level_id,
                            "doc_id": doc.document_id,
                        })
                except (ValueError, TypeError):
                    missing_approved_intake.append({"raw_prog": raw_prog, "doc_id": doc.document_id})

    # 2. Extract claimed intake from Disclosure
    disclosure_rows_by_prog: Dict[str, List[Dict[str, Any]]] = {}
    missing_claimed_intake: List[Dict[str, Any]] = []

    for doc in disclosure_docs:
        for tbl in doc.table_data:
            for row in tbl.rows:
                raw_prog = str(row.get("course") or row.get("programme") or "").strip()
                if not raw_prog or raw_prog.upper() in ("COURSE", "PROGRAMME", "PROGRAM", "NAME"):
                    continue
                norm_prog = _normalize_programme_name(raw_prog)
                if not norm_prog:
                    continue

                raw_intake = (
                    row.get("claimed_intake")
                    if "claimed_intake" in row
                    else (row.get("intake") if "intake" in row else row.get("approved_intake"))
                )
                if raw_intake is None or str(raw_intake).strip().upper() in ("NONE", "NULL", "N/A", "TBD", ""):
                    missing_claimed_intake.append({"raw_prog": raw_prog, "doc_id": doc.document_id})
                    continue

                try:
                    intake_int = int(raw_intake)
                    if intake_int < 0:
                        missing_claimed_intake.append({"raw_prog": raw_prog, "doc_id": doc.document_id})
                    else:
                        shift_id = _extract_shift_identifier(row, raw_prog)
                        level_id = _extract_level_identifier(row, raw_prog)
                        disclosure_rows_by_prog.setdefault(norm_prog, []).append({
                            "raw": raw_prog,
                            "intake": intake_int,
                            "shift": shift_id,
                            "level": level_id,
                            "doc_id": doc.document_id,
                        })
                except (ValueError, TypeError):
                    missing_claimed_intake.append({"raw_prog": raw_prog, "doc_id": doc.document_id})

    if not eoa_rows_by_prog and not disclosure_rows_by_prog:
        return None  # No course tables present

    # 3. Check for missing or unparseable intake values
    if missing_approved_intake:
        first = missing_approved_intake[0]
        return ValidationFinding(
            rule_id="RULE_CROSS_INTAKE_MISMATCH",
            rule_name="Cross-Document Programme Intake Quota Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"Cannot verify intake quota for programme '{first['raw_prog']}': approved intake value is missing or unparseable in AICTE EoA ('{first['doc_id']}').",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["approved_courses_and_intake", "programmes_and_intake"],
            evidence_values={"missing_approved_intake": missing_approved_intake},
            requires_human_review=True,
        )

    if missing_claimed_intake:
        first = missing_claimed_intake[0]
        return ValidationFinding(
            rule_id="RULE_CROSS_INTAKE_MISMATCH",
            rule_name="Cross-Document Programme Intake Quota Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=f"Cannot verify intake quota for programme '{first['raw_prog']}': claimed intake value is missing or unparseable in Mandatory Disclosure ('{first['doc_id']}').",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["approved_courses_and_intake", "programmes_and_intake"],
            evidence_values={"missing_claimed_intake": missing_claimed_intake},
            requires_human_review=True,
        )

    # 4. Resolve multi-row / multi-shift intake capacity
    approved_quotas: Dict[str, Dict[str, Any]] = {}
    for norm_p, rows in eoa_rows_by_prog.items():
        appr_intake, ambiguity, row_details = _resolve_programme_intake(rows, "AICTE EoA")
        if ambiguity:
            return ValidationFinding(
                rule_id="RULE_CROSS_INTAKE_MISMATCH",
                rule_name="Cross-Document Programme Intake Quota Verification",
                outcome="INCONCLUSIVE",
                severity="MEDIUM",
                explanation=f"Cannot verify approved intake quota for programme '{norm_p}': {ambiguity}.",
                affected_document_ids=[doc.document_id for doc in docs],
                affected_fields=["approved_courses_and_intake", "programmes_and_intake"],
                evidence_values={"programme": norm_p, "row_details": row_details},
                requires_human_review=True,
            )
        approved_quotas[norm_p] = {"raw": rows[0]["raw"], "intake": appr_intake, "rows": row_details, "doc_id": rows[0]["doc_id"]}

    claimed_quotas: Dict[str, Dict[str, Any]] = {}
    for norm_p, rows in disclosure_rows_by_prog.items():
        claim_intake, ambiguity, row_details = _resolve_programme_intake(rows, "Mandatory Disclosure")
        if ambiguity:
            return ValidationFinding(
                rule_id="RULE_CROSS_INTAKE_MISMATCH",
                rule_name="Cross-Document Programme Intake Quota Verification",
                outcome="INCONCLUSIVE",
                severity="MEDIUM",
                explanation=f"Cannot verify claimed intake quota for programme '{norm_p}': {ambiguity}.",
                affected_document_ids=[doc.document_id for doc in docs],
                affected_fields=["approved_courses_and_intake", "programmes_and_intake"],
                evidence_values={"programme": norm_p, "row_details": row_details},
                requires_human_review=True,
            )
        claimed_quotas[norm_p] = {"raw": rows[0]["raw"], "intake": claim_intake, "rows": row_details, "doc_id": rows[0]["doc_id"]}

    # 5. Deterministic programme matching and quota comparison
    violations: List[Dict[str, Any]] = []
    unmatched_claimed: List[Dict[str, Any]] = []

    for claim_norm, claim_info in claimed_quotas.items():
        if claim_norm in approved_quotas:
            appr_info = approved_quotas[claim_norm]
            if claim_info["intake"] > appr_info["intake"]:
                violations.append({
                    "programme_raw": claim_info["raw"],
                    "programme_norm": claim_norm,
                    "claimed": claim_info["intake"],
                    "approved": appr_info["intake"],
                })
        else:
            unmatched_claimed.append(claim_info)

    # If any deterministic match violates quota, emit FAIL
    if violations:
        first_v = violations[0]
        prog_display = first_v["programme_raw"].title()
        return ValidationFinding(
            rule_id="RULE_CROSS_INTAKE_MISMATCH",
            rule_name="Cross-Document Programme Intake Quota Verification",
            outcome="FAIL",
            severity="HIGH",
            explanation=f"Intake for {prog_display} exceeds approved quota: claimed {first_v['claimed']}, approved {first_v['approved']}",
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["approved_courses_and_intake", "programmes_and_intake"],
            evidence_values={
                "programme": first_v["programme_raw"],
                "claimed_intake": first_v["claimed"],
                "approved_intake": first_v["approved"],
                "all_violations": violations,
            },
            requires_human_review=True,
        )

    # If names differ and equivalence cannot be established deterministically, emit INCONCLUSIVE
    if unmatched_claimed:
        first_u = unmatched_claimed[0]
        return ValidationFinding(
            rule_id="RULE_CROSS_INTAKE_MISMATCH",
            rule_name="Cross-Document Programme Intake Quota Verification",
            outcome="INCONCLUSIVE",
            severity="MEDIUM",
            explanation=(
                f"Programme '{first_u['raw']}' in Mandatory Disclosure cannot be deterministically matched to "
                f"approved courses in AICTE EoA ({list(approved_quotas.keys())}). Equivalence is ambiguous; human adjudication required."
            ),
            affected_document_ids=[doc.document_id for doc in docs],
            affected_fields=["approved_courses_and_intake", "programmes_and_intake"],
            evidence_values={
                "unmatched_programme": first_u["raw"],
                "claimed_intake": first_u["intake"],
                "approved_programmes": list(approved_quotas.keys()),
            },
            requires_human_review=True,
        )

    # All claimed programmes deterministically matched and within approved quota
    return ValidationFinding(
        rule_id="RULE_CROSS_INTAKE_MISMATCH",
        rule_name="Cross-Document Programme Intake Quota Verification",
        outcome="PASS",
        severity="INFO",
        explanation="Claimed programme intake quotas across all matching courses remain within AICTE approved limits.",
        affected_document_ids=[doc.document_id for doc in docs],
        affected_fields=["approved_courses_and_intake", "programmes_and_intake"],
        evidence_values={
            "approved_quotas": {k: v["intake"] for k, v in approved_quotas.items()},
            "claimed_quotas": {k: v["intake"] for k, v in claimed_quotas.items()},
            "approved_row_details": {k: v["rows"] for k, v in approved_quotas.items()},
            "claimed_row_details": {k: v["rows"] for k, v in claimed_quotas.items()},
        },
        requires_human_review=False,
    )


def check_duplicate_hash(
    docs: List[ExtractionResult],
    registered_hashes: Optional[Dict[str, str]] = None,
) -> Optional[ValidationFinding]:
    """
    Deterministic duplicate document detection based on exact SHA-256 hash matching.
    Checks:
    1. Between documents in the current batch.
    2. Against an external/pre-existing submission registry (mapping sha256 -> previous_doc_id).

    Duplicate-hash semantics:
    - Produces a duplicate-document finding when identical SHA-256 hashes are detected.
    - Note: duplicate document upload indicates an identical re-submission or redundant file attachment,
      and does NOT imply fraud, tampering, or regulatory non-compliance solely because a duplicate exists.
    - Finding severity is MEDIUM to reflect an administrative duplicate without imputing bad faith.
    """
    # 1. Check against registered hashes (e.g. from existing submissions or previous application sessions)
    if registered_hashes:
        for doc in docs:
            if doc.sha256 and doc.sha256 in registered_hashes:
                prev_id = registered_hashes[doc.sha256]
                if prev_id != doc.document_id:
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
                        affected_document_ids=[doc.document_id, prev_id],
                        evidence_values={
                            "document_id": doc.document_id,
                            "sha256": doc.sha256,
                            "matching_registered_doc_id": prev_id,
                        },
                        requires_human_review=False,
                    )

    # 2. Check within current batch
    seen_hashes: Dict[str, str] = {}
    for doc in docs:
        if not doc.sha256:
            continue
        if doc.sha256 in seen_hashes:
            orig_doc_id = seen_hashes[doc.sha256]
            return ValidationFinding(
                rule_id="RULE_INTEGRITY_DUPLICATE_HASH",
                rule_name="Deterministic Duplicate Document Hash Verification",
                outcome="FAIL",
                severity="MEDIUM",
                explanation=(
                    f"Duplicate document detected in batch: sha256 '{doc.sha256[:12]}...' matches '{orig_doc_id}'. "
                    f"Note: duplicate document upload indicates an identical re-submission or redundant file "
                    f"attachment and does not imply fraud or regulatory non-compliance."
                ),
                affected_document_ids=[doc.document_id, orig_doc_id],
                evidence_values={"sha256": doc.sha256, "first_seen_doc_id": orig_doc_id},
                requires_human_review=False,
            )
        seen_hashes[doc.sha256] = doc.document_id

    return ValidationFinding(
        rule_id="RULE_INTEGRITY_DUPLICATE_HASH",
        rule_name="Deterministic Duplicate Document Hash Verification",
        outcome="PASS",
        severity="INFO",
        explanation="All submitted documents have distinct cryptographic SHA-256 hashes.",
        affected_document_ids=[doc.document_id for doc in docs],
        requires_human_review=False,
    )
