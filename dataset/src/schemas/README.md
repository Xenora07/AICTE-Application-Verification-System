# Document Extraction Output Schema Contract

This directory defines the stable Pydantic v2 data contract emitted by the extraction pipeline and consumed by downstream SIH26261 modules:
- **Validation Engine** (rule checks, pattern validation)
- **Cross-Document Consistency Engine** (intake quota comparison, ID matching)
- **Privacy Gateway** (PII redaction and masking)
- **Document Authenticity Service** (hash verification and tamper checks)
- **Dashboard / API Gateway** (structured JSON responses)

---

## 1. Schema Hierarchy

```
ExtractionResult
├── document_id: str                      # Stable identifier (e.g. "DOC_REAL_003")
├── source_file: str                      # POSIX relative path ("real_documents/...")
├── sha256: Optional[str]                 # 64-character lowercase SHA-256 hex string
├── document_type: str                    # e.g. "aicte_eoa", "naac_certificate"
├── classification_confidence: float|null # None for deterministic extraction; [0.0 - 1.0] if probabilistic
├── processing_status: str                # SUCCESS | SUCCESS_WITH_WARNINGS | SUCCESS_WITH_UNCERTAINTY | NEEDS_HUMAN_REVIEW | EXTRACTION_ERROR
├── processing_metadata: ProcessingMetadata
│   ├── total_pages: int (>= 0)
│   ├── processed_pages: int (>= 0)
│   ├── page_range: Optional[str]         # e.g. "1-5" or null for all pages
│   ├── extraction_path: str              # "digital" | "ocr" | "hybrid"
│   ├── digital_pages: List[int]          # 1-indexed page numbers extracted digitally
│   ├── ocr_pages: List[int]              # 1-indexed page numbers processed via OCR
│   ├── timestamp_utc: str                # ISO 8601 UTC timestamp
│   └── ocr_backend: Optional[str]        # e.g. "easyocr", "paddleocr", "synthetic_test_engine"
├── fields: Dict[str, FieldEvidence]
│   └── <field_name>:
│       ├── raw_value: Optional[str]      # Exact raw substring from page
│       ├── normalized_value: Any         # Coerced value (ISO date, int, float, string)
│       ├── page_number: Optional[int]    # 1-indexed page number (>= 1)
│       ├── bounding_box: List[float]|null# [x0, y0, x1, y1] in PDF points (top-left origin)
│       ├── confidence: Optional[float]   # None for digital text; [0.0 - 1.0] for OCR
│       ├── extraction_method: str|null   # "digital" | "ocr" | "hybrid"
│       ├── is_uncertain: bool            # True if flagged for ambiguity or low score
│       └── uncertainty_reason: str|null  # Explanatory reason if uncertain
├── table_data: List[TableData]
│   └── <table>:
│       ├── table_name: str
│       ├── page_number: int (>= 1)
│       ├── headers: List[str]
│       └── rows: List[Dict[str, Any]]
├── warnings: List[str]                   # Non-blocking warnings (partial results preserved)
└── errors: List[str]                     # Fatal or blocking errors
```

---

## 2. Coordinate System Convention

All bounding boxes adhere to standard PDF typographic points (1/72 inch):
- **Origin `(0, 0)`:** Top-left corner of the page.
- **`x0`:** Horizontal distance from left page edge to left boundary of element.
- **`y0`:** Vertical distance from top page edge to top boundary of element.
- **`x1`:** Horizontal distance from left page edge to right boundary of element.
- **`y1`:** Vertical distance from top page edge to bottom boundary of element.
- **Invariants:** `0 <= x0 <= x1` and `0 <= y0 <= y1`.

---

## 3. Honest Confidence Policy

To prevent hallucinations and false certainty:
1. **Deterministic Digital Text Extraction:** `confidence` is ALWAYS `null` (`None`). Do not invent or assign arbitrary 1.0 scores.
2. **Rule-Based Classification:** `classification_confidence` is ALWAYS `null` (`None`).
3. **OCR Engine Output:** Preserved directly from engine scores within `[0.0, 1.0]`. If below threshold (default `< 0.65`), the field sets `is_uncertain=True` and populates `uncertainty_reason`.

---

## 4. Usage Example

```python
from src.schemas import ExtractionResult

# Deserialize from downstream API or disk
result = ExtractionResult.model_validate_json(raw_json_str)

# Inspect field evidence
app_id_evidence = result.fields.get("application_id")
if app_id_evidence:
    print(f"Value: {app_id_evidence.normalized_value}")
    print(f"Page: {app_id_evidence.page_number}, BBox: {app_id_evidence.bounding_box}")
    print(f"Confidence: {app_id_evidence.confidence}") # None for digital

# Serialize cleanly
clean_json = result.to_json(indent=2)
```
