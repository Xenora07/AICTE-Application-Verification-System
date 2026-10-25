import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, FileText, Info, XCircle, FileUp } from 'lucide-react';
import { ReviewerSummary } from '../types/api';

interface ReviewerSummaryBannerProps {
  summary: ReviewerSummary;
  documentId: string;
  documentType: string;
  filename: string;
  sha256: string;
  processingStatus: string;
  totalPages?: number;
  fileSizeBytes?: number;
  uploadedAt?: string;
  institutionName?: string | null;
  applicationId?: string | null;
  academicYear?: string | null;
  onOpenAdjudication: () => void;
  onNewVerification?: () => void;
}

export const ReviewerSummaryBanner: React.FC<ReviewerSummaryBannerProps> = ({
  summary,
  documentId,
  documentType,
  filename,
  sha256,
  processingStatus,
  totalPages,
  fileSizeBytes,
  uploadedAt,
  institutionName,
  applicationId,
  academicYear,
  onOpenAdjudication,
  onNewVerification,
}) => {
  const [showMetadataModal, setShowMetadataModal] = useState(false);

  const formattedSize = fileSizeBytes && fileSizeBytes > 0
    ? fileSizeBytes >= 1024 * 1024
      ? `${(fileSizeBytes / (1024 * 1024)).toFixed(2)} MB`
      : `${(fileSizeBytes / 1024).toFixed(1)} KB`
    : 'Size unavailable';

  const formattedPages = totalPages !== undefined && totalPages > 0
    ? `${totalPages} ${totalPages === 1 ? 'page' : 'pages'}`
    : 'Page count unavailable';

  const formattedDate = uploadedAt
    ? new Date(uploadedAt).toLocaleString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Time unavailable';

  const getStatusBadgeConfig = () => {
    const isUnclassified = !documentType || documentType === 'unknown' || summary.total_rules_evaluated === 0;
    const isFailed = summary.failed_rules > 0 || processingStatus === 'ACTION_REQUIRED' || processingStatus === 'REJECTED' || summary.overall_status === 'REJECTED';
    const isNeedsReview = summary.requires_human_review || summary.inconclusive_rules > 0 || processingStatus.includes('WARNING') || processingStatus === 'NEEDS_HUMAN_REVIEW';

    if (isUnclassified) {
      return {
        icon: <Info size={20} style={{ color: 'var(--color-amber-accent)' }} />,
        title: 'UNCLASSIFIED / NO EXTRACTED FIELDS',
        subtitle: 'Document type unrecognized or no fields mapped',
        bg: 'var(--bg-surface-subtle)',
        border: 'var(--border-color)',
        textColor: 'var(--text-secondary)',
      };
    }

    if (isFailed) {
      return {
        icon: <XCircle size={20} style={{ color: '#ef4444' }} />,
        title: 'NON-COMPLIANT',
        subtitle: `${summary.failed_rules} critical regulatory discrepancy detected`,
        bg: 'var(--color-fail-bg)',
        border: 'var(--color-fail-border)',
        textColor: 'var(--color-fail-text)',
      };
    }

    if (isNeedsReview) {
      return {
        icon: <AlertTriangle size={20} style={{ color: '#d97706' }} />,
        title: 'HUMAN REVIEW REQUIRED',
        subtitle: `${summary.inconclusive_rules} finding(s) require regulatory adjudication`,
        bg: 'var(--color-inconclusive-bg)',
        border: 'var(--color-inconclusive-border)',
        textColor: 'var(--color-inconclusive-text)',
      };
    }

    return {
      icon: <CheckCircle2 size={20} style={{ color: '#16a34a' }} />,
      title: 'COMPLIANT',
      subtitle: 'Deterministic compliance verified',
      bg: 'var(--color-pass-bg)',
      border: 'var(--color-pass-border)',
      textColor: 'var(--color-pass-text)',
    };
  };

  const statusConfig = getStatusBadgeConfig();

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 340px',
      gap: '14px',
      marginBottom: '16px',
    }}>
      {/* Left: Current Document Metadata Box */}
      <div className="surface-card" style={{ padding: '14px 18px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
          {/* Red PDF Icon Badge */}
          <div style={{
            width: '42px',
            height: '52px',
            backgroundColor: '#ef4444',
            borderRadius: '5px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff',
            fontWeight: '800',
            fontSize: '11px',
            boxShadow: '0 2px 4px rgba(239, 68, 68, 0.25)',
            flexShrink: 0,
            marginTop: '2px',
          }}>
            <FileText size={18} />
            <span style={{ fontSize: '9px', marginTop: '1px', letterSpacing: '0.05em' }}>PDF</span>
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: 'var(--text-muted)',
                }}>
                  CURRENT DOCUMENT
                </span>
                <span style={{
                  fontSize: '10px',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  backgroundColor: 'var(--bg-surface-subtle)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-secondary)',
                  fontWeight: '600',
                }}>
                  ✓ Processed
                </span>
                {(documentId?.startsWith('TC_SYNTH') || filename?.toLowerCase().includes('synth')) && (
                  <span className="badge badge-pill badge-cat-authenticity" style={{ fontSize: '10px' }}>
                    Synthetic Scenario
                  </span>
                )}
              </div>

              {onNewVerification && (
                <button
                  type="button"
                  onClick={onNewVerification}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '11px', padding: '3px 9px' }}
                  title="Clear active document and upload or select another document"
                >
                  <FileUp size={12} />
                  <span>Verify Another Document</span>
                </button>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', flexWrap: 'wrap' }}>
              <h2 style={{
                fontSize: '18px',
                fontWeight: '700',
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
                {filename || 'Unnamed Document'}
              </h2>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              marginTop: '4px',
            }}>
              <span>Doc ID: <strong className="code-mono" style={{ color: 'var(--text-primary)' }}>{documentId || 'Not available'}</strong></span>
              <span style={{ color: 'var(--border-color)' }}>|</span>
              <span>Type: <strong className="code-mono" style={{ color: 'var(--text-primary)' }}>{!documentType || documentType === 'unknown' ? 'Unclassified' : documentType}</strong></span>
              <span style={{ color: 'var(--border-color)' }}>|</span>
              <span>SHA-256: <strong className="code-mono" style={{ color: 'var(--text-muted)' }}>{sha256 ? `${sha256.substring(0, 16)}...` : 'Not available'}</strong></span>
            </div>

            {/* Optional Institutional Context */}
            {(institutionName || applicationId || academicYear) && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '12px',
                fontSize: '11.5px',
                color: 'var(--text-secondary)',
                marginTop: '4px',
              }}>
                {institutionName && <span>Institution: <strong style={{ color: 'var(--text-primary)' }}>{institutionName}</strong></span>}
                {applicationId && <span>App ID: <strong className="code-mono" style={{ color: 'var(--text-primary)' }}>{applicationId}</strong></span>}
                {academicYear && <span>Academic Year: <strong style={{ color: 'var(--text-primary)' }}>{academicYear}</strong></span>}
              </div>
            )}

            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: '8px',
              paddingTop: '8px',
              borderTop: '1px solid var(--border-subtle)',
              fontSize: '11.5px',
              color: 'var(--text-muted)',
            }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <span>{formattedPages}</span>
                <span>•</span>
                <span>{formattedSize}</span>
                <span>•</span>
                <span>{formattedDate}</span>
              </div>

              <button
                type="button"
                onClick={() => setShowMetadataModal(!showMetadataModal)}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '11px', padding: '3px 8px' }}
              >
                <Info size={12} />
                <span>{showMetadataModal ? 'Hide Details' : 'View Details'}</span>
              </button>
            </div>

            {/* Expandable Details Drawer */}
            {showMetadataModal && (
              <div style={{
                marginTop: '10px',
                padding: '10px 12px',
                backgroundColor: 'var(--bg-surface-subtle)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                fontSize: '11.5px',
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px' }}>
                  <div><strong>Full SHA-256:</strong> <span className="code-mono">{sha256 || 'Not available'}</span></div>
                  <div><strong>Rules Evaluated:</strong> {summary.total_rules_evaluated}</div>
                  <div><strong>Passed:</strong> <span style={{ color: '#16a34a' }}>{summary.passed_rules}</span></div>
                  <div><strong>Failed:</strong> <span style={{ color: '#dc2626' }}>{summary.failed_rules}</span></div>
                  <div><strong>Inconclusive:</strong> <span style={{ color: '#d97706' }}>{summary.inconclusive_rules}</span></div>
                  <div><strong>Authenticity Signals:</strong> {summary.authenticity_signals_count}</div>
                  <div><strong>Privacy Redactions:</strong> {summary.privacy_redactions_count}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right: Overall Verification Status Card */}
      <div className="surface-card" style={{
        padding: '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
      }}>
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: 'var(--text-muted)',
          marginBottom: '6px',
        }}>
          Overall Verification Status
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '50%',
            backgroundColor: statusConfig.bg,
            border: `1px solid ${statusConfig.border}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            {statusConfig.icon}
          </div>

          <div>
            <div style={{
              fontSize: '14px',
              fontWeight: '700',
              color: statusConfig.textColor,
              lineHeight: '1.25',
            }}>
              {statusConfig.title}
            </div>
            <div style={{
              fontSize: '11px',
              color: 'var(--text-secondary)',
              marginTop: '2px',
            }}>
              {statusConfig.subtitle}
            </div>
          </div>
        </div>

        {summary.requires_human_review && (
          <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)' }}>
            {(() => {
              const pendingCount = summary.inconclusive_rules + summary.failed_rules;
              return (
                <button
                  onClick={onOpenAdjudication}
                  className="btn btn-outline-amber btn-sm"
                  style={{ width: '100%', justifyContent: 'center', fontSize: '11.5px' }}
                >
                  Adjudicate Evidence ({pendingCount} {pendingCount === 1 ? 'item' : 'items'})
                </button>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
};
