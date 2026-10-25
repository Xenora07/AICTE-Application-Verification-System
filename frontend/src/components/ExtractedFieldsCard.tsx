import React, { useState } from 'react';
import { FieldEvidence, TableData } from '../types/api';

interface ExtractedFieldsCardProps {
  fields: Record<string, FieldEvidence>;
  tables: TableData[];
  processingMetadata: any;
}

const FIELD_LABELS: Record<string, string> = {
  academic_year: 'Academic Year',
  academic_year_start: 'Academic Year Start',
  academic_year_end: 'Academic Year End',
  application_id: 'Application ID',
  permanent_institute_id: 'Permanent Institute ID',
  institution_name: 'Institution Name',
  state: 'State',
  district: 'District',
  program_level: 'Program Level',
  course_name: 'Course Name',
  approved_intake: 'Approved Intake',
  total_intake: 'Total Approved Intake',
  principal_name: 'Principal Name',
  land_area_acres: 'Total Land Area (Acres)',
  built_up_area_sqm: 'Built-Up Area (Sq.m)',
};

export const formatFieldLabel = (key: string): string => {
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  return key
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
};

export const ExtractedFieldsCard: React.FC<ExtractedFieldsCardProps> = ({
  fields,
  tables,
  processingMetadata,
}) => {
  const [activeTab, setActiveTab] = useState<'fields' | 'tables' | 'metadata'>('fields');
  const fieldEntries = Object.entries(fields);

  return (
    <div className="surface-card" style={{ padding: '20px', marginBottom: '20px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
        paddingBottom: '12px',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>
          Extracted Institutional Evidence & Bounding Boxes
        </h3>

        {/* View Switcher */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setActiveTab('fields')}
            className={`btn ${activeTab === 'fields' ? 'btn-brand' : 'btn-secondary'} btn-sm`}
          >
            Mapped Fields ({fieldEntries.length})
          </button>
          <button
            onClick={() => setActiveTab('tables')}
            className={`btn ${activeTab === 'tables' ? 'btn-brand' : 'btn-secondary'} btn-sm`}
          >
            Extracted Tables ({tables.length})
          </button>
          <button
            onClick={() => setActiveTab('metadata')}
            className={`btn ${activeTab === 'metadata' ? 'btn-brand' : 'btn-secondary'} btn-sm`}
          >
            Pipeline Metadata
          </button>
        </div>
      </div>

      {activeTab === 'fields' && (
        <div>
          {fieldEntries.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No structured regulatory fields mapped from this document payload.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="ledger-table">
                <thead>
                  <tr>
                    <th>Field Name</th>
                    <th>Normalized Value</th>
                    <th>Raw Snippet</th>
                    <th>Page</th>
                    <th>Route</th>
                    <th>Confidence</th>
                    <th>Bounding Box</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {fieldEntries.map(([name, ev]) => (
                    <tr key={name}>
                      <td>
                        <div style={{ fontWeight: '600', color: 'var(--text-primary)', fontSize: '12.5px' }}>
                          {formatFieldLabel(name)}
                        </div>
                        <div className="code-mono" style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {name}
                        </div>
                      </td>
                      <td>
                        <strong style={{ color: 'var(--text-primary)' }}>
                          {ev.normalized_value !== null && ev.normalized_value !== undefined
                            ? String(ev.normalized_value)
                            : <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>null</span>}
                        </strong>
                      </td>
                      <td>
                        <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                          {ev.raw_value ? `"${ev.raw_value.substring(0, 40)}${ev.raw_value.length > 40 ? '...' : ''}"` : '—'}
                        </span>
                      </td>
                      <td>{ev.page_number || '—'}</td>
                      <td>
                        <span className="badge badge-pill badge-cat-compliance" style={{ fontSize: '10px' }}>
                          {ev.extraction_method || 'digital'}
                        </span>
                      </td>
                      <td>
                        {ev.confidence !== null && ev.confidence !== undefined ? (
                          <span className="code-mono" style={{ color: '#15803d', fontWeight: '600' }}>
                            {(ev.confidence * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>
                            {ev.extraction_method === 'digital' ? 'Deterministic (Digital)' : 'Not available'}
                          </span>
                        )}
                      </td>
                      <td>
                        {ev.bounding_box ? (
                          <span className="code-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            [{ev.bounding_box.map((b) => Math.round(b)).join(', ')}]
                          </span>
                        ) : '—'}
                      </td>
                      <td>
                        {ev.is_uncertain ? (
                          <span className="badge badge-inconclusive badge-pill" style={{ fontSize: '10px' }}>
                            Uncertain
                          </span>
                        ) : (
                          <span className="badge badge-pass badge-pill" style={{ fontSize: '10px' }}>
                            Deterministic
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'tables' && (
        <div>
          {tables.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No structured tables extracted from this document.
            </div>
          ) : (
            tables.map((t, idx) => (
              <div key={idx} style={{ marginBottom: '20px' }}>
                <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: 'var(--color-brand)' }}>
                  {t.table_name} (Page {t.page_number})
                </h4>
                <div style={{ overflowX: 'auto' }}>
                  <table className="ledger-table">
                    <thead>
                      <tr>
                        {t.headers.map((h, i) => (
                          <th key={i}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {t.rows.map((row, rIdx) => (
                        <tr key={rIdx}>
                          {t.headers.map((h, cIdx) => (
                            <td key={cIdx}>{String(row[h] || '-')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'metadata' && (
        <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '6px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '12.5px' }}>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Total Pages: </span>
              <strong>{processingMetadata?.total_pages}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Processed Pages: </span>
              <strong>{processingMetadata?.processed_pages}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Extraction Route: </span>
              <strong style={{ color: 'var(--color-brand)' }}>{processingMetadata?.extraction_path}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Digital Pages: </span>
              <span>{processingMetadata?.digital_pages?.join(', ') || 'None'}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>OCR Pages: </span>
              <span>{processingMetadata?.ocr_pages?.join(', ') || 'None'}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Timestamp (UTC): </span>
              <span className="code-mono">{processingMetadata?.timestamp_utc}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
