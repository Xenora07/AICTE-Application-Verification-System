import React, { useEffect, useState } from 'react';
import { Check, X, AlertTriangle, XCircle, CheckCircle2 } from 'lucide-react';
import { AdjudicationDecision, AdjudicationRecord, NormalizedFinding } from '../types/api';

interface HumanReviewDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  findings: NormalizedFinding[];
  documentId: string;
  adjudications: Record<string, AdjudicationRecord>;
  onSaveAdjudication: (record: AdjudicationRecord) => void;
  initialFindingId?: string;
}

export const HumanReviewDrawer: React.FC<HumanReviewDrawerProps> = ({
  isOpen,
  onClose,
  findings,
  documentId,
  adjudications,
  onSaveAdjudication,
  initialFindingId,
}) => {
  const [activeFindingIndex, setActiveFindingIndex] = useState(0);
  const [notesInput, setNotesInput] = useState('');
  const [lastActionConfirmation, setLastActionConfirmation] = useState<string | null>(null);

  const reviewableFindings = findings.filter(
    (f) => f.requires_human_review || f.outcome === 'INCONCLUSIVE' || f.outcome === 'FAIL'
  );

  // Synchronize active finding index with requested initialFindingId on open
  useEffect(() => {
    if (isOpen && initialFindingId) {
      const targetIdx = reviewableFindings.findIndex((f) => f.finding_id === initialFindingId);
      if (targetIdx !== -1) {
        setActiveFindingIndex(targetIdx);
      }
    } else if (isOpen && (!initialFindingId || activeFindingIndex >= reviewableFindings.length)) {
      if (activeFindingIndex >= reviewableFindings.length) {
        setActiveFindingIndex(0);
      }
    }
  }, [isOpen, initialFindingId, reviewableFindings.length]);

  const currentFinding = reviewableFindings[activeFindingIndex];

  // Sync notes input when active finding changes
  useEffect(() => {
    if (currentFinding && adjudications[currentFinding.finding_id]) {
      setNotesInput(adjudications[currentFinding.finding_id].notes);
    } else {
      setNotesInput('');
    }
    setLastActionConfirmation(null);
  }, [activeFindingIndex, currentFinding?.finding_id]);

  if (!isOpen) return null;

  const handleSelectDecision = (decision: AdjudicationDecision, defaultNote: string) => {
    if (!currentFinding) return;

    const notesToSave = notesInput.trim() || defaultNote;
    const record: AdjudicationRecord = {
      findingId: currentFinding.finding_id,
      ruleId: currentFinding.rule_id,
      ruleName: currentFinding.rule_name,
      decision,
      notes: notesToSave,
      timestamp: new Date().toLocaleTimeString(),
    };

    setNotesInput(notesToSave);
    onSaveAdjudication(record);
    setLastActionConfirmation(
      `✓ Action recorded: "${decision}" for ${currentFinding.rule_id} (${currentFinding.rule_name}). Saved to session draft.`
    );
  };

  const currentDecision = currentFinding ? adjudications[currentFinding.finding_id] : undefined;

  const handleSaveAndClose = () => {
    if (currentFinding && currentDecision) {
      onSaveAdjudication({
        ...currentDecision,
        notes: notesInput.trim() || currentDecision.notes,
        timestamp: new Date().toLocaleTimeString(),
      });
    }
    onClose();
  };

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
      <div style={{
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        maxWidth: '820px',
        width: '100%',
        maxHeight: '92vh',
        overflowY: 'auto',
        padding: '24px',
        boxShadow: 'var(--shadow-dropdown)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <span>Regulatory Officer Adjudication Panel</span>
              <span className="badge badge-pill" style={{ backgroundColor: 'var(--color-brand-light)', color: 'var(--color-brand)', fontSize: '10px' }}>
                Decision Support
              </span>
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Document: <span className="code-mono">{documentId}</span> • Human regulatory adjudication workflow
            </p>
          </div>
          <button onClick={onClose} className="btn btn-secondary btn-sm" style={{ padding: '4px 10px' }}>
            Close
          </button>
        </div>

        {/* Limitation notice: UI-level session draft */}
        <div style={{
          padding: '8px 12px',
          backgroundColor: 'var(--bg-surface-subtle)',
          borderLeft: '3px solid #0284c7',
          borderRadius: '0 4px 4px 0',
          fontSize: '11.5px',
          color: 'var(--text-secondary)',
          marginBottom: '16px',
        }}>
          <strong>Audit Note:</strong> Adjudication actions are saved as an in-session officer draft. Decisions survive panel closing and reopening, but are not permanently written to a database endpoint.
        </div>

        {/* Action Confirmation Banner */}
        {lastActionConfirmation && (
          <div style={{
            padding: '9px 12px',
            backgroundColor: 'var(--color-pass-bg)',
            border: '1px solid var(--color-pass-border)',
            borderRadius: '6px',
            color: 'var(--color-pass-text)',
            fontSize: '12px',
            fontWeight: '600',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <span>{lastActionConfirmation}</span>
            <button
              onClick={() => setLastActionConfirmation(null)}
              style={{ background: 'none', color: 'var(--color-pass-text)', fontSize: '14px', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>
        )}

        {reviewableFindings.length === 0 ? (
          <div style={{ padding: '36px', textAlign: 'center', color: 'var(--color-pass-text)' }}>
            All findings in this document are deterministic PASS. No items require manual adjudication.
          </div>
        ) : (
          <div>
            {/* Finding Selector Pills */}
            <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '10px', marginBottom: '14px' }}>
              {reviewableFindings.map((f, idx) => {
                const decided = adjudications[f.finding_id];
                return (
                  <button
                    key={f.finding_id}
                    onClick={() => setActiveFindingIndex(idx)}
                    style={{
                      padding: '5px 10px',
                      borderRadius: '5px',
                      fontSize: '11.5px',
                      fontWeight: '600',
                      backgroundColor: idx === activeFindingIndex ? 'var(--color-brand)' : 'var(--bg-surface)',
                      color: idx === activeFindingIndex ? '#ffffff' : 'var(--text-secondary)',
                      border: `1px solid ${decided ? '#15803d' : idx === activeFindingIndex ? 'var(--color-brand)' : 'var(--border-color)'}`,
                      whiteSpace: 'nowrap',
                    }}
                    title={`Rule ID: ${f.rule_id}`}
                  >
                    {decided ? '✓ ' : ''}{f.rule_name || f.rule_id}
                    {decided ? ` (${decided.decision})` : ''}
                  </button>
                );
              })}
            </div>

            {currentFinding && (
              <div style={{
                backgroundColor: 'var(--bg-surface-subtle)',
                padding: '16px',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                marginBottom: '18px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span className="code-mono" style={{ fontSize: '12px', color: 'var(--color-brand)', fontWeight: '600' }}>
                    {currentFinding.rule_id}
                  </span>
                  <span className={`badge ${currentFinding.outcome === 'PASS' ? 'badge-pass' : currentFinding.outcome === 'FAIL' ? 'badge-fail' : 'badge-inconclusive'}`}>
                    {currentFinding.outcome}
                  </span>
                </div>

                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '6px', color: 'var(--text-primary)' }}>
                  {currentFinding.rule_name}
                </h4>

                <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                  {currentFinding.explanation}
                </p>

                <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                  <div>Affected Fields: <strong className="code-mono" style={{ color: 'var(--text-primary)' }}>{currentFinding.affected_fields?.join(', ') || 'None'}</strong></div>
                  {currentFinding.evidence_values && Object.keys(currentFinding.evidence_values).length > 0 && (
                    <pre style={{
                      marginTop: '6px',
                      padding: '8px',
                      backgroundColor: 'var(--bg-surface-subtle)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '4px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '11px',
                      color: 'var(--text-primary)',
                      overflowX: 'auto',
                    }}>
                      {JSON.stringify(currentFinding.evidence_values, null, 2)}
                    </pre>
                  )}
                </div>

                {/* Form to record official decision */}
                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>
                    Select Adjudication Action:
                  </label>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
                    <button
                      type="button"
                      onClick={() => handleSelectDecision('CONFIRMED_VALID', 'Accepted exception based on official stamp and manual cross-verification.')}
                      className="btn btn-sm"
                      style={{
                        backgroundColor: currentDecision?.decision === 'CONFIRMED_VALID' ? '#15803d' : 'var(--bg-surface)',
                        border: `1px solid ${currentDecision?.decision === 'CONFIRMED_VALID' ? '#15803d' : 'var(--border-color)'}`,
                        color: currentDecision?.decision === 'CONFIRMED_VALID' ? '#ffffff' : '#15803d',
                        fontWeight: '600',
                      }}
                    >
                      ✓ Validate Exception
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectDecision('REJECTED_NON_COMPLIANT', 'Confirmed regulatory non-compliance; application flagged for remediation.')}
                      className="btn btn-sm"
                      style={{
                        backgroundColor: currentDecision?.decision === 'REJECTED_NON_COMPLIANT' ? '#b91c1c' : 'var(--bg-surface)',
                        border: `1px solid ${currentDecision?.decision === 'REJECTED_NON_COMPLIANT' ? '#b91c1c' : 'var(--border-color)'}`,
                        color: currentDecision?.decision === 'REJECTED_NON_COMPLIANT' ? '#ffffff' : '#b91c1c',
                        fontWeight: '600',
                      }}
                    >
                      ✗ Flag Non-Compliant
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectDecision('REQUEST_CLARIFICATION', 'Issued formal clarification request to institution regarding evidence discrepancy.')}
                      className="btn btn-sm"
                      style={{
                        backgroundColor: currentDecision?.decision === 'REQUEST_CLARIFICATION' ? '#b45309' : 'var(--bg-surface)',
                        border: `1px solid ${currentDecision?.decision === 'REQUEST_CLARIFICATION' ? '#b45309' : 'var(--border-color)'}`,
                        color: currentDecision?.decision === 'REQUEST_CLARIFICATION' ? '#ffffff' : '#b45309',
                        fontWeight: '600',
                      }}
                    >
                      ? Request Clarification
                    </button>
                  </div>

                  {/* Officer Remarks Textarea */}
                  <div style={{ marginBottom: '10px' }}>
                    <label style={{ display: 'block', fontSize: '11.5px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      Officer Audit Remarks:
                    </label>
                    <textarea
                      rows={2}
                      value={notesInput}
                      onChange={(e) => {
                        const val = e.target.value;
                        setNotesInput(val);
                        if (currentDecision) {
                          onSaveAdjudication({
                            ...currentDecision,
                            notes: val,
                            timestamp: new Date().toLocaleTimeString(),
                          });
                        }
                      }}
                      placeholder="Enter specific audit remarks or justification for regulatory file..."
                      style={{
                        width: '100%',
                        padding: '8px 10px',
                        borderRadius: '6px',
                        backgroundColor: 'var(--bg-surface)',
                        border: '1px solid var(--border-color)',
                        fontSize: '12px',
                        color: 'var(--text-primary)',
                      }}
                    />
                  </div>

                  {/* Recorded Decision Summary Pill */}
                  {currentDecision && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '7px 10px',
                      backgroundColor: 'var(--color-pass-bg)',
                      border: '1px solid var(--color-pass-border)',
                      borderRadius: '5px',
                      fontSize: '11.5px',
                      color: 'var(--color-pass-text)',
                    }}>
                      <div>
                        Action Recorded: <strong>{currentDecision.decision}</strong>
                        {currentDecision.notes && <span> — "{currentDecision.notes}"</span>}
                      </div>
                      <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>
                        {currentDecision.timestamp}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Bottom Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                {Object.keys(adjudications).length} of {reviewableFindings.length} findings adjudicated in draft
              </div>
              <button onClick={handleSaveAndClose} className="btn btn-brand">
                Done Reviewing
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
