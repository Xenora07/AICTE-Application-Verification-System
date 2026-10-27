import React, { useState, useEffect } from 'react';
import { Search, Database, FileText, CheckCircle2, Play, Shield } from 'lucide-react';
import { DatasetManifestDocument } from '../types/api';

interface DatasetSampleSelectorProps {
  documents: DatasetManifestDocument[];
  onSelectSample: (docId: string) => void;
  isLoading: boolean;
  activeDocId?: string;
  isAuthenticated?: boolean;
  onRequireAuth?: (message?: string, docId?: string) => void;
}

const DOC_TYPE_DISPLAY_NAMES: Record<string, string> = {
  aicte_eoa: 'AICTE EoA',
  aicte_mandatory_disclosure: 'Mandatory Disclosure',
  naac_certificate: 'NAAC Certificate',
  nba_accreditation: 'NBA Accreditation',
};

const AUTH_REQUIRED_MESSAGE =
  'Auditor login required to run document verification and audit logging. Please sign in or register.';

export const formatDocTypeDisplay = (type?: string | null): string => {
  if (!type || type === 'unknown') return 'Unclassified';
  return DOC_TYPE_DISPLAY_NAMES[type] || type.replace(/_/g, ' ');
};

export const DatasetSampleSelector: React.FC<DatasetSampleSelectorProps> = ({
  documents,
  onSelectSample,
  isLoading,
  activeDocId,
  isAuthenticated = false,
  onRequireAuth,
}) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [authAlert, setAuthAlert] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      setAuthAlert(null);
    }
  }, [isAuthenticated]);

  const handleActionClick = (docId: string) => {
    if (!isAuthenticated) {
      setAuthAlert(AUTH_REQUIRED_MESSAGE);
      if (onRequireAuth) {
        onRequireAuth(AUTH_REQUIRED_MESSAGE, docId);
      }
      return;
    }
    onSelectSample(docId);
  };

  const filtered = documents.filter((doc) => {
    const matchesType = filterType === 'all' || doc.dataset_category === filterType;
    const matchesSearch =
      doc.file_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.doc_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.document_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.source_provenance.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesType && matchesSearch;
  });

  return (
    <div className="surface-card" style={{ padding: '20px', marginBottom: '20px' }}>
      {/* Informative Auth Required Alert */}
      {authAlert && (
        <div
          role="alert"
          className="auth-required-banner"
          style={{
            padding: '10px 14px',
            backgroundColor: 'var(--color-brand-light, #eff6ff)',
            border: '1px solid var(--color-brand-border, #bfdbfe)',
            borderRadius: '6px',
            color: 'var(--color-brand, #1e40af)',
            fontSize: '12px',
            marginBottom: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={16} style={{ flexShrink: 0, color: 'var(--color-brand, #2563eb)' }} />
            <span>{authAlert}</span>
          </div>
          <button
            type="button"
            onClick={() => setAuthAlert(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-brand, #1e40af)',
              cursor: 'pointer',
              fontSize: '14px',
              padding: '2px 6px',
            }}
            aria-label="Dismiss message"
          >
            ✕
          </button>
        </div>
      )}

      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '16px',
        paddingBottom: '14px',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '3px' }}>
            Sample Documents
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Try verification using the available sample documents
          </p>
        </div>

        {/* Filter controls */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={13} style={{ position: 'absolute', left: '9px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search sample documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                padding: '6px 10px 6px 28px',
                borderRadius: '6px',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                fontSize: '12.5px',
                width: '210px',
                color: 'var(--text-primary)',
              }}
            />
          </div>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{
              padding: '6px 10px',
              borderRadius: '6px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              fontSize: '12.5px',
              color: 'var(--text-primary)',
            }}
          >
            <option value="all">All Types ({documents.length})</option>
            <option value="real_documents">Digital PDFs</option>
            <option value="scanned_documents">Scanned & Hybrid</option>
          </select>
        </div>
      </div>

      {/* Dense Table of Sample Documents */}
      <div style={{ overflowX: 'auto', maxHeight: '480px', overflowY: 'auto' }}>
        <table className="ledger-table">
          <thead>
            <tr>
              <th>Doc ID</th>
              <th>File Name</th>
              <th>Type</th>
              <th>Document Type</th>
              <th>Pages</th>
              <th>Size</th>
              <th>Source</th>
              <th style={{ textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '36px 20px', textAlign: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)' }}>
                    No sample documents match your search
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Try searching by document ID, filename, or selecting another type.
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map((doc) => {
                const isActive = activeDocId === doc.doc_id;
                return (
                  <tr
                    key={doc.doc_id}
                    className={isActive ? 'active-row' : ''}
                  >
                    <td>
                      <span className="code-mono" style={{ fontWeight: '600', color: 'var(--color-brand)' }}>
                        {doc.doc_id}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: '500', color: 'var(--text-primary)' }}>
                        {doc.file_name}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${doc.dataset_category === 'real_documents' ? 'badge-cat-compliance' : 'badge-cat-authenticity'} badge-pill`} style={{ fontSize: '10.5px' }}>
                        {doc.dataset_category === 'real_documents' ? 'Digital' : 'Scanned/OCR'}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', fontWeight: '500', color: 'var(--text-secondary)' }} title={doc.document_type}>
                        {formatDocTypeDisplay(doc.document_type)}
                      </span>
                    </td>
                    <td>{doc.page_count}</td>
                    <td>{(Number(doc.file_size_bytes) / 1024).toFixed(0)} KB</td>
                    <td>
                      <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                        {doc.source_provenance || 'Regulatory Filing'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                        <button
                          onClick={() => handleActionClick(doc.doc_id)}
                          disabled={isLoading}
                          className={`btn ${isActive ? 'btn-brand' : 'btn-secondary'} btn-sm`}
                          style={{ padding: '3px 10px', fontSize: '11.5px' }}
                          title={!isAuthenticated ? 'Sign in to verify' : 'Verify Sample'}
                          aria-label={!isAuthenticated ? `Verify Sample ${doc.doc_id} (Sign in to verify)` : `Verify Sample ${doc.doc_id}`}
                        >
                          <Play size={11} />
                          <span>{isLoading && isActive ? 'Verifying...' : 'Verify Sample'}</span>
                        </button>
                        {!isAuthenticated && (
                          <span
                            className="guest-verify-hint"
                            style={{ fontSize: '10px', color: 'var(--text-muted)', lineHeight: '1.2' }}
                          >
                            Sign in to verify
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
