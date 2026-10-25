import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, FileText, Info, XCircle } from 'lucide-react';
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
}) => {
  const [showMetadataModal, setShowMetadataModal] = useState(false);

  const formattedSize = fileSizeBytes && fileSizeBytes > 0
    ? `${(fileSizeBytes / 1024).toFixed(1)} KB`
    : 'Size: Not available';

  const formattedPages = totalPages !== undefined && totalPages > 0
    ? `${totalPages} ${totalPages === 1 ? 'page' : 'pages'}`
    : 'Page count: Not available';

  const formattedDate = uploadedAt
    ? new Date(uploadedAt).toLocaleString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Upload time: Not available';

  const getStatusBadgeConfig = () => {
    const isNeedsReview = summary.requires_human_review || processingStatus.includes('WARNING') || processingStatus === 'NEEDS_HUMAN_REVIEW';
    const isFailed = processingStatus === 'ACTION_REQUIRED' || processingStatus === 'REJECTED' || summary.overall_status === 'REJECTED';

    if (isFailed) {
      return {
        icon: <XCircle size={22} style={{ color: '#ef4444' }} />,
        title: processingStatus || 'ACTION_REQUIRED',
        subtitle: 'Critical regulatory non-compliance detected',
        bg: '#fee2e2',
        border: '#fca5a5',
        textColor: '#b91c1c',
      };
    }

    if (isNeedsReview) {
      return {
        icon: <AlertTriangle size={22} style={{ color: '#d97706' }} />,
        title: processingStatus || 'SUCCESS_WITH_WARNINGS',
        subtitle: 'Needs human adjudication',
        bg: '#fef3c7',
        border: '#fde68a',
        textColor: '#b45309',
      };
    }

    return {
      icon: <CheckCircle2 size={22} style={{ color: '#16a34a' }} />,
      title: processingStatus || 'VERIFIED',
      subtitle: 'Deterministic compliance verified',
      bg: '#dcfce7',
      border: '#bbf7d0',
      textColor: '#15803d',
    };
  };

  const statusConfig = getStatusBadgeConfig();

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 340px',
      gap: '16px',
      marginBottom: '20px',
    }}>
      {/* Left: Current Document Metadata Box */}
      <div className="surface-card" style={{ padding: '18px 22px' }}>
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{
                fontSize: '10px',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: 'var(--text-muted)',
              }}>
                CURRENT DOCUMENT
              </span>
              <span className="badge badge-pass badge-pill" style={{ fontSize: '10px', padding: '1px 8px' }}>
                ✓ Processed
              </span>
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
              <span>Type: <strong className="code-mono" style={{ color: 'var(--text-primary)' }}>{documentType || 'Not available'}</strong></span>
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
        padding: '18px 20px',
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
          marginBottom: '8px',
        }}>
          Overall Verification Status
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
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
              fontSize: '14.5px',
              fontWeight: '700',
              color: statusConfig.textColor,
              lineHeight: '1.2',
            }}>
              {statusConfig.title}
            </div>
            <div style={{
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              marginTop: '2px',
            }}>
              {statusConfig.subtitle}
            </div>
          </div>
        </div>

        {summary.requires_human_review && (
          <div style={{ marginTop: '12px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)' }}>
            <button
              onClick={onOpenAdjudication}
              className="btn btn-outline-amber btn-sm"
              style={{ width: '100%', justifyContent: 'center', fontSize: '11.5px' }}
            >
              Adjudicate Evidence ({summary.inconclusive_rules + summary.failed_rules} items)
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
