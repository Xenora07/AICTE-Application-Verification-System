"""
tests/test_synthetic_scenarios.py - Automated verification for all 10 synthetic test scenarios and fixtures.
Verifies schema, uniqueness, honest confidence values, fixture isolation, and scenario logic.
"""

import json
import re
from pathlib import Path
import pytest
import pymupdf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_DIR = PROJECT_ROOT / "test_cases"
TEST_MANIFEST_PATH = TEST_CASES_DIR / "test_manifest.json"

VALID_SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_OUTCOMES = {
    "SUCCESS",
    "FAILED_VALIDATION",
    "FAILED_CONSISTENCY",
    "DUPLICATE_DETECTED",
    "NEEDS_HUMAN_REVIEW",
    "EXTRACTION_ERROR",
}

EXPECTED_SCENARIO_IDS = [
    "TC_SYNTH_001",
    "TC_SYNTH_002",
    "TC_SYNTH_003",
    "TC_SYNTH_004",
    "TC_SYNTH_005",
    "TC_SYNTH_006",
    "TC_SYNTH_007",
    "TC_SYNTH_008",
    "TC_SYNTH_009",
    "TC_SYNTH_010",
]


def load_synthetic_manifest():
    with open(TEST_MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_synthetic_manifest_exists_and_count():
    """Verify test_manifest.json exists and contains exactly 10 defined scenarios."""
    assert TEST_MANIFEST_PATH.exists(), f"Missing synthetic test manifest: {TEST_MANIFEST_PATH}"
    cases = load_synthetic_manifest()
    assert isinstance(cases, list)
    assert len(cases) == 10, f"Expected exactly 10 scenarios, found {len(cases)}"
    ids = [c["test_id"] for c in cases]
    assert ids == EXPECTED_SCENARIO_IDS, f"Scenario IDs mismatch: {ids}"


def test_synthetic_case_schema_and_uniqueness():
    """Verify scenario schema, unique IDs, explicit descriptions, and valid machine-readable outcomes."""
    cases = load_synthetic_manifest()
    seen_ids = set()

    for case in cases:
        test_id = case["test_id"]
        assert test_id not in seen_ids, f"Duplicate test_id: {test_id}"
        seen_ids.add(test_id)
        assert re.match(r"^TC_SYNTH_\d{3}$", test_id), f"Invalid test_id pattern: {test_id}"

        assert case.get("scenario_name", "").strip() != "", f"Empty scenario_name in {test_id}"
        assert case.get("description", "").strip() != "", f"Empty description in {test_id}"
        assert case.get("purpose", "").strip() != "", f"Empty purpose in {test_id}"
        assert case.get("is_synthetic") is True, f"Scenario {test_id} must have is_synthetic=True"

        assert case["expected_outcome"] in VALID_OUTCOMES, f"Invalid outcome in {test_id}: {case['expected_outcome']}"
        assert case["expected_severity"] in VALID_SEVERITIES, f"Invalid severity in {test_id}: {case['expected_severity']}"
        assert isinstance(case["requires_human_review"], bool), f"Invalid requires_human_review in {test_id}"
        assert len(case["expected_rule_ids"]) > 0, f"Missing rule IDs in {test_id}"


def test_fixture_isolation_and_paths():
    """Verify all fixtures reside in test_cases/fixtures/ and never reference real collected PDFs."""
    cases = load_synthetic_manifest()

    for case in cases:
        fixtures = case["fixture_references"]
        assert len(fixtures) > 0, f"Scenario {case['test_id']} has no fixture references"
        for fix_rel in fixtures:
            # Check relative path
            assert fix_rel.startswith("test_cases/fixtures/"), f"Fixture {fix_rel} not in test_cases/fixtures/"
            assert "real_documents" not in fix_rel, f"Fixture {fix_rel} leaks into real_documents"
            assert "scanned_documents" not in fix_rel, f"Fixture {fix_rel} leaks into scanned_documents"

            fix_path = PROJECT_ROOT / fix_rel
            assert fix_path.exists(), f"Fixture file not found: {fix_path}"


def test_honest_confidence_in_fixtures():
    """Verify no invented classification confidence and simulated OCR confidence is explicitly labeled."""
    fixtures_dir = TEST_CASES_DIR / "fixtures"

    for json_file in fixtures_dir.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Classification confidence must never be invented (must be null/None)
        if "classification_confidence" in data:
            assert data["classification_confidence"] is None, (
                f"Invented classification_confidence in {json_file.name}: {data['classification_confidence']}"
            )

        # In OCR fixtures with simulated confidence, must be labeled as synthetic
        if "processing_metadata" in data and data["processing_metadata"].get("extraction_path") == "ocr":
            backend = data["processing_metadata"].get("ocr_backend")
            assert backend in ("synthetic_test_engine", "synthetic_test_fixture"), (
                f"OCR fixture {json_file.name} missing synthetic backend label: {backend}"
            )


def test_tc09_malformed_fixture_robustness():
    """Verify TC_SYNTH_009 genuinely malformed binary raises Exception without segfault."""
    malformed_path = PROJECT_ROOT / "test_cases/fixtures/tc09_malformed_unreadable.bin"
    assert malformed_path.exists()
    assert malformed_path.suffix == ".bin", "Malformed fixture must not be disguised as .pdf"

    with pytest.raises(Exception):
        doc = pymupdf.open(malformed_path)
        _ = len(doc)
        doc.close()


@pytest.mark.parametrize("scenario_id", EXPECTED_SCENARIO_IDS)
def test_each_synthetic_scenario_outcome_logic(scenario_id: str):
    """Validate scenario-specific logic and expected findings for each of the 10 scenarios."""
    cases = {c["test_id"]: c for c in load_synthetic_manifest()}
    case = cases[scenario_id]

    if scenario_id == "TC_SYNTH_001":
        # Valid structured fields -> SUCCESS
        assert case["expected_outcome"] == "SUCCESS"
        assert len(case["expected_findings"]) == 0
        assert case["expected_severity"] == "INFO"
        assert case["requires_human_review"] is False

    elif scenario_id == "TC_SYNTH_002":
        # Missing required field -> FAILED_VALIDATION
        assert case["expected_outcome"] == "FAILED_VALIDATION"
        assert "RULE_REQ_ACADEMIC_YEAR" in case["expected_rule_ids"]
        assert case["expected_severity"] == "HIGH"
        assert case["requires_human_review"] is False

    elif scenario_id == "TC_SYNTH_003":
        # Invalid ID format -> FAILED_VALIDATION
        assert case["expected_outcome"] == "FAILED_VALIDATION"
        assert "RULE_FORMAT_APP_ID" in case["expected_rule_ids"]
        assert case["expected_severity"] == "MEDIUM"

    elif scenario_id == "TC_SYNTH_004":
        # Inconsistent dates -> FAILED_VALIDATION
        assert case["expected_outcome"] == "FAILED_VALIDATION"
        assert "RULE_DATE_RANGE_INVALID" in case["expected_rule_ids"]
        assert case["expected_severity"] == "HIGH"

    elif scenario_id == "TC_SYNTH_005":
        # Cross-document institution ID mismatch -> FAILED_CONSISTENCY
        assert case["expected_outcome"] == "FAILED_CONSISTENCY"
        assert "RULE_CROSS_INSTITUTION_ID" in case["expected_rule_ids"]
        assert case["expected_severity"] == "CRITICAL"
        assert case["requires_human_review"] is True

    elif scenario_id == "TC_SYNTH_006":
        # Programme/intake mismatch -> FAILED_CONSISTENCY
        assert case["expected_outcome"] == "FAILED_CONSISTENCY"
        assert "RULE_CROSS_INTAKE_MISMATCH" in case["expected_rule_ids"]
        assert case["expected_severity"] == "HIGH"
        assert case["requires_human_review"] is True

    elif scenario_id == "TC_SYNTH_007":
        # Duplicate document -> DUPLICATE_DETECTED
        assert case["expected_outcome"] == "DUPLICATE_DETECTED"
        assert "RULE_INTEGRITY_DUPLICATE_HASH" in case["expected_rule_ids"]
        assert case["expected_severity"] == "MEDIUM"

    elif scenario_id == "TC_SYNTH_008":
        # Low-confidence OCR -> NEEDS_HUMAN_REVIEW
        assert case["expected_outcome"] == "NEEDS_HUMAN_REVIEW"
        assert "RULE_OCR_CONFIDENCE_THRESHOLD" in case["expected_rule_ids"]
        assert case["requires_human_review"] is True

    elif scenario_id == "TC_SYNTH_009":
        # Malformed/unreadable -> EXTRACTION_ERROR
        assert case["expected_outcome"] == "EXTRACTION_ERROR"
        assert "RULE_FILE_PARSEABLE" in case["expected_rule_ids"]
        assert case["expected_severity"] == "CRITICAL"
        assert case["requires_human_review"] is True

    elif scenario_id == "TC_SYNTH_010":
        # Inconclusive evidence -> NEEDS_HUMAN_REVIEW
        assert case["expected_outcome"] == "NEEDS_HUMAN_REVIEW"
        assert "RULE_AMBIGUOUS_EVIDENCE" in case["expected_rule_ids"]
        assert case["requires_human_review"] is True

