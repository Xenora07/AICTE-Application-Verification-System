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

const formatFileSize = (bytes?: number): string => {
  if (!bytes || bytes <= 0) return '0 KB';
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
};

export const UploadSection: React.FC<UploadSectionProps> = ({
  onUpload,
  isLoading,
  uploadError,
  isModal = false,
  onCloseModal,
}) => {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
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
      setPreviewUrl(null);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setClientError('File exceeds 50 MB maximum allowed limit.');
      setSelectedFile(null);
      setPreviewUrl(null);
      return;
    }
    setSelectedFile(file);
    try {
      setPreviewUrl(URL.createObjectURL(file));
    } catch {
      setPreviewUrl(null);
    }
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

  const isDocumentIdValid = !documentId.trim() || /^[a-zA-Z0-9_\-\. ]{2,64}$/.test(documentId.trim());
  const canSubmit = Boolean(selectedFile) && !clientError && isDocumentIdValid && !isLoading;

  const content = (
    <div className="surface-card" style={{ padding: '22px', position: 'relative' }}>
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

      <div style={{ marginBottom: '14px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '3px' }}>
          Upload Regulatory Document
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Supports AICTE Extension of Approval (EoA), Mandatory Disclosure, NAAC, and NBA (.pdf)
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Compact Drag and Drop Zone */}
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
            border: `2px dashed ${dragOver ? 'var(--color-brand)' : selectedFile ? 'var(--color-pass-border)' : 'var(--border-color)'}`,
            borderRadius: '6px',
            padding: '18px 16px',
            textAlign: 'center',
            backgroundColor: dragOver ? 'var(--color-brand-light)' : selectedFile ? 'var(--color-pass-bg)' : 'var(--bg-surface-subtle)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            marginBottom: '14px',
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

          <div style={{ marginBottom: '6px', display: 'flex', justifyContent: 'center' }}>
            {selectedFile ? (
              <CheckCircle2 size={24} style={{ color: 'var(--color-pass-text)' }} />
            ) : (
              <Upload size={24} style={{ color: 'var(--color-brand)' }} />
            )}
          </div>

          {selectedFile ? (
            <div>
              <div style={{ fontSize: '13.5px', fontWeight: '600', color: 'var(--color-pass-text)' }}>
                {selectedFile.name}
              </div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                {formatFileSize(selectedFile.size)} — Ready for regulatory verification
              </div>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                Drag and drop institutional approval letter or disclosure PDF
              </div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                or click to select file from system (Max 50MB • PDF format)
              </div>
            </div>
          )}
        </div>

        {/* Live Document Preview on Initial Upload Screen */}
        {selectedFile && previewUrl && (
          <div style={{
            marginBottom: '14px',
            borderRadius: '6px',
            overflow: 'hidden',
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-surface)',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 12px',
              backgroundColor: 'var(--bg-surface-subtle)',
              borderBottom: '1px solid var(--border-subtle)',
              fontSize: '11px',
              fontWeight: '600',
              color: 'var(--text-secondary)',
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FileText size={13} style={{ color: 'var(--color-brand)' }} />
                Document Preview (Page 1)
              </span>
              <span className="code-mono" style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>
                {formatFileSize(selectedFile.size)}
              </span>
            </div>
            <div style={{ height: '220px', width: '100%' }}>
              <iframe
                src={`${previewUrl}#page=1&toolbar=0&navpanes=0`}
                title="Initial Document Stream Preview"
                style={{ width: '100%', height: '100%', border: 'none' }}
              />
            </div>
          </div>
        )}

        {/* Options Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '11.5px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '4px' }}>
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
                border: `1px solid ${!isDocumentIdValid ? 'var(--color-fail-border)' : 'var(--border-color)'}`,
                fontSize: '12.5px',
                color: 'var(--text-primary)',
              }}
            />
            {!isDocumentIdValid && (
              <span style={{ fontSize: '10.5px', color: 'var(--color-fail-text)', marginTop: '2px', display: 'block' }}>
                Must be 2–64 alphanumeric characters
              </span>
            )}
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '11.5px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '4px' }}>
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
                fontSize: '12.5px',
                color: 'var(--text-primary)',
                cursor: 'pointer',
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
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', cursor: 'pointer', color: 'var(--text-primary)' }}>
              <input
                type="checkbox"
                checked={enablePrivacyMasking}
                onChange={(e) => setEnablePrivacyMasking(e.target.checked)}
                style={{ width: '15px', height: '15px', accentColor: 'var(--color-brand)' }}
              />
              <span style={{ fontWeight: '500' }}>Enable Privacy Gateway</span>
            </label>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '23px', marginTop: '1px' }}>
              Automated PII masking (phone, email, identity)
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

        {/* Action Buttons & Guidance */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
          <div style={{ fontSize: '11.5px', color: selectedFile ? 'var(--color-pass-text)' : 'var(--text-muted)' }}>
            {selectedFile ? '✓ Document ready to verify' : 'Select a PDF document above to enable verification'}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            {selectedFile && (
              <button
                type="button"
                onClick={() => { setSelectedFile(null); setPreviewUrl(null); setClientError(null); }}
                className="btn btn-secondary btn-sm"
                disabled={isLoading}
              >
                Clear
              </button>
            )}
            <button
              type="submit"
              className="btn btn-brand"
              disabled={!canSubmit}
              style={{ minWidth: '190px' }}
            >
              {isLoading ? 'Verifying Pipeline...' : 'Start Document Verification'}
            </button>
          </div>
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
