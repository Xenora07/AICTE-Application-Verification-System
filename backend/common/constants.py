"""
backend/common/constants.py - Global constants and regulatory definitions for SIH26261.
"""

from pathlib import Path

# Paths
BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent

if (BACKEND_ROOT / "dataset").exists():
    DATASET_ROOT = BACKEND_ROOT / "dataset"
elif (REPO_ROOT / "dataset").exists():
    DATASET_ROOT = REPO_ROOT / "dataset"
else:
    DATASET_ROOT = REPO_ROOT / "dataset"
REAL_DOCS_DIR = DATASET_ROOT / "real_documents"
SCANNED_DOCS_DIR = DATASET_ROOT / "scanned_documents"
DATASET_MANIFEST_PATH = DATASET_ROOT / "data_manifest.csv"
TEST_MANIFEST_PATH = DATASET_ROOT / "test_cases" / "test_manifest.json"
FIXTURES_DIR = DATASET_ROOT / "test_cases" / "fixtures"

# Application Limits
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_FILE_EXTENSIONS = {".pdf"}
DEFAULT_OCR_THRESHOLD = 0.65

# Document Types
DOC_TYPE_AICTE_EOA = "aicte_eoa"
DOC_TYPE_AICTE_DISCLOSURE = "aicte_mandatory_disclosure"
DOC_TYPE_NAAC_CERT = "naac_certificate"
DOC_TYPE_NBA_ACCREDITATION = "nba_accreditation"

SUPPORTED_DOCUMENT_TYPES = [
    DOC_TYPE_AICTE_EOA,
    DOC_TYPE_AICTE_DISCLOSURE,
    DOC_TYPE_NAAC_CERT,
    DOC_TYPE_NBA_ACCREDITATION,
]

# Rule Severity
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_INFO = "INFO"

# Rule Outcomes
OUTCOME_PASS = "PASS"
OUTCOME_FAIL = "FAIL"
OUTCOME_INCONCLUSIVE = "INCONCLUSIVE"

# Finding Categories
CATEGORY_COMPLIANCE = "COMPLIANCE"
CATEGORY_AUTHENTICITY = "AUTHENTICITY"
CATEGORY_PRIVACY = "PRIVACY"
CATEGORY_CONSISTENCY = "CONSISTENCY"

# Overall Application Status
STATUS_VERIFIED = "VERIFIED"
STATUS_NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
STATUS_ACTION_REQUIRED = "ACTION_REQUIRED"
STATUS_REJECTED = "REJECTED"
