import React, { useEffect, useState } from 'react';
import { Check, AlertTriangle, XCircle, CheckCircle2 } from 'lucide-react';
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

const DEFAULT_ACTION_NOTES: Record<AdjudicationDecision, string> = {
  CONFIRMED_VALID: 'Accepted exception based on official stamp and manual cross-verification.',
  REJECTED_NON_COMPLIANT: 'Confirmed regulatory non-compliance; application flagged for remediation.',
  REQUEST_CLARIFICATION: 'Issued formal clarification request to institution regarding evidence discrepancy.',
};

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

  // Sync notes input when active finding changes or when adjudications update
  useEffect(() => {
    if (currentFinding && adjudications[currentFinding.finding_id]) {
      setNotesInput(adjudications[currentFinding.finding_id].notes);
    } else {
      setNotesInput('');
    }
    setLastActionConfirmation(null);
  }, [activeFindingIndex, currentFinding?.finding_id, adjudications]);

  if (!isOpen) return null;

  const currentDecision = currentFinding ? adjudications[currentFinding.finding_id] : undefined;

  const handleSelectDecision = (decision: AdjudicationDecision) => {
    if (!currentFinding) return;

    const defaultNote = DEFAULT_ACTION_NOTES[decision];
    const isOtherDefaultNote = Object.values(DEFAULT_ACTION_NOTES).includes(notesInput.trim());

    // If remarks are empty OR match any action's default note, use the new decision's default note.
    // Otherwise preserve the officer's custom typed note.
    const notesToSave = (!notesInput.trim() || isOtherDefaultNote)
      ? defaultNote
      : notesInput.trim();

    const record: AdjudicationRecord = {
      findingId: currentFinding.finding_id,
      ruleId: currentFinding.rule_id,
      ruleName: currentFinding.rule_name,
      decision,
      notes: notesToSave,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    };

    setNotesInput(notesToSave);
    onSaveAdjudication(record);
    setLastActionConfirmation(
      `✓ Action recorded: "${decision}" for ${currentFinding.rule_id} (${currentFinding.rule_name}). Saved to session draft.`
    );
  };

  const handleSaveAndClose = () => {
    if (currentFinding && currentDecision) {
      onSaveAdjudication({
        ...currentDecision,
        notes: notesInput.trim() || currentDecision.notes,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      });
    }
    onClose();
  };

  // Accurately count reviewable findings that have an in-session draft decision
  const adjudicatedCount = reviewableFindings.filter((f) => !!adjudications[f.finding_id]).length;

  return (
    <div
      style={{
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
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="adjudication-panel-title"
    >
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          maxWidth: '840px',
          width: '100%',
          maxHeight: '92vh',
          overflowY: 'auto',
          padding: '24px',
          boxShadow: 'var(--shadow-dropdown)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
          <div>
            <h3
              id="adjudication-panel-title"
              style={{ fontSize: '16px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}
            >
              <span>Regulatory Officer Adjudication Panel</span>
              <span className="badge badge-pill" style={{ backgroundColor: 'var(--color-brand-light)', color: 'var(--color-brand)', fontSize: '10px' }}>
                Decision Support
              </span>
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Document: <span className="code-mono">{documentId}</span> • Human regulatory adjudication workflow
            </p>
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary btn-sm"
            style={{ padding: '4px 10px' }}
            aria-label="Close Adjudication Panel"
          >
            Close
          </button>
        </div>

        {/* Limitation notice: UI-level session draft */}
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: 'var(--bg-surface-subtle)',
            borderLeft: '3px solid #0284c7',
            borderRadius: '0 4px 4px 0',
            fontSize: '11.5px',
            color: 'var(--text-secondary)',
            marginBottom: '16px',
          }}
        >
          <strong>Audit Note:</strong> Adjudication actions are saved as an in-session officer draft. Decisions survive panel closing and reopening, but are not permanently written to a database endpoint.
        </div>

        {/* Action Confirmation Banner */}
        {lastActionConfirmation && (
          <div
            style={{
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
            }}
          >
            <span>{lastActionConfirmation}</span>
            <button
              onClick={() => setLastActionConfirmation(null)}
              style={{ background: 'none', border: 'none', color: 'var(--color-pass-text)', fontSize: '14px', cursor: 'pointer' }}
              aria-label="Dismiss confirmation"
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
                const isActive = idx === activeFindingIndex;
                const pillBorderColor = decided
                  ? (decided.decision === 'CONFIRMED_VALID' ? '#15803d' : decided.decision === 'REJECTED_NON_COMPLIANT' ? '#b91c1c' : '#b45309')
                  : (isActive ? 'var(--color-brand)' : 'var(--border-color)');

                return (
                  <button
                    key={f.finding_id}
                    onClick={() => setActiveFindingIndex(idx)}
                    className="btn btn-sm"
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '11.5px',
                      fontWeight: '600',
                      backgroundColor: isActive ? 'var(--color-brand)' : 'var(--bg-surface)',
                      color: isActive ? '#ffffff' : (decided ? 'var(--text-primary)' : 'var(--text-secondary)'),
                      border: `1.5px solid ${pillBorderColor}`,
                      whiteSpace: 'nowrap',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      cursor: 'pointer',
                    }}
                    title={`Rule ID: ${f.rule_id}`}
                    aria-selected={isActive}
                  >
                    {decided && <Check size={12} style={{ strokeWidth: 3, color: isActive ? '#ffffff' : pillBorderColor }} />}
                    <span>{f.rule_name || f.rule_id}</span>
                    {decided && (
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: '700',
                          opacity: isActive ? 0.9 : 0.8,
                          marginLeft: '2px',
                        }}
                      >
                        ({decided.decision})
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {currentFinding && (
              <div
                style={{
                  backgroundColor: 'var(--bg-surface-subtle)',
                  padding: '16px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  marginBottom: '18px',
                }}
              >
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
                    <pre
                      style={{
                        marginTop: '6px',
                        padding: '8px',
                        backgroundColor: 'var(--bg-surface-subtle)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '4px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        color: 'var(--text-primary)',
                        overflowX: 'auto',
                      }}
                    >
                      {JSON.stringify(currentFinding.evidence_values, null, 2)}
                    </pre>
                  )}
                </div>

                {/* Form to record official decision */}
                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '14px' }}>
                  <label style={{ display: 'block', fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '10px' }}>
                    Select Adjudication Action:
                  </label>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px', marginBottom: '14px' }}>
                    {/* Action 1: Validate Exception */}
                    <button
                      type="button"
                      data-testid="action-btn-validate"
                      onClick={() => handleSelectDecision('CONFIRMED_VALID')}
                      className={`btn ${currentDecision?.decision === 'CONFIRMED_VALID' ? 'active' : ''}`}
                      aria-pressed={currentDecision?.decision === 'CONFIRMED_VALID'}
                      style={{
                        padding: '10px 14px',
                        fontSize: '12.5px',
                        fontWeight: '600',
                        justifyContent: 'center',
                        backgroundColor: currentDecision?.decision === 'CONFIRMED_VALID' ? '#15803d' : 'var(--bg-surface)',
                        border: `1.5px solid ${currentDecision?.decision === 'CONFIRMED_VALID' ? '#15803d' : '#15803d'}`,
                        color: currentDecision?.decision === 'CONFIRMED_VALID' ? '#ffffff' : '#15803d',
                        boxShadow: currentDecision?.decision === 'CONFIRMED_VALID' ? '0 0 0 3px rgba(21, 128, 61, 0.25), 0 2px 4px rgba(0,0,0,0.1)' : 'none',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease-in-out',
                      }}
                    >
                      <Check size={15} style={{ strokeWidth: 2.5 }} />
                      <span>Validate Exception</span>
                      {currentDecision?.decision === 'CONFIRMED_VALID' && (
                        <span style={{ fontSize: '10px', backgroundColor: 'rgba(255,255,255,0.28)', padding: '1px 6px', borderRadius: '999px', marginLeft: '4px' }}>
                          ✓ Active
                        </span>
                      )}
                    </button>

                    {/* Action 2: Flag Non-Compliant */}
                    <button
                      type="button"
                      data-testid="action-btn-reject"
                      onClick={() => handleSelectDecision('REJECTED_NON_COMPLIANT')}
                      className={`btn ${currentDecision?.decision === 'REJECTED_NON_COMPLIANT' ? 'active' : ''}`}
                      aria-pressed={currentDecision?.decision === 'REJECTED_NON_COMPLIANT'}
                      style={{
                        padding: '10px 14px',
                        fontSize: '12.5px',
                        fontWeight: '600',
                        justifyContent: 'center',
                        backgroundColor: currentDecision?.decision === 'REJECTED_NON_COMPLIANT' ? '#b91c1c' : 'var(--bg-surface)',
                        border: `1.5px solid ${currentDecision?.decision === 'REJECTED_NON_COMPLIANT' ? '#b91c1c' : '#b91c1c'}`,
                        color: currentDecision?.decision === 'REJECTED_NON_COMPLIANT' ? '#ffffff' : '#b91c1c',
                        boxShadow: currentDecision?.decision === 'REJECTED_NON_COMPLIANT' ? '0 0 0 3px rgba(185, 28, 28, 0.25), 0 2px 4px rgba(0,0,0,0.1)' : 'none',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease-in-out',
                      }}
                    >
                      <XCircle size={15} style={{ strokeWidth: 2.5 }} />
                      <span>Flag Non-Compliant</span>
                      {currentDecision?.decision === 'REJECTED_NON_COMPLIANT' && (
                        <span style={{ fontSize: '10px', backgroundColor: 'rgba(255,255,255,0.28)', padding: '1px 6px', borderRadius: '999px', marginLeft: '4px' }}>
                          ✓ Active
                        </span>
                      )}
                    </button>

                    {/* Action 3: Request Clarification */}
                    <button
                      type="button"
                      data-testid="action-btn-clarify"
                      onClick={() => handleSelectDecision('REQUEST_CLARIFICATION')}
                      className={`btn ${currentDecision?.decision === 'REQUEST_CLARIFICATION' ? 'active' : ''}`}
                      aria-pressed={currentDecision?.decision === 'REQUEST_CLARIFICATION'}
                      style={{
                        padding: '10px 14px',
                        fontSize: '12.5px',
                        fontWeight: '600',
                        justifyContent: 'center',
                        backgroundColor: currentDecision?.decision === 'REQUEST_CLARIFICATION' ? '#b45309' : 'var(--bg-surface)',
                        border: `1.5px solid ${currentDecision?.decision === 'REQUEST_CLARIFICATION' ? '#b45309' : '#b45309'}`,
                        color: currentDecision?.decision === 'REQUEST_CLARIFICATION' ? '#ffffff' : '#b45309',
                        boxShadow: currentDecision?.decision === 'REQUEST_CLARIFICATION' ? '0 0 0 3px rgba(180, 83, 9, 0.25), 0 2px 4px rgba(0,0,0,0.1)' : 'none',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease-in-out',
                      }}
                    >
                      <AlertTriangle size={15} style={{ strokeWidth: 2.5 }} />
                      <span>Request Clarification</span>
                      {currentDecision?.decision === 'REQUEST_CLARIFICATION' && (
                        <span style={{ fontSize: '10px', backgroundColor: 'rgba(255,255,255,0.28)', padding: '1px 6px', borderRadius: '999px', marginLeft: '4px' }}>
                          ✓ Active
                        </span>
                      )}
                    </button>
                  </div>

                  {/* Officer Remarks Textarea */}
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', fontSize: '11.5px', color: 'var(--text-secondary)', marginBottom: '4px', fontWeight: '500' }}>
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
                            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
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

                  {/* Immediate Visual Feedback for Selected Action */}
                  {currentDecision ? (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        backgroundColor: currentDecision.decision === 'CONFIRMED_VALID'
                          ? 'var(--color-pass-bg)'
                          : currentDecision.decision === 'REJECTED_NON_COMPLIANT'
                          ? 'var(--color-fail-bg)'
                          : 'var(--color-inconclusive-bg)',
                        border: `1px solid ${
                          currentDecision.decision === 'CONFIRMED_VALID'
                            ? 'var(--color-pass-border)'
                            : currentDecision.decision === 'REJECTED_NON_COMPLIANT'
                            ? 'var(--color-fail-border)'
                            : 'var(--color-inconclusive-border)'
                        }`,
                        borderRadius: '6px',
                        fontSize: '12px',
                        color: currentDecision.decision === 'CONFIRMED_VALID'
                          ? 'var(--color-pass-text)'
                          : currentDecision.decision === 'REJECTED_NON_COMPLIANT'
                          ? 'var(--color-fail-text)'
                          : 'var(--color-inconclusive-text)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                        <CheckCircle2 size={15} style={{ strokeWidth: 2.5 }} />
                        <span>
                          Action Recorded: <strong>{currentDecision.decision}</strong>
                          {currentDecision.notes && <span style={{ opacity: 0.9 }}> — "{currentDecision.notes}"</span>}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', opacity: 0.8, whiteSpace: 'nowrap', marginLeft: '12px' }}>
                        {currentDecision.timestamp} • Session Draft
                      </span>
                    </div>
                  ) : (
                    <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', fontStyle: 'italic', padding: '4px 0' }}>
                      No adjudication decision recorded yet for this finding. Select an action above to log a draft decision.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Bottom Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                <strong style={{ color: adjudicatedCount > 0 ? 'var(--color-brand)' : 'var(--text-primary)' }}>
                  {adjudicatedCount}
                </strong> of {reviewableFindings.length} findings adjudicated in draft
              </div>
              <button onClick={handleSaveAndClose} className="btn btn-brand" style={{ padding: '8px 18px', fontWeight: '600' }}>
                Done Reviewing
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
