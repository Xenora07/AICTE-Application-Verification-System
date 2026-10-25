import React from 'react';
import { FlaskConical, Play } from 'lucide-react';
import { SyntheticTestCase } from '../types/api';

interface SyntheticTestRunnerProps {
  testCases: SyntheticTestCase[];
  onExecuteScenario: (testId: string) => void;
  isLoading: boolean;
  activeTestId?: string;
}

export const SyntheticTestRunner: React.FC<SyntheticTestRunnerProps> = ({
  testCases,
  onExecuteScenario,
  isLoading,
  activeTestId,
}) => {
  return (
    <div className="surface-card" style={{ padding: '22px', marginBottom: '24px' }}>
      <div style={{ marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid var(--border-subtle)' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '3px' }}>
          Synthetic Regulatory Edge Cases & Failure Scenarios (TC01 – TC10)
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Execute standardized synthetic scenarios to demonstrate how the deterministic validation engine, authenticity gateway, and human-review routing respond to deliberate regulatory discrepancies.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
        {testCases.map((tc) => {
          const isActive = activeTestId === tc.test_id;
          return (
            <div
              key={tc.test_id}
              style={{
                backgroundColor: isActive ? 'var(--color-brand-light)' : 'var(--bg-surface-subtle)',
                border: `1px solid ${isActive ? 'var(--color-amber-accent)' : 'var(--border-color)'}`,
                borderRadius: '6px',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span className="code-mono" style={{ fontSize: '12px', color: 'var(--color-brand)', fontWeight: '700' }}>
                    {tc.test_id}
                  </span>
                  <span className={`badge ${tc.expected_outcome === 'SUCCESS' ? 'badge-pass' : tc.expected_outcome.includes('FAILED') ? 'badge-fail' : 'badge-inconclusive'} badge-pill`} style={{ fontSize: '10.5px' }}>
                    {tc.expected_outcome === 'SUCCESS'
                      ? 'Expected: Pass'
                      : tc.expected_outcome.includes('FAILED')
                      ? 'Expected: Fail'
                      : 'Expected: Review'}
                  </span>
                </div>

                <div style={{ fontSize: '13.5px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  {tc.scenario_name}
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: '1.4' }}>
                  {tc.description}
                </p>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                  <span>Rule: <strong className="code-mono" style={{ color: 'var(--text-primary)' }}>{tc.expected_rule_ids?.join(', ')}</strong></span>
                  <span>•</span>
                  <span>Severity: <strong style={{ color: tc.expected_severity === 'CRITICAL' ? 'var(--color-fail-text)' : tc.expected_severity === 'HIGH' ? '#c2410c' : 'var(--text-primary)' }}>{tc.expected_severity}</strong></span>
                  {tc.requires_human_review && (
                    <>
                      <span>•</span>
                      <span style={{ color: 'var(--color-inconclusive-text)', fontWeight: '600' }}>Requires Review</span>
                    </>
                  )}
                </div>
              </div>

              <div style={{ marginTop: '12px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => onExecuteScenario(tc.test_id)}
                  disabled={isLoading}
                  className={`btn ${isActive ? 'btn-brand' : 'btn-secondary'} btn-sm`}
                  style={{ fontSize: '11.5px', padding: '3px 10px' }}
                >
                  <Play size={11} />
                  <span>{isLoading && isActive ? 'Executing...' : 'Run Scenario'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
