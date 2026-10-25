"""
src/mappers/base_mapper.py - Abstract protocol and utilities for deterministic field mapping.
Separates raw extracted text from normalized values and preserves coordinate/page provenance.
Maintains honest ambiguity handling when multiple conflicting candidate values are discovered.
"""

from abc import ABC, abstractmethod
import re
from typing import Any, Callable, Dict, List, Optional
from src.extractors.base import DocumentContent, ExtractedBlock, PageExtraction
from src.schemas.common import FieldEvidence, TableData


class BaseMapper(ABC):
    """Base class for document-specific deterministic field mapping."""

    document_type: str = "generic"

    @abstractmethod
    def map_fields(self, content: DocumentContent) -> Dict[str, FieldEvidence]:
        """Extract canonical document fields from raw extraction content."""
        pass

    def extract_tables(self, content: DocumentContent) -> List[TableData]:
        """Extract structured tabular data if present in the document."""
        return []

    @staticmethod
    def _is_reliable_digital_block(
        block: ExtractedBlock,
        raw_val: str,
        match_text: str,
    ) -> bool:
        """
        Check if a digital extraction block reliably bounds the specific field.
        Returns False if the block is a composite container (e.g. running header/footer,
        multi-cell table row, or large multi-sentence paragraph), to avoid attaching
        misleading coarse bounding boxes or fabricating coordinates.
        """
        if block.is_ocr:
            return True

        text = block.text.strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 1. Reject running headers/footers with pagination or system disclaimers
        footer_markers = [
            r"page\s+\d+\s+of\s+\d+",
            r"computer\s+generated",
            r"printed\s+by",
            r"letter\s+printed\s+on",
            r"no\s+signature\s+is\s+required",
        ]
        for marker in footer_markers:
            if re.search(marker, text, re.IGNORECASE):
                return False

        # 2. Reject multi-field blocks (e.g. table rows combining disparate fields)
        field_markers = [
            r"permanent\s*(?:institute\s*)?id",
            r"application\s*(?:id|no)",
            r"name\s+of\s+the\s+institution",
            r"name\s+of\s+the\s+society",
            r"all\s+india\s+council",
        ]
        matching_markers = sum(1 for m in field_markers if re.search(m, text, re.IGNORECASE))
        if matching_markers >= 2:
            return False

        # 3. Reject large multi-line paragraphs where match is only a minor fragment
        if len(lines) > 3 and len(match_text) < len(text) * 0.4:
            return False

        return True

    @classmethod
    def search_pattern_with_evidence(
        cls,
        content: DocumentContent,
        pattern: re.Pattern,
        normalizer: Optional[Callable[[str], Any]] = None,
        check_conflicts: bool = True,
    ) -> Optional[FieldEvidence]:
        """
        Search for regex pattern across all pages in document content.
        - First searches block-by-block to preserve precise bounding boxes.
        - Falls back to full-page text search if matching pattern spans blocks.
        - Attaches bounding box only when it reliably identifies the source text for that field.
        - Detects conflicting candidates across pages and flags is_uncertain=True.
        - Flags uncertainty when OCR character substitution (e.g. 'O' -> '0') is applied.
        """
        candidates: List[FieldEvidence] = []

        for page in content.pages:
            method_str = "ocr" if page.method == "ocr" else "digital"

            # 1. Block-by-block search for precise bounding boxes
            matched_on_blocks = False
            for block in page.blocks:
                match = pattern.search(block.text)
                if match:
                    matched_on_blocks = True
                    raw_val = match.group(1) if match.groups() else match.group(0)
                    raw_val = raw_val.strip()
                    norm_val = normalizer(raw_val) if normalizer else raw_val

                    is_ocr = block.is_ocr or page.method == "ocr"
                    conf = block.confidence if is_ocr else None

                    is_uncertain = False
                    reasons: List[str] = []
                    if conf is not None and conf < 0.65:
                        is_uncertain = True
                        reasons.append(f"OCR confidence ({conf:.2f}) is below 0.65 threshold")

                    # Check for OCR character substitutions in numeric fields (e.g. 'O' -> '0')
                    if isinstance(norm_val, (int, float)) and re.search(r"[OoBb]", raw_val):
                        is_uncertain = True
                        reasons.append(f"OCR character substitution applied to raw value '{raw_val}'")

                    # Check for numeric out-of-range bounds (e.g. CGPA > 10.0 or < 0.0)
                    if isinstance(norm_val, (int, float)) and (norm_val < 0.0 or norm_val > 10.0):
                        is_uncertain = True
                        reasons.append(f"Value {norm_val} outside expected range [0.0 - 10.0]")

                    # Check for address/postal code pollution in institution name
                    if isinstance(norm_val, str) and re.search(r"\b\d{6}\b", raw_val):
                        is_uncertain = True
                        reasons.append(f"Field contains potential address/postal code text in '{raw_val}'")

                    reason_str = "; ".join(reasons) if reasons else None

                    # Determine if block provides a reliable bounding box
                    reliable_box = (
                        block.bounding_box
                        if cls._is_reliable_digital_block(block, raw_val, match.group(0))
                        else None
                    )

                    candidate = FieldEvidence(
                        raw_value=raw_val,
                        normalized_value=norm_val,
                        page_number=page.page_number,
                        bounding_box=reliable_box,
                        confidence=conf,
                        extraction_method="ocr" if is_ocr else "digital",
                        is_uncertain=is_uncertain,
                        uncertainty_reason=reason_str,
                    )
                    candidates.append(candidate)

            # 2. Page-level search fallback if no blocks on this page matched
            if not matched_on_blocks:
                match = pattern.search(page.text)
                if match:
                    raw_val = match.group(1) if match.groups() else match.group(0)
                    raw_val = raw_val.strip()
                    norm_val = normalizer(raw_val) if normalizer else raw_val

                    # Try to link bounding box to an existing block on the page containing raw_val
                    linked_box = None
                    linked_conf = None
                    is_ocr = page.method == "ocr"

                    matching_blocks = [b for b in page.blocks if raw_val in b.text]
                    if len(matching_blocks) == 1:
                        target_b = matching_blocks[0]
                        if cls._is_reliable_digital_block(target_b, raw_val, raw_val):
                            linked_box = target_b.bounding_box
                        if is_ocr:
                            linked_conf = target_b.confidence

                    is_uncertain = False
                    reasons = []
                    if linked_conf is not None and linked_conf < 0.65:
                        is_uncertain = True
                        reasons.append(f"OCR confidence ({linked_conf:.2f}) is below 0.65 threshold")

                    if isinstance(norm_val, (int, float)) and re.search(r"[OoBb]", raw_val):
                        is_uncertain = True
                        reasons.append(f"OCR character substitution applied to raw value '{raw_val}'")

                    if isinstance(norm_val, (int, float)) and (norm_val < 0.0 or norm_val > 10.0):
                        is_uncertain = True
                        reasons.append(f"Value {norm_val} outside expected range [0.0 - 10.0]")

                    if isinstance(norm_val, str) and re.search(r"\b\d{6}\b", raw_val):
                        is_uncertain = True
                        reasons.append(f"Field contains potential address/postal code text in '{raw_val}'")

                    reason_str = "; ".join(reasons) if reasons else None

                    candidate = FieldEvidence(
                        raw_value=raw_val,
                        normalized_value=norm_val,
                        page_number=page.page_number,
                        bounding_box=linked_box,
                        confidence=linked_conf if is_ocr else None,
                        extraction_method=method_str,
                        is_uncertain=is_uncertain,
                        uncertainty_reason=reason_str,
                    )
                    candidates.append(candidate)

        if not candidates:
            return None

        # Check for ambiguity / conflicting candidate values
        if check_conflicts and len(candidates) > 1:
            distinct_norm_values = {
                str(c.normalized_value).strip().lower()
                for c in candidates
                if c.normalized_value is not None
            }
            if len(distinct_norm_values) > 1:
                # Ambiguity detected: conflicting candidates found across pages/blocks
                primary = candidates[0].model_copy()
                conflict_summary = ", ".join(
                    f"'{c.raw_value}' (p. {c.page_number})" for c in candidates[:3]
                )
                primary.is_uncertain = True
                primary.uncertainty_reason = (
                    f"Conflicting candidates detected: [{conflict_summary}]"
                )
                return primary

        # If candidates agree on normalized value, prefer candidate with a reliable bounding box
        candidates_with_box = [c for c in candidates if c.bounding_box is not None]
        if candidates_with_box:
            return candidates_with_box[0]

        return candidates[0]
