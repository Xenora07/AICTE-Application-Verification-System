# Deterministic Validation & Cross-Document Consistency Engine

This module implements the Phase 7 deterministic, explainable verification rules and cross-document consistency checks for the SIH26261 document processing pipeline.

**Core Mandates:**
1. **Decision Support Only:** This system provides evidence and rule findings to assist human regulatory officials. It never makes automated application approval decisions.
2. **Honest Ambiguity Handling:** Missing or low-confidence evidence is categorized as `INCONCLUSIVE` and never treated as automated proof of failure.
3. **Evidence Preservation:** Every finding references stable rule IDs, severities, explanations, affected document IDs, and underlying raw/normalized values.
4. **Decoupled Architecture:** Operates strictly on `ExtractionResult` contracts, completely separated from OCR backends, layout mapping, privacy masking, or authenticity services.

---

## 1. Single-Document Validation Rules

### `RULE_FILE_PARSEABLE`
- **Purpose:** Verifies that the PDF input stream was successfully parsed without fatal extraction errors.
- **Required Evidence:** `doc.processing_status` and `doc.errors`.
- **Outcome Logic:**
  - `FAIL` (`CRITICAL`): If `processing_status == "EXTRACTION_ERROR"` or unreadable stream errors exist. `requires_human_review=True`.
  - `PASS` (`INFO`): File structure parsed cleanly.
- **Limitations:** Does not inspect cryptographic signatures or pixel-level image corruption beyond PDF stream parseability.

### `RULE_SCHEMA_CONFORMANCE`
- **Purpose:** Verifies that the payload conforms to the canonical `ExtractionResult` Pydantic contract.
- **Required Evidence:** `doc.fields`, `doc.table_data`, `doc.processing_metadata`.
- **Outcome Logic:**
  - `PASS` (`INFO`): All fields and metadata conform to required types and coordinate bounds.

### `RULE_REQ_ACADEMIC_YEAR`
- **Purpose:** Ensures the mandatory `academic_year` field is present in AICTE approval and mandatory disclosure documents.
- **Required Evidence:** `fields["academic_year"]`, `doc.document_type`, `doc.processing_status`, `doc.processing_metadata`.
- **Outcome Logic:**
  - `PASS` (`INFO`): Valid normalized academic year present (e.g. `"2026-2027"`).
  - `FAIL` (`HIGH`): Field missing from document payload when document type is confidently known to require it (`aicte_eoa`, `aicte_mandatory_disclosure`) and extraction completed reliably.
    *Important:* A missing mapped field fails digital verification but does not necessarily prove that the physical source document lacks the information.
  - `INCONCLUSIVE` (`LOW` / `MEDIUM`): Document type is unknown/generic, extraction failed or was incomplete, raw text could not be normalized, or evidence is uncertain/low-confidence OCR. `requires_human_review=True`.
- **Limitations:** Only legally mandatory for approval and disclosure filings; other certificates pass by default.

### `RULE_FORMAT_APP_ID`
- **Purpose:** Verifies that AICTE Application ID adheres to canonical format.
- **Required Evidence:** `fields["application_id"]`.
- **Outcome Logic:**
  - `PASS` (`INFO`): Matches standard format (e.g. `^1-[0-9]+$`).
  - `FAIL` (`MEDIUM`): Confidently extracted (digital or high-confidence OCR) value unambiguously violates format (e.g. `"INVALID-APP-ID-XYZ"`).
  - `INCONCLUSIVE` (`MEDIUM`): Extraction is low-confidence OCR (< 0.65) or uncertain; uncertain OCR text is never treated as definitive proof of invalidity. Raw text preserved. `requires_human_review=True`.
- **Limitations:** Historical approval letters prior to 2010 used regional formats (`Eastern/...`) rather than numeric IDs.

### `RULE_FORMAT_PERM_ID`
- **Purpose:** Verifies that Permanent Institute ID conforms to regulatory format (`^[1-9]-[0-9]+$`).
- **Required Evidence:** `fields["permanent_institute_id"]`.
- **Outcome Logic:**
  - `PASS` (`INFO`): Matches expected format.
  - `FAIL` (`MEDIUM`): Confidently extracted value is a malformed non-numeric string.
  - `INCONCLUSIVE` (`MEDIUM`): Low-confidence OCR or uncertain extraction. Raw text preserved for adjudication. `requires_human_review=True`.
- **Limitations:** Some institutions list legacy AICTE file numbers rather than modernized portal IDs.

### `RULE_DATE_RANGE_INVALID`
- **Purpose:** Validates that accreditation validity end date is chronologically after the start date.
- **Required Evidence:** `fields["valid_from"]` and `fields["valid_to"]` (ISO 8601 normalized).
- **Outcome Logic:**
  - `PASS` (`INFO`): `valid_to >= valid_from`.
  - `FAIL` (`HIGH`): Confidently extracted dates where `valid_to < valid_from` (inverted chronological range).
  - `INCONCLUSIVE` (`LOW` / `MEDIUM`): One or both dates are unparsed (`None`), missing, or extracted via low-confidence/uncertain OCR. Uncertain OCR is not treated as definitive proof of date invalidity. `requires_human_review=True`.
- **Limitations:** Requires both dates to be present; does not infer missing start dates from certificate issue dates.

### `RULE_CGPA_RANGE`
- **Purpose:** Verifies that NAAC CGPA is within standard regulatory boundaries (`0.0 <= cgpa <= 4.0` or `<= 10.0`).
- **Required Evidence:** `fields["cgpa"]`.
- **Outcome Logic:**
  - `PASS` (`INFO`): Confident value within `[0.0, 10.0]`.
  - `FAIL` (`HIGH`): Confident value $< 0.0$ or $> 10.0$.
  - `INCONCLUSIVE` (`MEDIUM`): Value within bounds but flagged `is_uncertain=True` (e.g. OCR substitution `'O'` $\rightarrow$ `'0'`) or unparseable. `requires_human_review=True`.
- **Limitations:** Cannot distinguish between a 3.5 on a 4.0 scale vs a 3.5 on a 10.0 scale without explicit scale declaration text.

### `RULE_GRADE_VALIDITY`
- **Purpose:** Confirms NAAC accreditation grade is recognized in the official grading scale (`A++`, `A+`, `A`, `B++`, `B+`, `B`, `C`, `D`).
- **Required Evidence:** `fields["accreditation_grade"]`.
- **Outcome Logic:**
  - `PASS` (`INFO`): Grade in recognized regulatory set.
  - `INCONCLUSIVE` (`MEDIUM`): Grade does not match standard letter scale (e.g. historical star ratings, points, alternate grading systems) or was extracted with low-confidence OCR. Unknown grade schemes produce `INCONCLUSIVE`, preserving raw evidence for human adjudication, unless reliable evidence proves violation of an explicitly documented rule. `requires_human_review=True`.
- **Limitations:** Historic NAAC certificates prior to 2016 used star ratings (e.g. 5-star) or letter grades without plus signs.

### `RULE_OCR_CONFIDENCE_THRESHOLD`
- **Purpose:** Flags fields where OCR recognition confidence falls below acceptance threshold ($0.65$).
- **Required Evidence:** `field.confidence` for all fields with `extraction_method == "ocr"`.
- **Outcome Logic:**
  - `PASS` (`INFO`): All OCR fields meet or exceed $0.65$ (or digital extraction).
  - `INCONCLUSIVE` (`MEDIUM`): One or more fields have confidence $< 0.65$. `requires_human_review=True`.
- **Limitations:** Confidence scores reflect OCR engine character probabilities, not factual truth.

### `RULE_AMBIGUOUS_EVIDENCE`
- **Purpose:** Detects conflicting candidates across pages or characters flagged for ambiguity.
- **Required Evidence:** `field.is_uncertain` and `field.uncertainty_reason`.
- **Outcome Logic:**
  - `PASS` (`INFO`): No uncertain fields flagged.
  - `INCONCLUSIVE` (`HIGH`): Conflicting candidates across pages or character substitution detected. `requires_human_review=True`.
- **Limitations:** Relies on extraction mapper's page-level candidate collation.

---

## 2. Cross-Document Consistency Checks

### `RULE_CROSS_INSTITUTION_ID`
- **Purpose:** Ensures Permanent Institute ID matches across multiple documents submitted by the same institution (e.g. AICTE EoA vs Mandatory Disclosure).
- **Required Evidence:** `permanent_institute_id` in at least two documents.
- **Outcome Logic:**
  - `PASS` (`INFO`): Identical ID across all documents.
  - `FAIL` (`CRITICAL`): Discrepant IDs (e.g. `1-4775731` vs `1-9999999`). `requires_human_review=True`.
  - `INCONCLUSIVE` (`MEDIUM`): ID missing or uncertain in one of the compared documents. `requires_human_review=True`.
- **Limitations:** Cannot resolve mergers or historical re-numbering of institutions without official gazette data.

### `RULE_CROSS_INSTITUTION_NAME`
- **Purpose:** Checks alignment of institution names across documents.
- **Required Evidence:** `institution_name` in at least two documents.
- **Outcome Logic:**
  - `PASS` (`INFO`): Normalized names align or share core distinctive tokens.
  - `FAIL` (`HIGH`): Unrelated institution names detected in the same submission bundle. `requires_human_review=True`.
  - `INCONCLUSIVE` (`LOW`): One of the names is uncertain or contains address pollution.
- **Limitations:** Keyword-based matching cannot recognize minor legal name changes or campus branch variations.

### `RULE_CROSS_INTAKE_MISMATCH`
- **Purpose:** Compares approved intake quotas in AICTE EoA against claimed intake quotas in Mandatory Disclosure.
- **Required Evidence:** `approved_courses_and_intake` table in EoA and `programmes_and_intake` table in Disclosure.
- **Outcome Logic:**
  - Does not compare quotas unless programme identity and both intake values are supported by reliable evidence.
  - Safely normalizes programme names and resolves canonical aliases (e.g. `CSE` $\leftrightarrow$ `COMPUTER SCIENCE AND ENGINEERING`).
  - `PASS` (`INFO`): All claimed intake values $\le$ approved intake quotas for all deterministically matched programmes.
  - `FAIL` (`HIGH`): Deterministically matched course where claimed intake exceeds approved quota (e.g. claimed 180 vs approved 120). `requires_human_review=True`.
  - `INCONCLUSIVE` (`MEDIUM`): Programme names differ and equivalence cannot be established deterministically, or intake quota is missing/unparseable in either document. Never emits a false FAIL or potentially incorrect PASS. `requires_human_review=True`.
- **Limitations:** Non-standard specialized course titles without established canonical aliases require human adjudication.

### `RULE_INTEGRITY_DUPLICATE_HASH`
- **Purpose:** Deterministic detection of duplicate documents via cryptographic SHA-256 hash matching.
- **Required Evidence:** `doc.sha256` compared across batch or against registered submission database.
- **Outcome Logic:**
  - `PASS` (`INFO`): Distinct SHA-256 hashes across all documents.
  - `FAIL` (`MEDIUM`): Produces a duplicate-document finding when identical SHA-256 hashes are detected.
    *Important Semantics:* Identical SHA-256 hashes represent an administrative re-submission or redundant file attachment. They do **NOT** imply fraud, tampering, or regulatory non-compliance solely because a duplicate exists. Severity is `MEDIUM` to reflect administrative collision without imputing bad faith.
- **Limitations:** Only detects exact bitwise duplicates; edited or re-scanned copies will have distinct hashes and are evaluated via cross-document field checks instead.
