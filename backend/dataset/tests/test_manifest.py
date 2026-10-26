"""
tests/test_manifest.py - Rigorous automated verification for data_manifest.csv.
"""

import csv
import hashlib
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "data_manifest.csv"

EXPECTED_COLUMNS = [
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


def test_manifest_file_exists():
    """Verify data_manifest.csv exists in the project root."""
    assert MANIFEST_PATH.exists(), f"Missing manifest at {MANIFEST_PATH}"


def test_manifest_header_and_columns():
    """Verify header columns match the locked schema exactly."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == EXPECTED_COLUMNS, f"Header mismatch: {header} vs {EXPECTED_COLUMNS}"


def test_manifest_row_count_and_uniqueness():
    """Verify document rows match actual files on disk and IDs are unique."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Count actual PDFs on disk
    real_pdfs = list((PROJECT_ROOT / "real_documents").glob("*.pdf"))
    scan_pdfs = list((PROJECT_ROOT / "scanned_documents").glob("*.pdf"))
    total_disk_pdfs = len(real_pdfs) + len(scan_pdfs)

    assert len(rows) == total_disk_pdfs, f"Expected {total_disk_pdfs} rows, found {len(rows)}"

    doc_ids = [r["doc_id"] for r in rows]
    assert len(doc_ids) == len(set(doc_ids)), "Duplicate doc_id found in manifest"

    # Verify ID format
    for doc_id in doc_ids:
        assert doc_id.startswith("DOC_REAL_") or doc_id.startswith("DOC_SCAN_"), (
            f"Invalid doc_id format: {doc_id}"
        )


def test_manifest_checksums_and_file_integrity():
    """Verify SHA-256 hashes, file sizes, page counts, and disk file existence."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for idx, row in enumerate(rows, start=1):
        rel_path = row["relative_path"]
        assert "\\" not in rel_path, f"Row {idx} contains backslashes: {rel_path}"

        disk_file = PROJECT_ROOT / rel_path
        assert disk_file.exists(), f"Row {idx} points to non-existent file: {disk_file}"
        assert disk_file.name == row["file_name"], f"Row {idx} filename mismatch"

        # Check file size matches
        actual_size = disk_file.stat().st_size
        assert int(row["file_size_bytes"]) == actual_size, (
            f"Row {idx} file size mismatch: {row['file_size_bytes']} vs {actual_size}"
        )

        # Check page count
        page_count = int(row["page_count"])
        assert page_count > 0, f"Row {idx} invalid page count: {page_count}"

        # Re-compute and verify SHA-256
        h = hashlib.sha256()
        with open(disk_file, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        expected_sha = h.hexdigest()
        assert row["sha256_checksum"] == expected_sha, f"Row {idx} SHA-256 mismatch"

        # Check values in valid ranges
        assert row["has_embedded_text"] in ("true", "false")
        assert row["ocr_required"] in ("none", "full", "hybrid")
        assert row["processing_status"] in ("healthy", "unsupported_type", "corrupted", "password_protected")
        assert len(row["source_provenance"].strip()) > 0
        assert len(row["notes"].strip()) > 0


def test_manifest_reproducibility():
    """Ensure running generate_manifest produces deterministic output identical to disk."""
    from scripts.generate_manifest import generate_manifest, MANIFEST_COLUMNS

    fresh_rows = generate_manifest(PROJECT_ROOT)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        existing_rows = list(csv.DictReader(f))

    assert len(fresh_rows) == len(existing_rows), "Row count differed on regeneration"
    for fresh, existing in zip(fresh_rows, existing_rows):
        for col in MANIFEST_COLUMNS:
            assert str(fresh[col]) == str(existing[col]), f"Discrepancy in col {col} for {fresh['doc_id']}"
