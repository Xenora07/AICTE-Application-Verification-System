"""
generate_manifest.py - Deterministic dataset manifest generator for SIH26261.

Scans real_documents/ and scanned_documents/, inspects PDF structure via PyMuPDF,
computes cryptographic checksums, performs multi-factor text/image detection,
and writes data_manifest.csv at the project root using standard csv.DictWriter.
"""

import csv
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_DIRS = [
    ("real_documents", "DOC_REAL"),
    ("scanned_documents", "DOC_SCAN"),
]

MANIFEST_COLUMNS = [
    "doc_id",
    "relative_path",
    "file_name",
    "dataset_category",
    "file_type",
    "file_size_bytes",
    "page_count",
    "has_embedded_text",
    "ocr_required",
    "sha256_checksum",
    "processing_status",
    "document_type",
    "source_provenance",
    "notes",
]


def compute_sha256(file_path: Path) -> str:
    """Compute full 64-character lowercase SHA-256 checksum."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def analyze_pdf_pages(doc: pymupdf.Document) -> Tuple[int, int, int, int, str]:
    """
    Perform multi-factor analysis on all pages of a PDF:
    - Counts pages with sufficient selectable digital text.
    - Counts pages that require OCR (raster image present with insufficient text).
    - Accumulates total digital character count and word count.
    - Collects leading textual snippet for classification.
    """
    pages_with_digital_text = 0
    pages_requiring_ocr = 0
    total_chars = 0
    total_words = 0
    full_text_corpus: List[str] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text()
        raw_chars = len(text.strip())
        words = [w for w in text.split() if any(c.isalnum() for c in w)]
        word_count = len(words)
        img_count = len(page.get_images())

        total_chars += raw_chars
        total_words += word_count
        if raw_chars > 0:
            full_text_corpus.append(text[:2000])

        # Multi-factor decision for digital vs scanned page:
        # A page is considered digitally readable if it has at least 10 words and 50 chars of text.
        is_digital_page = word_count >= 10 and raw_chars >= 50

        # A page requires OCR if it has raster images and lacks sufficient digital text.
        is_ocr_page = img_count > 0 and word_count < 10

        if is_digital_page:
            pages_with_digital_text += 1
        if is_ocr_page or (word_count == 0 and raw_chars == 0):
            pages_requiring_ocr += 1

    sample_text = "\n".join(full_text_corpus)
    return pages_with_digital_text, pages_requiring_ocr, total_chars, total_words, sample_text


def classify_document(sample_text: str, filename: str) -> Tuple[str, str, str]:
    """
    Deterministically infer document_type, source_provenance, and notes.
    Never invents unverified provenance.
    """
    text_upper = sample_text.upper()
    fname_upper = filename.upper()

    doc_type = "unknown"
    provenance = "undetermined"
    notes_list: List[str] = []

    # Check for duplicate extension quirk
    if filename.endswith(".pdf.pdf"):
        notes_list.append("Double .pdf.pdf extension in filename")

    # 1. AICTE Extension of Approval (EoA)
    if (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION" in text_upper
        or "EXTENSION OF APPROVAL" in text_upper
        or "EOA" in fname_upper
    ):
        doc_type = "aicte_eoa"
        if "KALYANI GOVERNMENT ENGINEERING COLLEGE" in text_upper or "KGEC" in fname_upper:
            provenance = "Kalyani Government Engineering College"
        elif "BHARATI VIDYAPEETH" in text_upper:
            provenance = "Bharati Vidyapeeth's College of Engineering"
        else:
            provenance = "AICTE Approved Institution (see document body)"

    # 2. AICTE Mandatory Disclosure
    elif "MANDATORY DISCLOSURE" in text_upper or "MANDATORY_DISCLOSURE" in fname_upper:
        doc_type = "aicte_mandatory_disclosure"
        if "BHARATI VIDYAPEETH" in text_upper:
            provenance = "Bharati Vidyapeeth's College of Engineering"
        elif "WESTERN/1-" in text_upper:
            provenance = "AICTE Western Region Institution"
        elif "SOUTHERN/1-" in text_upper:
            provenance = "AICTE Southern Region Institution"
        else:
            provenance = "Public Institutional Disclosure"

    # 3. NAAC Certificate
    elif "NAAC" in text_upper or "NAAC" in fname_upper or "NATIONAL ASSESSMENT AND ACCREDITATION" in text_upper:
        doc_type = "naac_certificate"
        if "YASHWANTRAO CHAVAN" in text_upper:
            provenance = "Yashwantrao Chavan Maharashtra Open University"
        else:
            provenance = "undetermined_scanned"

    # 4. NBA Accreditation Letter
    elif "NBA" in text_upper or "NBA" in fname_upper or "NATIONAL BOARD OF ACCREDITATION" in text_upper:
        doc_type = "nba_accreditation"
        if "C.B.I.T" in text_upper or "CHAITANYA BHARATHI" in text_upper:
            provenance = "Chaitanya Bharathi Institute of Technology"
        else:
            provenance = "undetermined_scanned"

    # 5. Academic Coursework / Anomaly
    elif "COMPUTER ARCHITECTURE AND MICROPROCESSOR" in text_upper or "CAMP SLA" in fname_upper:
        doc_type = "unrecognized_academic"
        provenance = "Student Coursework Assignment"
        notes_list.append("Negative control: 8086 microprocessors assignment; out-of-scope for regulatory pipeline")

    # Fallback for purely scanned documents without OCR text yet
    if doc_type == "unknown":
        if "NAAC" in fname_upper:
            doc_type = "naac_certificate"
            provenance = "undetermined_scanned"
            notes_list.append("Purely scanned NAAC certificate; OCR required for text extraction")
        elif "NBA" in fname_upper:
            doc_type = "nba_accreditation"
            provenance = "undetermined_scanned"
            notes_list.append("Purely scanned NBA accreditation; OCR required for text extraction")
        elif "ACCR" in fname_upper:
            doc_type = "nba_accreditation"
            provenance = "undetermined_scanned"
            notes_list.append("Scanned accreditation document; OCR required for text extraction")

    notes = "; ".join(notes_list) if notes_list else "Standard document"
    return doc_type, provenance, notes


def generate_manifest(project_root: Path = PROJECT_ROOT) -> List[Dict[str, Any]]:
    """Scan documents, inspect metadata, and return manifest rows."""
    manifest_rows: List[Dict[str, Any]] = []

    for dir_name, id_prefix in DATASET_DIRS:
        target_dir = project_root / dir_name
        if not target_dir.exists():
            continue

        file_list = sorted([f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"])

        for idx, file_path in enumerate(file_list, start=1):
            doc_id = f"{id_prefix}_{idx:03d}"
            # Relative path with forward slashes for cross-platform stability
            rel_path = f"{dir_name}/{file_path.name}"
            file_size = file_path.stat().st_size
            sha256 = compute_sha256(file_path)

            status = "healthy"
            total_pages = 0
            has_embedded = False
            ocr_req = "full"
            doc_type = "unknown"
            provenance = "undetermined"
            notes = ""

            try:
                doc = pymupdf.open(file_path)
                total_pages = len(doc)
                if doc.is_encrypted:
                    status = "password_protected"
                else:
                    digital_pages, ocr_pages, total_chars, total_words, sample_text = analyze_pdf_pages(doc)
                    has_embedded = total_chars > 50

                    if ocr_pages == 0 and digital_pages > 0:
                        ocr_req = "none"
                    elif digital_pages == 0:
                        ocr_req = "full"
                    else:
                        ocr_req = "hybrid"

                    doc_type, provenance, auto_notes = classify_document(sample_text, file_path.name)

                    notes_parts = []
                    if auto_notes and auto_notes != "Standard document":
                        notes_parts.append(auto_notes)
                    if ocr_req == "hybrid":
                        notes_parts.append(f"Hybrid: {digital_pages} digital pages, {ocr_pages} scanned pages")
                    if total_pages > 40:
                        notes_parts.append(f"High page count ({total_pages} pages)")

                    notes = "; ".join(notes_parts) if notes_parts else "Standard document"

                doc.close()
            except Exception as exc:
                status = "corrupted"
                notes = f"Error reading PDF: {exc}"

            row = {
                "doc_id": doc_id,
                "relative_path": rel_path,
                "file_name": file_path.name,
                "dataset_category": dir_name,
                "file_type": "pdf",
                "file_size_bytes": file_size,
                "page_count": total_pages,
                "has_embedded_text": str(has_embedded).lower(),
                "ocr_required": ocr_req,
                "sha256_checksum": sha256,
                "processing_status": status,
                "document_type": doc_type,
                "source_provenance": provenance,
                "notes": notes,
            }
            manifest_rows.append(row)

    return manifest_rows


def write_manifest_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    """Write rows to CSV file using standard csv.DictWriter with RFC 4180 compliance."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def validate_manifest_csv(csv_path: Path) -> bool:
    """Validate that the generated CSV is structurally sound and meets all requirements."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Manifest not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != MANIFEST_COLUMNS:
            raise ValueError(f"Header mismatch. Found: {reader.fieldnames}, Expected: {MANIFEST_COLUMNS}")

        rows = list(reader)

    if len(rows) == 0:
        raise ValueError("Manifest is empty!")

    doc_ids = set()
    for i, row in enumerate(rows, start=1):
        # 1. No empty values in required fields
        for col in MANIFEST_COLUMNS:
            val = row.get(col, "")
            if val is None or val.strip() == "":
                raise ValueError(f"Row {i} has empty column '{col}'")

        # 2. Check doc_id uniqueness and format
        doc_id = row["doc_id"]
        if doc_id in doc_ids:
            raise ValueError(f"Duplicate doc_id found: {doc_id}")
        doc_ids.add(doc_id)

        # 3. Check SHA-256 validity
        sha = row["sha256_checksum"]
        if len(sha) != 64 or not all(c in "0123456789abcdefABCDEF" for c in sha):
            raise ValueError(f"Invalid SHA-256 hash in row {i}: {sha}")

        # 4. Check relative path existence and forward slashes
        rel_p = row["relative_path"]
        if "\\" in rel_p:
            raise ValueError(f"Row {i} contains backslash in path: {rel_p}")
        target_file = PROJECT_ROOT / rel_p
        if not target_file.exists():
            raise FileNotFoundError(f"Row {i} references non-existent file: {target_file}")

        # 5. Check numeric fields
        int(row["file_size_bytes"])
        int(row["page_count"])

        # 6. Check boolean and enum fields
        assert row["has_embedded_text"] in ("true", "false"), f"Invalid boolean: {row['has_embedded_text']}"
        assert row["ocr_required"] in ("none", "full", "hybrid"), f"Invalid ocr_required: {row['ocr_required']}"
        assert row["processing_status"] in ("healthy", "unsupported_type", "corrupted", "password_protected"), (
            f"Invalid processing_status: {row['processing_status']}"
        )

    print(f"Validation successful: {len(rows)} document rows verified against schema.")
    return True


if __name__ == "__main__":
    out_csv = PROJECT_ROOT / "data_manifest.csv"
    print(f"Scanning dataset and generating manifest at: {out_csv}")
    rows = generate_manifest(PROJECT_ROOT)
    write_manifest_csv(rows, out_csv)
    validate_manifest_csv(out_csv)
    print(f"Generated {len(rows)} records successfully.")
