/**
 * frontend/src/services/api.ts - Configurable HTTP client for FastAPI backend.
 */

import {
  CrossValidateResponse,
  DatasetManifestDocument,
  DocumentProcessResponse,
  SyntheticTestCase,
  SystemHealth,
} from '../types/api';
import { authStorage } from './auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

function getAuthHeaders(extraHeaders?: Record<string, string>): Record<string, string> {
  const token = authStorage.getToken();
  const headers: Record<string, string> = { ...(extraHeaders || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // fallback to statusText
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Check system health and capabilities */
  async getHealth(): Promise<SystemHealth> {
    const res = await fetch(`${API_BASE_URL}/health`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<SystemHealth>(res);
  },

  /** Upload and process a PDF document through the full verification pipeline */
  async uploadAndProcessDocument(
    file: File,
    options?: {
      documentId?: string;
      documentType?: string;
      enablePrivacyMasking?: boolean;
      ocrThreshold?: number;
    }
  ): Promise<DocumentProcessResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.documentId) formData.append('document_id', options.documentId);
    if (options?.documentType) formData.append('document_type', options.documentType);
    formData.append('enable_privacy_masking', String(options?.enablePrivacyMasking ?? true));
    formData.append('ocr_threshold', String(options?.ocrThreshold ?? 0.65));

    const res = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    });
    return handleResponse<DocumentProcessResponse>(res);
  },

  /** Run cross-document consistency verification */
  async crossValidateDocuments(documentIds?: string[]): Promise<CrossValidateResponse> {
    const res = await fetch(`${API_BASE_URL}/documents/cross-validate`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(documentIds ? { document_ids: documentIds } : {}),
    });
    return handleResponse<CrossValidateResponse>(res);
  },

  /** List cataloged dataset documents from data_manifest.csv */
  async getDatasetManifest(): Promise<{ total_documents: number; documents: DatasetManifestDocument[] }> {
    const res = await fetch(`${API_BASE_URL}/dataset/manifest`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<{ total_documents: number; documents: DatasetManifestDocument[] }>(res);
  },

  /** Run one-click verification on any sample document in real_documents or scanned_documents */
  async verifyDatasetSample(
    docId: string,
    options?: { enablePrivacyMasking?: boolean; ocrThreshold?: number }
  ): Promise<DocumentProcessResponse> {
    const params = new URLSearchParams();
    if (options?.enablePrivacyMasking !== undefined) {
      params.append('enable_privacy_masking', String(options.enablePrivacyMasking));
    }
    if (options?.ocrThreshold !== undefined) {
      params.append('ocr_threshold', String(options.ocrThreshold));
    }

    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/dataset/verify-sample/${encodeURIComponent(docId)}${query}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse<DocumentProcessResponse>(res);
  },

  /** List all 10 synthetic test scenarios */
  async getTestCases(): Promise<{ total_test_cases: number; test_cases: SyntheticTestCase[] }> {
    const res = await fetch(`${API_BASE_URL}/test-cases`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<{ total_test_cases: number; test_cases: SyntheticTestCase[] }>(res);
  },

  /** Execute a synthetic scenario against its JSON/binary fixture */
  async executeTestScenario(testId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/test-cases/execute/${encodeURIComponent(testId)}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse<any>(res);
  },
};
