import React, { useRef, useState } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, X } from 'lucide-react';

interface UploadSectionProps {
  onUpload: (
    file: File,
    options: {
      documentId?: string;
      documentType?: string;
      enablePrivacyMasking: boolean;
      ocrThreshold: number;
    }
  ) => void;
  isLoading: boolean;
  uploadError: string | null;
  isModal?: boolean;
  onCloseModal?: () => void;
}

export const UploadSection: React.FC<UploadSectionProps> = ({
  onUpload,
  isLoading,
  uploadError,
  isModal = false,
  onCloseModal,
}) => {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentId, setDocumentId] = useState('');
  const [documentType, setDocumentType] = useState('');
  const [enablePrivacyMasking, setEnablePrivacyMasking] = useState(true);
  const [ocrThreshold, setOcrThreshold] = useState(0.65);
  const [clientError, setClientError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setClientError(null);
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setClientError('Invalid file format. Only PDF documents (.pdf) are accepted.');
      setSelectedFile(null);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setClientError('File exceeds 50 MB maximum allowed limit.');
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setClientError('Please select a PDF document to verify.');
      return;
    }
    onUpload(selectedFile, {
      documentId: documentId.trim() || undefined,
      documentType: documentType || undefined,
      enablePrivacyMasking,
      ocrThreshold,
    });
    if (isModal && onCloseModal) {
      onCloseModal();
    }
  };

  const content = (
    <div className="surface-card" style={{ padding: '24px', position: 'relative' }}>
      {isModal && onCloseModal && (
        <button
          onClick={onCloseModal}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          <X size={18} />
        </button>
      )}

      <div style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
          Upload Regulatory Document
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Supports AICTE EoA, Mandatory Disclosure, NAAC, NBA (.pdf)
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Drag and Drop Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
              handleFile(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? 'var(--color-brand)' : selectedFile ? '#16a34a' : 'var(--border-color)'}`,
            borderRadius: '8px',
            padding: '30px 20px',
            textAlign: 'center',
            backgroundColor: dragOver ? 'var(--color-brand-light)' : selectedFile ? '#f0fdf4' : 'var(--bg-surface-subtle)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            marginBottom: '16px',
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFile(e.target.files[0]);
              }
            }}
          />

          <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'center' }}>
            {selectedFile ? (
              <CheckCircle2 size={32} style={{ color: '#16a34a' }} />
            ) : (
              <Upload size={32} style={{ color: 'var(--text-muted)' }} />
            )}
          </div>

          {selectedFile ? (
            <div>
              <div style={{ fontSize: '14px', fontWeight: '600', color: '#15803d' }}>
                {selectedFile.name}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                {(selectedFile.size / 1024).toFixed(1)} KB — Ready for regulatory extraction
              </div>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: '13.5px', fontWeight: '600', color: 'var(--text-primary)' }}>
                Drag and drop institutional approval letter or mandatory disclosure PDF
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>
                or click to browse your filesystem (Max 50MB)
              </div>
            </div>
          )}
        </div>

        {/* Options Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: 'var(--text-secondary)', marginBottom: '5px' }}>
              Custom Document ID (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. DOC_REAL_001"
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
              style={{
                width: '100%',
                padding: '7px 10px',
                borderRadius: '6px',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                fontSize: '13px',
                color: 'var(--text-primary)',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: 'var(--text-secondary)', marginBottom: '5px' }}>
              Document Type Hint
            </label>
            <select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              style={{
                width: '100%',
                padding: '7px 10px',
                borderRadius: '6px',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                fontSize: '13px',
                color: 'var(--text-primary)',
              }}
            >
              <option value="">Auto-Detect from Content</option>
              <option value="aicte_eoa">AICTE Extension of Approval (EoA)</option>
              <option value="aicte_mandatory_disclosure">AICTE Mandatory Disclosure</option>
              <option value="naac_certificate">NAAC Accreditation Certificate</option>
              <option value="nba_accreditation">NBA Accreditation Letter</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', cursor: 'pointer', color: 'var(--text-primary)' }}>
              <input
                type="checkbox"
                checked={enablePrivacyMasking}
                onChange={(e) => setEnablePrivacyMasking(e.target.checked)}
                style={{ width: '15px', height: '15px', accentColor: 'var(--color-brand)' }}
              />
              <span>Enable Privacy Gateway (PII Masking)</span>
            </label>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '23px', marginTop: '1px' }}>
              Redacts personal phone numbers, emails, and IDs
            </span>
          </div>
        </div>

        {/* Error Alert */}
        {(clientError || uploadError) && (
          <div style={{
            padding: '10px 14px',
            backgroundColor: 'var(--color-fail-bg)',
            border: '1px solid var(--color-fail-border)',
            borderRadius: '6px',
            color: 'var(--color-fail-text)',
            fontSize: '12px',
            marginBottom: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <AlertCircle size={16} />
            <span>{clientError || uploadError}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          {selectedFile && (
            <button
              type="button"
              onClick={() => { setSelectedFile(null); setClientError(null); }}
              className="btn btn-secondary"
              disabled={isLoading}
            >
              Clear
            </button>
          )}
          <button
            type="submit"
            className="btn btn-brand"
            disabled={isLoading || !selectedFile}
            style={{ minWidth: '180px' }}
          >
            {isLoading ? 'Verifying Pipeline...' : 'Start Document Verification'}
          </button>
        </div>
      </form>
    </div>
  );

  if (isModal) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(28, 25, 23, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: '20px',
        backdropFilter: 'blur(2px)',
      }}>
        <div style={{ maxWidth: '640px', width: '100%' }}>
          {content}
        </div>
      </div>
    );
  }

  return content;
};
