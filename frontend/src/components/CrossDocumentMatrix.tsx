import React from 'react';
import { CopyCheck, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { CrossValidateResponse } from '../types/api';

interface CrossDocumentMatrixProps {
  onRunCrossValidation: () => void;
  crossReport: CrossValidateResponse | null;
  isLoading: boolean;
  activeDocumentsCount: number;
}

export const CrossDocumentMatrix: React.FC<CrossDocumentMatrixProps> = ({
  onRunCrossValidation,
  crossReport,
  isLoading,
  activeDocumentsCount,
}) => {
  return (
    <div className="surface-card" style={{ padding: '22px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '18px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
            Cross-Document Regulatory Consistency Engine
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Compares multi-document submissions (e.g. AICTE Extension of Approval vs Mandatory Disclosure) to ensure quota integrity and identify institutional discrepancies.
          </p>
        </div>

        <div>
          <button
            onClick={onRunCrossValidation}
            disabled={isLoading || activeDocumentsCount < 2}
            className="btn btn-brand"
            style={{ fontSize: '12.5px' }}
          >
            <CopyCheck size={14} />
            <span>{isLoading ? 'Comparing Bundle...' : `Cross-Check Documents (${activeDocumentsCount} in session)`}</span>
          </button>
        </div>
      </div>

      {activeDocumentsCount < 2 && !crossReport && (
        <div style={{
          padding: '24px',
          backgroundColor: 'var(--bg-surface-subtle)',
          borderRadius: '6px',
          border: '1px dashed var(--border-color)',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '12.5px',
        }}>
          Cross-document verification requires at least 2 processed documents in the current session (e.g. upload an AICTE EoA and a Mandatory Disclosure, or test synthetic pair TC_SYNTH_005 / TC_SYNTH_006).
        </div>
      )}

      {crossReport && (
        <div>
          {/* Consistency Overview Pill */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            backgroundColor: crossReport.overall_status === 'PASS' ? 'var(--color-pass-bg)' : 'var(--color-fail-bg)',
            border: `1px solid ${crossReport.overall_status === 'PASS' ? 'var(--color-pass-border)' : 'var(--color-fail-border)'}`,
            borderRadius: '6px',
            marginBottom: '16px',
          }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Cross-Document Verification Status</div>
              <div style={{ fontSize: '15px', fontWeight: '700', color: crossReport.overall_status === 'PASS' ? 'var(--color-pass-text)' : 'var(--color-fail-text)' }}>
                {crossReport.overall_status === 'PASS' ? 'CONSISTENT — ALL CROSS-CHECKS PASSED' : 'DISCREPANCY DETECTED'}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <span className={`badge ${crossReport.overall_status === 'PASS' ? 'badge-pass' : 'badge-fail'} badge-pill`}>
                {crossReport.overall_status}
              </span>
              {crossReport.requires_human_review && (
                <span className="badge badge-inconclusive badge-pill">
                  Adjudication Required
                </span>
              )}
            </div>
          </div>

          {/* Consistency Findings List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {crossReport.normalized_findings.map((f, i) => (
              <div
                key={i}
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'var(--bg-surface-subtle)',
                  borderRadius: '6px',
                  border: `1px solid ${f.outcome === 'FAIL' ? 'var(--color-fail-border)' : f.outcome === 'INCONCLUSIVE' ? 'var(--color-inconclusive-border)' : 'var(--border-color)'}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={`badge ${f.outcome === 'PASS' ? 'badge-pass' : f.outcome === 'FAIL' ? 'badge-fail' : 'badge-inconclusive'} badge-pill`}>
                      {f.outcome}
                    </span>
                    <span className="code-mono" style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-brand)' }}>
                      {f.rule_id}
                    </span>
                    <span style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)' }}>
                      {f.rule_name}
                    </span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Docs: {f.affected_document_ids?.join(' and ')}
                  </span>
                </div>

                <p style={{ fontSize: '12px', color: f.outcome === 'FAIL' ? 'var(--color-fail-text)' : 'var(--text-secondary)', marginTop: '4px' }}>
                  {f.explanation}
                </p>

                {f.evidence_values && Object.keys(f.evidence_values).length > 0 && (
                  <pre style={{
                    marginTop: '6px',
                    padding: '8px',
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '4px',
                    fontSize: '11px',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-mono)',
                    overflowX: 'auto',
                  }}>
                    {JSON.stringify(f.evidence_values, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
