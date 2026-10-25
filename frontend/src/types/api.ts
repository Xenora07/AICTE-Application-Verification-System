/**
 * frontend/src/types/api.ts - TypeScript Data Contracts aligned with backend Pydantic models.
 */

export type RuleOutcome = 'PASS' | 'FAIL' | 'INCONCLUSIVE';
export type RuleSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type FindingCategory = 'COMPLIANCE' | 'AUTHENTICITY' | 'PRIVACY' | 'CONSISTENCY';
export type OverallStatus = 'VERIFIED' | 'NEEDS_HUMAN_REVIEW' | 'ACTION_REQUIRED' | 'REJECTED';

export type AdjudicationDecision = 'CONFIRMED_VALID' | 'REJECTED_NON_COMPLIANT' | 'REQUEST_CLARIFICATION';

export interface AdjudicationRecord {
  findingId: string;
  ruleId: string;
  ruleName: string;
  decision: AdjudicationDecision;
  notes: string;
  timestamp: string;
}

export interface FieldEvidence {
  raw_value: string | null;
  normalized_value: any;
  page_number: number | null;
  bounding_box: [number, number, number, number] | null; // [x0, y0, x1, y1] PDF points
  confidence: number | null; // null for digital text, [0.0 - 1.0] for OCR
  extraction_method: 'digital' | 'ocr' | 'hybrid' | null;
  is_uncertain: boolean;
  uncertainty_reason: string | null;
}

export interface TableData {
  table_name: string;
  page_number: number;
  headers: string[];
  rows: Record<string, any>[];
}

export interface ProcessingMetadata {
  total_pages: number;
  processed_pages: number;
  page_range?: string | null;
  extraction_path: 'digital' | 'ocr' | 'hybrid';
  digital_pages: number[];
  ocr_pages: number[];
  timestamp_utc: string;
  ocr_backend?: string | null;
}

export interface ValidationFinding {
  rule_id: string;
  rule_name: string;
  outcome: RuleOutcome;
  severity: RuleSeverity;
  explanation: string;
  affected_document_ids: string[];
  affected_fields: string[];
  evidence_values: Record<string, any>;
  requires_human_review: boolean;
  timestamp_utc: string;
}

export interface DocumentValidationReport {
  document_id: string;
  document_type: string;
  overall_outcome: RuleOutcome;
  findings: ValidationFinding[];
  summary: Record<string, number>;
  requires_human_review: boolean;
}

export interface CrossDocumentConsistencyReport {
  overall_outcome: RuleOutcome;
  findings: ValidationFinding[];
  evaluated_documents: string[];
  summary: Record<string, number>;
  requires_human_review: boolean;
}

export interface NormalizedFinding {
  finding_id: string;
  category: FindingCategory;
  rule_id: string;
  rule_name: string;
  outcome: RuleOutcome;
  severity: RuleSeverity;
  explanation: string;
  affected_document_ids: string[];
  affected_fields: string[];
  evidence_values: Record<string, any>;
  requires_human_review: boolean;
  timestamp_utc: string;
}

export interface ReviewerSummary {
  total_rules_evaluated: number;
  passed_rules: number;
  failed_rules: number;
  inconclusive_rules: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  info_findings: number;
  authenticity_signals_count: number;
  privacy_redactions_count: number;
  overall_status: OverallStatus;
  requires_human_review: boolean;
}

export interface DocumentProcessResponse {
  success: boolean;
  document_id: string;
  filename: string;
  file_size_bytes: number;
  sha256: string;
  document_type: string;
  processing_status: string;
  processing_metadata: ProcessingMetadata;
  extracted_fields: Record<string, FieldEvidence>;
  table_data: TableData[];
  validation_report: DocumentValidationReport;
  normalized_findings: NormalizedFinding[];
  reviewer_summary: ReviewerSummary;
  warnings: string[];
  errors: string[];
}

export interface CrossValidateResponse {
  success: boolean;
  consistency_report: CrossDocumentConsistencyReport;
  normalized_findings: NormalizedFinding[];
  overall_status: string;
  requires_human_review: boolean;
}

export interface DatasetManifestDocument {
  doc_id: string;
  relative_path: string;
  file_name: string;
  dataset_category: string;
  file_type: string;
  file_size_bytes: string | number;
  page_count: string | number;
  has_embedded_text: string | boolean;
  ocr_required: string;
  sha256_checksum: string;
  processing_status: string;
  document_type: string;
  source_provenance: string;
  notes: string;
}

export interface SyntheticTestCase {
  test_id: string;
  scenario_name: string;
  description: string;
  purpose: string;
  document_type: string;
  is_synthetic: boolean;
  expected_outcome: string;
  expected_findings: string[];
  expected_rule_ids: string[];
  expected_severity: string;
  requires_human_review: boolean;
}

export interface SystemHealth {
  status: string;
  service: string;
  version: string;
  ocr_engine: string;
  dataset_documents_available: number;
  synthetic_test_cases_available: number;
  active_documents_in_session: number;
}
