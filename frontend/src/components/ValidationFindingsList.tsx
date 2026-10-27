import React, { useState, useMemo, useEffect } from 'react';
import {
  Search,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  FileText,
  AlertTriangle,
  XCircle,
  MoreHorizontal,
  Check,
  Layers,
  FileCheck2,
} from 'lucide-react';
import {
  AdjudicationRecord,
  FieldEvidence,
  FindingCategory,
  NormalizedFinding,
  RuleOutcome,
  RuleSeverity,
} from '../types/api';

interface ValidationFindingsListProps {
  findings: NormalizedFinding[];
  adjudications?: Record<string, AdjudicationRecord>;
  onOpenAdjudicationForFinding?: (findingId: string) => void;
  onOpenReviewAll?: () => void;
  extractedFields?: Record<string, FieldEvidence>;
  totalPages?: number;
  documentFilename?: string;
  pdfUrl?: string | null;
}

export const ValidationFindingsList: React.FC<ValidationFindingsListProps> = ({
  findings,
  adjudications = {},
  onOpenAdjudicationForFinding,
  onOpenReviewAll,
  extractedFields = {},
  totalPages,
  documentFilename,
  pdfUrl,
}) => {
  // Filters state
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('ALL');
  const [needsJudgmentOnly, setNeedsJudgmentOnly] = useState(false);

  // Selected finding for evidence inspector
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(
    findings[0]?.finding_id || null
  );
  const [evidenceTab, setEvidenceTab] = useState<'details' | 'rule' | 'value'>('details');
  const [zoomLevel, setZoomLevel] = useState(100);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [viewMode, setViewMode] = useState<'evidence' | 'pdf'>(pdfUrl ? 'pdf' : 'evidence');

  // Filter findings based on user criteria
  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      // Type / Category
      if (typeFilter !== 'ALL' && f.category !== typeFilter) return false;
      // Severity
      if (severityFilter !== 'ALL' && f.severity !== severityFilter) return false;
      // Outcome
      if (outcomeFilter === 'ADJUDICATED') {
        if (!adjudications[f.finding_id]) return false;
      } else if (outcomeFilter !== 'ALL' && f.outcome !== outcomeFilter) {
        return false;
      }
      // Needs judgment toggle (filters out already adjudicated findings and PASS findings)
      if (needsJudgmentOnly && (!f.requires_human_review || !!adjudications[f.finding_id])) return false;
      // Search query
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const matchesId = f.rule_id.toLowerCase().includes(query);
        const matchesName = f.rule_name.toLowerCase().includes(query);
        const matchesField = f.affected_fields?.some((af) => af.toLowerCase().includes(query));
        const matchesExplanation = f.explanation.toLowerCase().includes(query);
        const matchesAdjudication = adjudications[f.finding_id]?.decision.toLowerCase().includes(query) ||
          adjudications[f.finding_id]?.notes.toLowerCase().includes(query);
        if (!matchesId && !matchesName && !matchesField && !matchesExplanation && !matchesAdjudication) return false;
      }
      return true;
    });
  }, [findings, adjudications, typeFilter, severityFilter, outcomeFilter, needsJudgmentOnly, searchTerm]);

  // Active finding
  const activeFinding = useMemo(() => {
    if (!selectedFindingId && filteredFindings.length > 0) {
      return filteredFindings[0];
    }
    return findings.find((f) => f.finding_id === selectedFindingId) || filteredFindings[0] || null;
  }, [selectedFindingId, filteredFindings, findings]);

  // Derive evidence metadata from active finding's affected fields
  const activeEvidence: FieldEvidence | null = useMemo(() => {
    if (!activeFinding || !activeFinding.affected_fields || activeFinding.affected_fields.length === 0) {
      return null;
    }
    for (const fieldName of activeFinding.affected_fields) {
      if (extractedFields[fieldName]) {
        return extractedFields[fieldName];
      }
    }
    return null;
  }, [activeFinding, extractedFields]);

  // Synchronize current page with active evidence
  useEffect(() => {
    if (activeEvidence?.page_number) {
      setCurrentPage(activeEvidence.page_number);
    }
  }, [activeEvidence]);

  // Count items requiring review
  const reviewableCount = useMemo(() => {
    return findings.filter((f) => f.requires_human_review || f.outcome === 'INCONCLUSIVE' || f.outcome === 'FAIL').length;
  }, [findings]);

  const adjudicatedCount = useMemo(() => Object.keys(adjudications).length, [adjudications]);
  const pendingReviewCount = Math.max(0, reviewableCount - adjudicatedCount);

  // Genuine values (no fabricated defaults)
  const activePageNumber = currentPage;

  const boundingBox = activeEvidence?.bounding_box || null;

  const confidenceDisplay = useMemo(() => {
    if (activeEvidence?.confidence !== null && activeEvidence?.confidence !== undefined) {
      return `${(activeEvidence.confidence * 100).toFixed(1)}%`;
    }
    if (activeEvidence?.extraction_method === 'digital') {
      return 'Digital ground truth (Deterministic)';
    }
    return 'Not available';
  }, [activeEvidence]);

  // Distinct pages present in the extraction metadata
  const availablePages = useMemo(() => {
    const pageSet = new Set<number>();
    if (activePageNumber) pageSet.add(activePageNumber);
    Object.values(extractedFields).forEach((ev) => {
      if (ev.page_number) pageSet.add(ev.page_number);
    });
    if (totalPages && totalPages > 0) {
      for (let p = 1; p <= Math.min(totalPages, 5); p++) {
        pageSet.add(p);
      }
    }
    return Array.from(pageSet).sort((a, b) => a - b);
  }, [activePageNumber, extractedFields, totalPages]);

  const getSeverityBadge = (severity: RuleSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="badge badge-sev-critical badge-pill">● Critical</span>;
      case 'HIGH':
        return <span className="badge badge-sev-high badge-pill">▲ High</span>;
      case 'MEDIUM':
        return <span className="badge badge-sev-medium badge-pill">■ Medium</span>;
      case 'LOW':
      case 'INFO':
        return <span className="badge badge-sev-low badge-pill">○ Low</span>;
    }
  };

  const getCategoryBadge = (category: FindingCategory) => {
    switch (category) {
      case 'COMPLIANCE':
        return <span className="badge badge-cat-compliance badge-pill">Compliance</span>;
      case 'AUTHENTICITY':
        return <span className="badge badge-cat-authenticity badge-pill">Authenticity</span>;
      case 'PRIVACY':
        return <span className="badge badge-cat-privacy badge-pill">Privacy</span>;
      case 'CONSISTENCY':
        return <span className="badge badge-cat-consistency badge-pill">Consistency</span>;
    }
  };

  const getStatusBadge = (outcome: RuleOutcome) => {
    switch (outcome) {
      case 'PASS':
        return (
          <span className="badge badge-pass badge-pill">
            <Check size={11} style={{ strokeWidth: 3 }} />
            Passed
          </span>
        );
      case 'FAIL':
        return (
          <span className="badge badge-fail badge-pill">
            <XCircle size={11} />
            Failed
          </span>
        );
      case 'INCONCLUSIVE':
        return (
          <span className="badge badge-inconclusive badge-pill">
            <AlertTriangle size={11} />
            Inconclusive
          </span>
        );
    }
  };

  const getAdjudicatedOutcomeView = (finding: NormalizedFinding, decided?: AdjudicationRecord) => {
    if (!decided) {
      return getStatusBadge(finding.outcome);
    }

    switch (decided.decision) {
      case 'CONFIRMED_VALID':
        return (
          <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }}>
            <span
              className="badge badge-pass badge-pill"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              title={`Adjudication: Exception Accepted by Regulatory Officer (Original validation outcome: ${finding.outcome})`}
            >
              <Check size={11} style={{ strokeWidth: 3 }} />
              <span>Exception Accepted</span>
            </span>
            <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', lineHeight: '1.2' }}>
              Orig: {finding.outcome} (Overridden)
            </span>
          </div>
        );
      case 'REJECTED_NON_COMPLIANT':
        return (
          <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }}>
            <span
              className="badge badge-fail badge-pill"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              title={`Adjudication: Flagged Non-Compliant by Regulatory Officer (Original validation outcome: ${finding.outcome})`}
            >
              <XCircle size={11} />
              <span>Flagged Non-Compliant</span>
            </span>
            <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', lineHeight: '1.2' }}>
              Orig: {finding.outcome} (Confirmed)
            </span>
          </div>
        );
      case 'REQUEST_CLARIFICATION':
        return (
          <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }}>
            <span
              className="badge badge-inconclusive badge-pill"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              title={`Adjudication: Clarification Requested from Institution (Original validation outcome: ${finding.outcome})`}
            >
              <AlertTriangle size={11} />
              <span>Clarification Pending</span>
            </span>
            <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', lineHeight: '1.2' }}>
              Orig: {finding.outcome} (Clarifying)
            </span>
          </div>
        );
    }
  };

  const getRowDotColor = (f: NormalizedFinding) => {
    const decided = adjudications[f.finding_id];
    if (decided) {
      if (decided.decision === 'CONFIRMED_VALID') return 'var(--color-pass-dot)';
      if (decided.decision === 'REJECTED_NON_COMPLIANT') return 'var(--color-fail-dot)';
      if (decided.decision === 'REQUEST_CLARIFICATION') return 'var(--color-inconclusive-dot)';
    }
    if (f.outcome === 'FAIL') return 'var(--color-fail-dot)';
    if (f.outcome === 'INCONCLUSIVE') return 'var(--color-inconclusive-dot)';
    if (f.category === 'AUTHENTICITY') return '#3b82f6';
    if (f.category === 'PRIVACY') return '#06b6d4';
    return 'var(--color-pass-dot)';
  };

  return (
    <div>
      {/* Workspace Controls & Filters */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '16px',
      }}>
        {/* Left: Search and Dropdowns */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Search box */}
          <div style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            minWidth: '260px',
          }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search rule name, field or status..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '7px 12px 7px 32px',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-surface)',
                fontSize: '12.5px',
                color: 'var(--text-primary)',
              }}
            />
          </div>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            style={{
              padding: '7px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-surface)',
              fontSize: '12.5px',
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            <option value="ALL">All Types</option>
            <option value="COMPLIANCE">Compliance</option>
            <option value="AUTHENTICITY">Authenticity</option>
            <option value="PRIVACY">Privacy</option>
            <option value="CONSISTENCY">Consistency</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            style={{
              padding: '7px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-surface)',
              fontSize: '12.5px',
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Outcome Filter */}
          <select
            value={outcomeFilter}
            onChange={(e) => setOutcomeFilter(e.target.value)}
            style={{
              padding: '7px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-surface)',
              fontSize: '12.5px',
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            <option value="ALL">All Outcomes</option>
            {adjudicatedCount > 0 && (
              <option value="ADJUDICATED">Adjudicated in Draft ({adjudicatedCount})</option>
            )}
            <option value="INCONCLUSIVE">Inconclusive</option>
            <option value="FAIL">Failed</option>
            <option value="PASS">Passed</option>
          </select>
        </div>

        {/* Right: Toggle & Review All CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Needs judgment switch */}
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <input
              type="checkbox"
              checked={needsJudgmentOnly}
              onChange={(e) => setNeedsJudgmentOnly(e.target.checked)}
              style={{
                accentColor: 'var(--color-brand)',
                cursor: 'pointer',
                width: '15px',
                height: '15px',
              }}
            />
            <span>Needs my judgment only</span>
          </label>

          {/* Review All button */}
          <button
            onClick={onOpenReviewAll}
            className="btn btn-brand"
            style={{ padding: '7px 16px', fontSize: '12.5px' }}
          >
            <SlidersHorizontal size={14} />
            <span>
              {pendingReviewCount > 0
                ? `Review All (${pendingReviewCount} pending)`
                : `Review All (${adjudicatedCount} in draft)`}
            </span>
          </button>
        </div>
      </div>

      {/* Main Split Layout: Table (Left) + Evidence Inspector (Right) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.4fr) minmax(420px, 1fr)',
        gap: '20px',
        alignItems: 'start',
      }}>
        {/* Left: Dense Findings Table */}
        <div className="surface-card" style={{ overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="ledger-table">
              <thead>
                <tr>
                  <th style={{ width: '38px', textAlign: 'center' }}>#</th>
                  <th>Rule & Code</th>
                  <th style={{ width: '100px' }}>Category</th>
                  <th style={{ width: '90px' }}>Severity</th>
                  <th style={{ width: '110px' }}>Outcome</th>
                  <th style={{ width: '80px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredFindings.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No verification findings match the current filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredFindings.map((f, index) => {
                    const isSelected = activeFinding?.finding_id === f.finding_id;
                    const decided = adjudications[f.finding_id];
                    const isReviewable = f.requires_human_review || f.outcome === 'INCONCLUSIVE' || f.outcome === 'FAIL';

                    return (
                      <tr
                        key={f.finding_id}
                        className={isSelected ? 'active-row' : ''}
                        onClick={() => setSelectedFindingId(f.finding_id)}
                        style={{ cursor: 'pointer' }}
                      >
                        {/* Dot indicator & row number */}
                        <td style={{ textAlign: 'center', verticalAlign: 'middle' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}>
                            <span style={{
                              width: '7px',
                              height: '7px',
                              borderRadius: '50%',
                              backgroundColor: getRowDotColor(f),
                              display: 'inline-block',
                            }} />
                            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600' }}>
                              {index + 1}
                            </span>
                          </div>
                        </td>

                        {/* Rule Name (Prominent) & Rule ID (Secondary Monospace) */}
                        <td>
                          <div style={{ fontWeight: '600', color: 'var(--text-primary)', fontSize: '12.5px', lineHeight: '1.25' }}>
                            {f.rule_name}
                          </div>
                          <div className="code-mono" style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                            {f.rule_id}
                          </div>
                          {decided && (
                            <div style={{
                              marginTop: '4px',
                              fontSize: '10.5px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontWeight: '600',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              backgroundColor:
                                decided.decision === 'CONFIRMED_VALID'
                                  ? 'var(--color-pass-bg)'
                                  : decided.decision === 'REJECTED_NON_COMPLIANT'
                                  ? 'var(--color-fail-bg)'
                                  : 'var(--color-inconclusive-bg)',
                              color:
                                decided.decision === 'CONFIRMED_VALID'
                                  ? 'var(--color-pass-text)'
                                  : decided.decision === 'REJECTED_NON_COMPLIANT'
                                  ? 'var(--color-fail-text)'
                                  : 'var(--color-inconclusive-text)',
                              border: `1px solid ${
                                decided.decision === 'CONFIRMED_VALID'
                                  ? 'var(--color-pass-border)'
                                  : decided.decision === 'REJECTED_NON_COMPLIANT'
                                  ? 'var(--color-fail-border)'
                                  : 'var(--color-inconclusive-border)'
                              }`,
                            }}>
                              {decided.decision === 'CONFIRMED_VALID' ? (
                                <Check size={10} style={{ strokeWidth: 3 }} />
                              ) : decided.decision === 'REJECTED_NON_COMPLIANT' ? (
                                <XCircle size={10} />
                              ) : (
                                <AlertTriangle size={10} />
                              )}
                              <span>
                                {decided.decision === 'CONFIRMED_VALID' && 'Exception Validated'}
                                {decided.decision === 'REJECTED_NON_COMPLIANT' && 'Non-Compliant'}
                                {decided.decision === 'REQUEST_CLARIFICATION' && 'Clarification Req.'}
                                {decided.notes ? ` — "${decided.notes.length > 28 ? `${decided.notes.substring(0, 28)}...` : decided.notes}"` : ''}
                              </span>
                            </div>
                          )}
                        </td>

                        {/* Category */}
                        <td>
                          {getCategoryBadge(f.category)}
                        </td>

                        {/* Severity */}
                        <td>
                          {getSeverityBadge(f.severity)}
                        </td>

                        {/* Outcome / Status */}
                        <td>
                          {getAdjudicatedOutcomeView(f, decided)}
                        </td>

                        {/* Streamlined Action Button */}
                        <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                          {decided ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onOpenAdjudicationForFinding) {
                                  onOpenAdjudicationForFinding(f.finding_id);
                                } else if (onOpenReviewAll) {
                                  onOpenReviewAll();
                                }
                              }}
                              className="btn btn-secondary btn-sm"
                              style={{ padding: '3px 8px', fontSize: '11px', fontWeight: '600' }}
                              title="Edit active adjudication decision in session draft"
                            >
                              <span>Edit Draft</span>
                              <span>✎</span>
                            </button>
                          ) : isReviewable ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onOpenAdjudicationForFinding) {
                                  onOpenAdjudicationForFinding(f.finding_id);
                                } else if (onOpenReviewAll) {
                                  onOpenReviewAll();
                                }
                              }}
                              className="btn btn-outline-amber btn-sm"
                              style={{ padding: '3px 8px', fontSize: '11px', fontWeight: '600' }}
                            >
                              <span>Review</span>
                              <span>→</span>
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedFindingId(f.finding_id);
                              }}
                              className="btn btn-secondary btn-sm"
                              style={{ padding: '3px 7px', fontSize: '11px' }}
                            >
                              <span>Inspect</span>
                              <span>→</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Genuine Evidence Details & Document Inspector Panel */}
        <div className="surface-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Top Panel Controls */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: '10px',
            borderBottom: '1px solid var(--border-subtle)',
          }}>
            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
              Page {currentPage} {totalPages ? `of ${totalPages}` : ''}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {pdfUrl && (
                <div style={{ display: 'flex', gap: '4px', marginRight: '6px' }}>
                  <button
                    type="button"
                    onClick={() => setViewMode('evidence')}
                    className={`btn btn-sm ${viewMode === 'evidence' ? 'btn-brand' : 'btn-secondary'}`}
                    style={{ fontSize: '11px', padding: '2px 7px' }}
                  >
                    Evidence
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('pdf')}
                    className={`btn btn-sm ${viewMode === 'pdf' ? 'btn-brand' : 'btn-secondary'}`}
                    style={{ fontSize: '11px', padding: '2px 7px' }}
                  >
                    PDF
                  </button>
                </div>
              )}

              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="btn btn-secondary btn-sm"
                style={{ padding: '4px 6px' }}
                title="Previous page"
                aria-label="Previous page"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                type="button"
                onClick={() => setCurrentPage((p) => (totalPages ? Math.min(totalPages, p + 1) : p + 1))}
                className="btn btn-secondary btn-sm"
                style={{ padding: '4px 6px' }}
                title="Next page"
                aria-label="Next page"
              >
                <ChevronRight size={14} />
              </button>

              <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--border-color)', margin: '0 4px' }} />

              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.max(50, z - 10))}
                style={{ background: 'none', color: 'var(--text-secondary)', padding: '2px', cursor: 'pointer' }}
                title="Zoom out"
                aria-label="Zoom out"
              >
                <ZoomOut size={14} />
              </button>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', minWidth: '34px', textAlign: 'center' }}>
                {zoomLevel}%
              </span>
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.min(200, z + 10))}
                style={{ background: 'none', color: 'var(--text-secondary)', padding: '2px', cursor: 'pointer' }}
                title="Zoom in"
                aria-label="Zoom in"
              >
                <ZoomIn size={14} />
              </button>
            </div>
          </div>

          {/* Genuine Document / Evidence Viewer Area */}
          {pdfUrl && viewMode === 'pdf' ? (
            /* Real PDF Viewer via browser object embed */
            <div style={{
              height: '320px',
              borderRadius: '6px',
              overflow: 'hidden',
              border: '1px solid var(--border-color)',
            }}>
              <iframe
                src={`${pdfUrl}#page=${currentPage}&zoom=${zoomLevel}&toolbar=0&navpanes=0`}
                title="Real Document PDF View"
                style={{ width: '100%', height: '100%', border: 'none' }}
              />
            </div>
          ) : (
            /* Genuine Evidence Stream Inspector */
            <div style={{
              display: 'grid',
              gridTemplateColumns: availablePages.length > 1 ? '50px 1fr' : '1fr',
              gap: '12px',
              backgroundColor: 'var(--bg-surface-subtle)',
              borderRadius: '6px',
              padding: '12px',
              minHeight: '260px',
              border: '1px solid var(--border-subtle)',
            }}>
              {/* Actual Page Thumbnails if available */}
              {availablePages.length > 1 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {availablePages.map((pNum) => (
                    <div
                      key={pNum}
                      onClick={() => setCurrentPage(pNum)}
                      style={{
                        backgroundColor: 'var(--bg-surface)',
                        border: `1.5px solid ${pNum === activePageNumber ? 'var(--color-amber-accent)' : 'var(--border-color)'}`,
                        borderRadius: '4px',
                        padding: '4px',
                        textAlign: 'center',
                        cursor: 'pointer',
                        boxShadow: pNum === activePageNumber ? '0 0 0 1px var(--color-amber-accent)' : 'none',
                      }}
                    >
                      <div style={{
                        height: '32px',
                        backgroundColor: 'var(--bg-hover)',
                        borderRadius: '2px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '9px',
                        color: 'var(--text-muted)',
                      }}>
                        📄
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px', fontWeight: '600' }}>
                        {pNum}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Genuine Extracted Evidence & Stream Region (NO fake document text) */}
              <div style={{
                backgroundColor: 'var(--bg-surface)',
                borderRadius: '4px',
                padding: '16px',
                boxShadow: 'var(--shadow-card)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                fontSize: '12px',
                lineHeight: '1.5',
              }}>
                <div>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '10px',
                    paddingBottom: '8px',
                    borderBottom: '1px solid var(--border-subtle)',
                    gap: '12px',
                  }}>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', lineHeight: '1.3' }}>
                        {activeFinding?.rule_name || 'Evaluated Rule Evidence'}
                      </div>
                      <div className="code-mono" style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {activeFinding?.rule_id || 'N/A'}
                      </div>
                    </div>
                    <span style={{ fontSize: '10px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      Evidence Inspector
                    </span>
                  </div>

                  {/* Active Officer Adjudication Determination (Session Draft) */}
                  {activeFinding && adjudications[activeFinding.finding_id] && (() => {
                    const adj = adjudications[activeFinding.finding_id];
                    return (
                      <div style={{
                        padding: '10px 12px',
                        borderRadius: '6px',
                        marginBottom: '12px',
                        backgroundColor:
                          adj.decision === 'CONFIRMED_VALID'
                            ? 'var(--color-pass-bg)'
                            : adj.decision === 'REJECTED_NON_COMPLIANT'
                            ? 'var(--color-fail-bg)'
                            : 'var(--color-inconclusive-bg)',
                        border: `1px solid ${
                          adj.decision === 'CONFIRMED_VALID'
                            ? 'var(--color-pass-border)'
                            : adj.decision === 'REJECTED_NON_COMPLIANT'
                            ? 'var(--color-fail-border)'
                            : 'var(--color-inconclusive-border)'
                        }`,
                        fontSize: '12px',
                        color:
                          adj.decision === 'CONFIRMED_VALID'
                            ? 'var(--color-pass-text)'
                            : adj.decision === 'REJECTED_NON_COMPLIANT'
                            ? 'var(--color-fail-text)'
                            : 'var(--color-inconclusive-text)',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: '700' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            {adj.decision === 'CONFIRMED_VALID' ? (
                              <Check size={14} style={{ strokeWidth: 3 }} />
                            ) : adj.decision === 'REJECTED_NON_COMPLIANT' ? (
                              <XCircle size={14} />
                            ) : (
                              <AlertTriangle size={14} />
                            )}
                            <span>
                              {adj.decision === 'CONFIRMED_VALID' && 'Adjudicated: Exception Accepted'}
                              {adj.decision === 'REJECTED_NON_COMPLIANT' && 'Adjudicated: Flagged Non-Compliant'}
                              {adj.decision === 'REQUEST_CLARIFICATION' && 'Adjudicated: Clarification Requested'}
                            </span>
                          </div>
                          <span style={{ fontSize: '10.5px', opacity: 0.85 }}>Session Draft</span>
                        </div>
                        <div style={{ marginTop: '4px', fontSize: '11.5px', opacity: 0.95 }}>
                          Officer Remarks: "{adj.notes}"
                        </div>
                        <div style={{ marginTop: '3px', fontSize: '10.5px', opacity: 0.75 }}>
                          Original rule outcome: <strong>{activeFinding.outcome}</strong> • Timestamp: {adj.timestamp}
                        </div>
                      </div>
                    );
                  })()}

                  {activeEvidence ? (
                    <div>
                      {/* Bounding box highlight frame if real coordinates exist */}
                      {boundingBox ? (
                        <div style={{
                          border: '2px solid #f97316',
                          backgroundColor: 'rgba(251, 146, 60, 0.08)',
                          borderRadius: '4px',
                          padding: '10px',
                          marginBottom: '10px',
                        }}>
                          <div style={{ fontSize: '10px', fontWeight: '700', color: '#c2410c', marginBottom: '4px' }}>
                            BOUNDING BOX [{boundingBox.map((b) => Math.round(b)).join(', ')}] — Page {activeEvidence.page_number || activePageNumber}
                          </div>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                            {activeEvidence.raw_value || String(activeEvidence.normalized_value)}
                          </div>
                        </div>
                      ) : (
                        <div style={{
                          padding: '10px',
                          backgroundColor: 'var(--bg-surface-subtle)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '4px',
                          marginBottom: '10px',
                        }}>
                          <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                            EXTRACTED DIGITAL TEXT SNIPPET
                          </div>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                            {activeEvidence.raw_value || (activeEvidence.normalized_value !== null ? String(activeEvidence.normalized_value) : 'Value not available in stream')}
                          </div>
                        </div>
                      )}

                      <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                        <div>Affected Field: <strong className="code-mono">{activeFinding?.affected_fields?.join(', ') || 'N/A'}</strong></div>
                        <div>Extraction Route: <strong>{activeEvidence.extraction_method || 'digital'}</strong></div>
                        {activeEvidence.uncertainty_reason && (
                          <div style={{ color: '#b45309', marginTop: '4px' }}>
                            Uncertainty Note: {activeEvidence.uncertainty_reason}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '20px 8px', color: 'var(--text-secondary)' }}>
                      <div style={{ fontWeight: '600', color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {activeFinding?.rule_name}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                        {activeFinding?.explanation || 'No rule explanation supplied.'}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        Rule evaluated at document level; no single field bounding box mapped.
                      </div>
                    </div>
                  )}
                </div>

                <div style={{
                  paddingTop: '8px',
                  borderTop: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '10.5px',
                  color: 'var(--text-muted)',
                }}>
                  <span>Document: {documentFilename || 'Active Document'}</span>
                  <span>Page {activePageNumber}</span>
                </div>
              </div>
            </div>
          )}

          {/* Bottom Tabs: Evidence Details / Rule Information / Extracted Value */}
          <div>
            <div style={{
              display: 'flex',
              gap: '16px',
              borderBottom: '1px solid var(--border-subtle)',
              marginBottom: '12px',
            }}>
              <button
                type="button"
                onClick={() => setEvidenceTab('details')}
                style={{
                  padding: '6px 0',
                  fontSize: '12px',
                  fontWeight: evidenceTab === 'details' ? '600' : '500',
                  color: evidenceTab === 'details' ? 'var(--color-brand)' : 'var(--text-secondary)',
                  borderBottom: `2px solid ${evidenceTab === 'details' ? 'var(--color-brand)' : 'transparent'}`,
                  background: 'none',
                  cursor: 'pointer',
                }}
              >
                Evidence Details
              </button>
              <button
                type="button"
                onClick={() => setEvidenceTab('rule')}
                style={{
                  padding: '6px 0',
                  fontSize: '12px',
                  fontWeight: evidenceTab === 'rule' ? '600' : '500',
                  color: evidenceTab === 'rule' ? 'var(--color-brand)' : 'var(--text-secondary)',
                  borderBottom: `2px solid ${evidenceTab === 'rule' ? 'var(--color-brand)' : 'transparent'}`,
                  background: 'none',
                  cursor: 'pointer',
                }}
              >
                Rule Information
              </button>
              <button
                type="button"
                onClick={() => setEvidenceTab('value')}
                style={{
                  padding: '6px 0',
                  fontSize: '12px',
                  fontWeight: evidenceTab === 'value' ? '600' : '500',
                  color: evidenceTab === 'value' ? 'var(--color-brand)' : 'var(--text-secondary)',
                  borderBottom: `2px solid ${evidenceTab === 'value' ? 'var(--color-brand)' : 'transparent'}`,
                  background: 'none',
                  cursor: 'pointer',
                }}
              >
                Extracted Value
              </button>
            </div>

            {/* Tab 1: Evidence Details */}
            {evidenceTab === 'details' && (
              <div style={{
                backgroundColor: 'var(--bg-surface-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <FileText size={18} style={{ color: 'var(--color-amber-accent)', marginTop: '2px' }} />
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
                      {activeEvidence?.page_number ? `Selected region from page ${activeEvidence.page_number}` : 'Digital stream extraction'}
                    </div>
                    <div className="code-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {boundingBox
                        ? `Bounding Box: [${boundingBox.map((b) => Math.round(b)).join(', ')}] (PDF points)`
                        : 'Bounding Box: Not available (Digital Text Stream)'}
                    </div>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Confidence</div>
                  {activeEvidence?.confidence !== null && activeEvidence?.confidence !== undefined ? (
                    <div
                      className={`badge badge-pill ${
                        activeEvidence.confidence >= 0.8
                          ? 'badge-pass'
                          : activeEvidence.confidence >= 0.65
                          ? 'badge-inconclusive'
                          : 'badge-fail'
                      }`}
                      style={{ fontSize: '11px', fontWeight: '700', padding: '2px 8px' }}
                    >
                      {confidenceDisplay}
                    </div>
                  ) : activeEvidence?.extraction_method === 'digital' ? (
                    <div
                      className="badge badge-pill"
                      style={{
                        fontSize: '10.5px',
                        fontWeight: '600',
                        padding: '2px 8px',
                        backgroundColor: 'var(--bg-surface-subtle)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border-color)',
                      }}
                    >
                      {confidenceDisplay}
                    </div>
                  ) : (
                    <div
                      className="badge badge-pill"
                      style={{
                        fontSize: '11px',
                        fontWeight: '600',
                        padding: '2px 8px',
                        backgroundColor: 'var(--bg-surface-subtle)',
                        color: 'var(--text-muted)',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      {confidenceDisplay}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tab 2: Rule Information */}
            {evidenceTab === 'rule' && (
              <div style={{
                backgroundColor: 'var(--bg-surface-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '12px',
                fontSize: '12px',
              }}>
                <div style={{ fontWeight: '600', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  {activeFinding?.rule_name || 'No rule selected'}
                </div>
                <div style={{ color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  {activeFinding?.explanation || 'No explanation available.'}
                </div>
                <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
                  Category: <strong>{activeFinding?.category || 'N/A'}</strong> • Severity: <strong>{activeFinding?.severity || 'N/A'}</strong>
                </div>
              </div>
            )}

            {/* Tab 3: Extracted Value */}
            {evidenceTab === 'value' && (
              <div style={{
                backgroundColor: 'var(--bg-surface-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px',
                fontSize: '11.5px',
              }}>
                {activeFinding?.evidence_values && Object.keys(activeFinding.evidence_values).length > 0 ? (
                  <pre style={{
                    margin: 0,
                    padding: '8px',
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '4px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    color: 'var(--text-primary)',
                    maxHeight: '120px',
                    overflowY: 'auto',
                  }}>
                    {JSON.stringify(activeFinding.evidence_values, null, 2)}
                  </pre>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', padding: '6px' }}>
                    No raw evidence dictionary payload for this deterministic finding.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
