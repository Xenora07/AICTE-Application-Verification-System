/**
 * frontend/src/tests/adjudication.test.mjs
 * Test Suite: Human Review Adjudication Action Flow & State Persistence
 *
 * Verifies:
 * 1. Selecting "Validate Exception", "Flag Non-Compliant", and "Request Clarification".
 * 2. Generating complete AdjudicationRecords with rule details and officer remarks.
 * 3. Saving decisions to the session adjudications dictionary.
 * 4. Preserving adjudications across panel close (isOpen: false) and reopen (isOpen: true).
 * 5. Dashboard confirmation alert formatting identifying selected decision and rule.
 * 6. UI-level session draft boundary (honest limitation: no silent backend loss claims).
 * 7. Regression Coverage: Draft counter updates, remarks preservation, duplicate click idempotency, Done Reviewing.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

const DEFAULT_NOTES = {
  CONFIRMED_VALID: 'Accepted exception based on official stamp and manual cross-verification.',
  REJECTED_NON_COMPLIANT: 'Confirmed regulatory non-compliance; application flagged for remediation.',
  REQUEST_CLARIFICATION: 'Issued formal clarification request to institution regarding evidence discrepancy.',
};

// Derived Display Helpers matching ValidationFindingsList.tsx & ReviewerSummaryBanner.tsx
function getAdjudicatedOutcomeView(finding, decided) {
  if (!decided) {
    return {
      statusBadge: finding.outcome === 'PASS' ? 'Passed' : finding.outcome === 'FAIL' ? 'Failed' : 'Inconclusive',
      badgeClass: finding.outcome === 'PASS' ? 'badge-pass' : finding.outcome === 'FAIL' ? 'badge-fail' : 'badge-inconclusive',
      isOverridden: false,
      originalOutcome: finding.outcome,
      displayText: finding.outcome === 'PASS' ? 'Passed' : finding.outcome === 'FAIL' ? 'Failed' : 'Inconclusive',
    };
  }

  switch (decided.decision) {
    case 'CONFIRMED_VALID':
      return {
        statusBadge: 'Exception Accepted',
        badgeClass: 'badge-pass',
        isOverridden: true,
        subtext: `Orig: ${finding.outcome} (Overridden)`,
        originalOutcome: finding.outcome,
        displayText: 'Exception Accepted',
      };
    case 'REJECTED_NON_COMPLIANT':
      return {
        statusBadge: 'Flagged Non-Compliant',
        badgeClass: 'badge-fail',
        isOverridden: true,
        subtext: `Orig: ${finding.outcome} (Confirmed)`,
        originalOutcome: finding.outcome,
        displayText: 'Flagged Non-Compliant',
      };
    case 'REQUEST_CLARIFICATION':
      return {
        statusBadge: 'Clarification Pending',
        badgeClass: 'badge-inconclusive',
        isOverridden: true,
        subtext: `Orig: ${finding.outcome} (Clarifying)`,
        originalOutcome: finding.outcome,
        displayText: 'Clarification Pending',
      };
  }
}

function getStatusBadgeConfig(summary, adjudications = {}) {
  const adjudicatedCount = Object.keys(adjudications).length;
  const totalReviewable = summary.inconclusive_rules + summary.failed_rules;
  const pendingReviewCount = Math.max(0, totalReviewable - adjudicatedCount);

  if (totalReviewable > 0 && pendingReviewCount === 0) {
    const hasRejected = Object.values(adjudications).some((a) => a.decision === 'REJECTED_NON_COMPLIANT');
    const hasClarification = Object.values(adjudications).some((a) => a.decision === 'REQUEST_CLARIFICATION');

    if (hasRejected) {
      return {
        title: 'NON-COMPLIANT (ADJUDICATED)',
        subtitle: `All ${totalReviewable} finding(s) reviewed • Non-compliance confirmed in session draft`,
      };
    }
    if (hasClarification) {
      return {
        title: 'CLARIFICATION PENDING (ADJUDICATED)',
        subtitle: `All ${totalReviewable} finding(s) reviewed • Clarification requested in session draft`,
      };
    }
    return {
      title: 'EXCEPTIONS ACCEPTED (ADJUDICATED)',
      subtitle: `All ${totalReviewable} finding(s) reviewed • Exceptions confirmed by regulatory officer (Session Draft)`,
    };
  }

  return {
    title: 'HUMAN REVIEW REQUIRED',
    subtitle: `${summary.inconclusive_rules} finding(s) require regulatory adjudication`,
  };
}

// Simulated state manager representing App.tsx & HumanReviewDrawer.tsx contract
class AdjudicationWorkflowManager {
  constructor() {
    this.adjudications = {};
    this.isDrawerOpen = false;
    this.adjudicationAlert = null;
    this.activeFindingIndex = 0;
  }

  openDrawer(initialFindingId = null, reviewableFindings = sampleFindings) {
    this.isDrawerOpen = true;
    if (initialFindingId) {
      const idx = reviewableFindings.findIndex((f) => f.finding_id === initialFindingId);
      this.activeFindingIndex = idx !== -1 ? idx : 0;
    } else {
      this.activeFindingIndex = 0;
    }
  }

  getActiveFinding(reviewableFindings = sampleFindings) {
    return reviewableFindings[this.activeFindingIndex];
  }

  closeDrawer() {
    this.isDrawerOpen = false;
  }

  selectDecision(finding, decision, customNote = '') {
    const defaultNote = DEFAULT_NOTES[decision] || 'Adjudicated by regulatory officer.';
    const isOtherDefaultNote = Object.values(DEFAULT_NOTES).includes(customNote.trim());

    // If remarks are empty OR match any action's default note, use the new decision's default note.
    // Otherwise preserve the officer's custom typed note.
    const noteToSave = (!customNote.trim() || isOtherDefaultNote)
      ? defaultNote
      : customNote.trim();

    const record = {
      findingId: finding.finding_id,
      ruleId: finding.rule_id,
      ruleName: finding.rule_name,
      decision,
      notes: noteToSave,
      timestamp: new Date().toLocaleTimeString(),
    };

    // Save into state
    this.saveAdjudication(record);
    return record;
  }

  saveAdjudication(record) {
    this.adjudications[record.findingId] = record;
    this.adjudicationAlert = `Action Recorded: "${record.decision}" for ${record.ruleId} (${record.ruleName}) — "${record.notes}" (Session Draft)`;
  }

  saveAndClose(finding, currentDecision, currentNoteInput) {
    if (finding && currentDecision) {
      this.saveAdjudication({
        ...currentDecision,
        notes: currentNoteInput.trim() || currentDecision.notes,
        timestamp: new Date().toLocaleTimeString(),
      });
    }
    this.closeDrawer();
  }

  getDecisionForFinding(findingId) {
    return this.adjudications[findingId];
  }

  getDraftCount(reviewableFindings = sampleFindings) {
    return reviewableFindings.filter((f) => !!this.adjudications[f.finding_id]).length;
  }
}

// Sample findings from verification pipeline
const sampleFindings = [
  {
    finding_id: 'FIND_EOA_001',
    rule_id: 'REG_APPROVAL_STATUS',
    rule_name: 'AICTE Approval Status Check',
    outcome: 'FAIL',
    severity: 'CRITICAL',
    requires_human_review: true,
    explanation: 'Document status indicates conditional/pending approval.',
    affected_fields: ['approval_status'],
  },
  {
    finding_id: 'FIND_EOA_002',
    rule_id: 'VAL_LAND_AREA_INCONCL',
    rule_name: 'Campus Land Area Compliance',
    outcome: 'INCONCLUSIVE',
    severity: 'MEDIUM',
    requires_human_review: true,
    explanation: 'Land area unit ambiguous between acres and hectares.',
    affected_fields: ['land_area_acres'],
  },
];

describe('Human Review Adjudication Panel - Action Flow Tests', () => {
  it('1. should record "CONFIRMED_VALID" (Validate Exception) with default note', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    const record = manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID');

    assert.equal(record.decision, 'CONFIRMED_VALID');
    assert.equal(record.ruleId, 'REG_APPROVAL_STATUS');
    assert.match(record.notes, /Accepted exception/);
    assert.equal(manager.adjudications['FIND_EOA_001'].decision, 'CONFIRMED_VALID');
  });

  it('2. should record "REJECTED_NON_COMPLIANT" (Flag Non-Compliant) with default note', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    const record = manager.selectDecision(sampleFindings[0], 'REJECTED_NON_COMPLIANT');

    assert.equal(record.decision, 'REJECTED_NON_COMPLIANT');
    assert.equal(record.ruleId, 'REG_APPROVAL_STATUS');
    assert.match(record.notes, /Confirmed regulatory non-compliance/);
    assert.equal(manager.adjudications['FIND_EOA_001'].decision, 'REJECTED_NON_COMPLIANT');
  });

  it('3. should record "REQUEST_CLARIFICATION" (Request Clarification) with custom officer note', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    const customRemarks = 'Official land mutation deed page 3 is illegible; request high-res scanned upload.';
    const record = manager.selectDecision(sampleFindings[1], 'REQUEST_CLARIFICATION', customRemarks);

    assert.equal(record.decision, 'REQUEST_CLARIFICATION');
    assert.equal(record.ruleId, 'VAL_LAND_AREA_INCONCL');
    assert.equal(record.notes, customRemarks);
    assert.equal(manager.adjudications['FIND_EOA_002'].decision, 'REQUEST_CLARIFICATION');
  });

  it('4. should generate dashboard confirmation alert identifying decision and rule', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    manager.selectDecision(sampleFindings[1], 'REQUEST_CLARIFICATION', 'Need surveyor report.');

    assert.ok(manager.adjudicationAlert);
    assert.match(manager.adjudicationAlert, /Action Recorded: "REQUEST_CLARIFICATION"/);
    assert.match(manager.adjudicationAlert, /VAL_LAND_AREA_INCONCL/);
    assert.match(manager.adjudicationAlert, /\(Session Draft\)/);
  });

  it('5. should preserve recorded decisions when closing the panel', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();
    assert.equal(manager.isDrawerOpen, true);

    // Make decision
    manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID', 'Override verified by Regional Officer.');

    // Save & Close Panel
    const current = manager.getDecisionForFinding('FIND_EOA_001');
    manager.saveAndClose(sampleFindings[0], current, current.notes);

    assert.equal(manager.isDrawerOpen, false);
    // Decision must NOT be lost on close
    assert.ok(manager.adjudications['FIND_EOA_001']);
    assert.equal(manager.adjudications['FIND_EOA_001'].decision, 'CONFIRMED_VALID');
    assert.equal(manager.adjudications['FIND_EOA_001'].notes, 'Override verified by Regional Officer.');
  });

  it('6. should restore recorded decision and notes when reopening the panel', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    // Select Request Clarification
    manager.selectDecision(sampleFindings[1], 'REQUEST_CLARIFICATION', 'Survey coordinates required.');
    manager.closeDrawer();
    assert.equal(manager.isDrawerOpen, false);

    // Reopen drawer
    manager.openDrawer();
    assert.equal(manager.isDrawerOpen, true);

    // Retrieve state as HumanReviewDrawer does on mount/selection
    const restoredDecision = manager.getDecisionForFinding('FIND_EOA_002');
    assert.ok(restoredDecision, 'Decision must be present upon reopening');
    assert.equal(restoredDecision.decision, 'REQUEST_CLARIFICATION');
    assert.equal(restoredDecision.ruleId, 'VAL_LAND_AREA_INCONCL');
    assert.equal(restoredDecision.notes, 'Survey coordinates required.');
  });

  it('7. should independently maintain decisions across multiple findings', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID', 'Stamp verified.');
    manager.selectDecision(sampleFindings[1], 'REQUEST_CLARIFICATION', 'Missing annexure.');

    manager.closeDrawer();

    assert.equal(Object.keys(manager.adjudications).length, 2);
    assert.equal(manager.getDecisionForFinding('FIND_EOA_001').decision, 'CONFIRMED_VALID');
    assert.equal(manager.getDecisionForFinding('FIND_EOA_002').decision, 'REQUEST_CLARIFICATION');

    manager.openDrawer();
    assert.equal(manager.getDecisionForFinding('FIND_EOA_001').decision, 'CONFIRMED_VALID');
    assert.equal(manager.getDecisionForFinding('FIND_EOA_002').decision, 'REQUEST_CLARIFICATION');
  });

  it('8. should update existing decision and preserve latest notes upon saveAndClose', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    // First action: Request Clarification
    manager.selectDecision(sampleFindings[0], 'REQUEST_CLARIFICATION', 'Initial query');
    assert.equal(manager.getDecisionForFinding('FIND_EOA_001').decision, 'REQUEST_CLARIFICATION');

    // Change action to Flag Non-Compliant with new notes
    const updated = manager.selectDecision(sampleFindings[0], 'REJECTED_NON_COMPLIANT', 'After re-reading, definite failure.');

    // Save and close
    manager.saveAndClose(sampleFindings[0], updated, 'Final determination: non-compliant.');

    assert.equal(manager.isDrawerOpen, false);
    assert.equal(manager.getDecisionForFinding('FIND_EOA_001').decision, 'REJECTED_NON_COMPLIANT');
    assert.equal(manager.getDecisionForFinding('FIND_EOA_001').notes, 'Final determination: non-compliant.');
  });

  it('9. should open drawer at specific finding index when initialFindingId is passed', () => {
    const manager = new AdjudicationWorkflowManager();

    // Clicking Review -> on the second reviewable finding (FIND_EOA_002)
    manager.openDrawer('FIND_EOA_002', sampleFindings);

    assert.equal(manager.isDrawerOpen, true);
    assert.equal(manager.activeFindingIndex, 1);
    const active = manager.getActiveFinding(sampleFindings);
    assert.equal(active.finding_id, 'FIND_EOA_002');
    assert.equal(active.rule_id, 'VAL_LAND_AREA_INCONCL');

    // Recording decision records against FIND_EOA_002, NOT index 0 (FIND_EOA_001)
    manager.selectDecision(active, 'REQUEST_CLARIFICATION', 'Survey coordinates needed.');
    assert.equal(manager.getDecisionForFinding('FIND_EOA_002').decision, 'REQUEST_CLARIFICATION');
    assert.equal(manager.getDecisionForFinding('FIND_EOA_001'), undefined);
  });

  it('10. should safely fallback to index 0 if initialFindingId is unknown or omitted', () => {
    const manager = new AdjudicationWorkflowManager();

    // Omitted initialFindingId (e.g. from Review All CTA)
    manager.openDrawer(null, sampleFindings);
    assert.equal(manager.activeFindingIndex, 0);
    assert.equal(manager.getActiveFinding(sampleFindings).finding_id, 'FIND_EOA_001');

    // Unknown or stale initialFindingId
    manager.openDrawer('NON_EXISTENT_FINDING', sampleFindings);
    assert.equal(manager.activeFindingIndex, 0);
    assert.equal(manager.getActiveFinding(sampleFindings).finding_id, 'FIND_EOA_001');
  });

  it('11. should format document types and field keys to human-readable labels while preserving raw identifiers', () => {
    const docTypeMap = {
      aicte_eoa: 'AICTE EoA',
      aicte_mandatory_disclosure: 'Mandatory Disclosure',
      naac_certificate: 'NAAC Certificate',
      nba_accreditation: 'NBA Accreditation',
    };
    assert.equal(docTypeMap['aicte_eoa'], 'AICTE EoA');
    assert.equal(docTypeMap['aicte_mandatory_disclosure'], 'Mandatory Disclosure');

    const formatFieldKey = (key) => {
      const fieldLabels = {
        academic_year: 'Academic Year',
        academic_year_start: 'Academic Year Start',
        academic_year_end: 'Academic Year End',
        application_id: 'Application ID',
        permanent_institute_id: 'Permanent Institute ID',
        institution_name: 'Institution Name',
      };
      return fieldLabels[key] || key.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    };

    assert.equal(formatFieldKey('permanent_institute_id'), 'Permanent Institute ID');
    assert.equal(formatFieldKey('academic_year_start'), 'Academic Year Start');
    assert.equal(formatFieldKey('unknown_custom_field'), 'Unknown Custom Field');
  });

  // ============================================================================
  // Extended Regression Tests for SIH26261 Action Workflow Requirements
  // ============================================================================

  it('12. should immediately and accurately update draft counter when actions are recorded', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer(null, sampleFindings);

    // Initial draft count must be 0 of 2
    assert.equal(manager.getDraftCount(sampleFindings), 0);

    // Record decision on finding 0 (1 of 2)
    manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID');
    assert.equal(manager.getDraftCount(sampleFindings), 1);

    // Record decision on finding 1 (2 of 2)
    manager.selectDecision(sampleFindings[1], 'REJECTED_NON_COMPLIANT');
    assert.equal(manager.getDraftCount(sampleFindings), 2);
  });

  it('13. should ensure custom officer audit remarks are retained with the chosen decision', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    const specificRemark = 'Clause 4.2 exemption certified by AICTE Regional Director in letter Ref #RD-2026-901.';
    const record = manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID', specificRemark);

    assert.equal(record.notes, specificRemark);
    assert.equal(manager.getDecisionForFinding('FIND_EOA_001').notes, specificRemark);
  });

  it('14. should switch default notes when officer changes decision without custom remarks', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    // 1. First selects Validate Exception (gets CONFIRMED_VALID default note)
    const rec1 = manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID');
    assert.match(rec1.notes, /Accepted exception/);

    // 2. Changes mind to Flag Non-Compliant without custom note (must get REJECTED_NON_COMPLIANT default note)
    const rec2 = manager.selectDecision(sampleFindings[0], 'REJECTED_NON_COMPLIANT', rec1.notes);
    assert.match(rec2.notes, /Confirmed regulatory non-compliance/);

    // 3. Changes mind to Request Clarification (must get REQUEST_CLARIFICATION default note)
    const rec3 = manager.selectDecision(sampleFindings[0], 'REQUEST_CLARIFICATION', rec2.notes);
    assert.match(rec3.notes, /Issued formal clarification request/);
  });

  it('15. should prevent duplicate adjudication records upon repeated clicks of same or different actions', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer();

    // Click Validate Exception 5 times
    manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID');
    manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID');
    manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID');
    manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID');
    manager.selectDecision(sampleFindings[0], 'CONFIRMED_VALID');

    // Must still contain exactly 1 entry for FIND_EOA_001 and 1 total key
    assert.equal(Object.keys(manager.adjudications).length, 1);
    assert.equal(manager.getDraftCount(sampleFindings), 1);
    assert.equal(manager.getDecisionForFinding('FIND_EOA_001').decision, 'CONFIRMED_VALID');
  });

  it('16. should behave consistently with Done Reviewing: persists draft determinations and closes panel', () => {
    const manager = new AdjudicationWorkflowManager();
    manager.openDrawer('FIND_EOA_001', sampleFindings);
    assert.equal(manager.isDrawerOpen, true);

    const rec = manager.selectDecision(sampleFindings[0], 'REQUEST_CLARIFICATION', 'Preliminary note');

    // Officer refines remark right before clicking Done Reviewing
    const refinedRemark = 'Final refined note: submit audited balance sheet page 4.';
    manager.saveAndClose(sampleFindings[0], rec, refinedRemark);

    assert.equal(manager.isDrawerOpen, false);
    const finalStored = manager.getDecisionForFinding('FIND_EOA_001');
    assert.equal(finalStored.decision, 'REQUEST_CLARIFICATION');
    assert.equal(finalStored.notes, refinedRemark);
    assert.equal(manager.getDraftCount(sampleFindings), 1);
  });

  it('17. should display "Exception Accepted" with overridden status on main findings view after Done Reviewing Validate Exception', () => {
    const manager = new AdjudicationWorkflowManager();
    const finding = sampleFindings[1]; // RULE_REQ_ACADEMIC_YEAR / VAL_LAND_AREA_INCONCL (INCONCLUSIVE)
    assert.equal(finding.outcome, 'INCONCLUSIVE');

    // Before adjudication: displays original inconclusive badge
    const initialView = getAdjudicatedOutcomeView(finding, manager.getDecisionForFinding(finding.finding_id));
    assert.equal(initialView.displayText, 'Inconclusive');
    assert.equal(initialView.isOverridden, false);

    // Open drawer, select Validate Exception, click Done Reviewing
    manager.openDrawer(finding.finding_id, sampleFindings);
    const rec = manager.selectDecision(finding, 'CONFIRMED_VALID', 'Verified official surveyor stamp in Annexure II');
    manager.saveAndClose(finding, rec, rec.notes);

    // Drawer closes and commits to state
    assert.equal(manager.isDrawerOpen, false);
    const decision = manager.getDecisionForFinding(finding.finding_id);
    assert.ok(decision);

    // Main findings table outcome column reflects adjudication
    const adjudicatedView = getAdjudicatedOutcomeView(finding, decision);
    assert.equal(adjudicatedView.displayText, 'Exception Accepted');
    assert.equal(adjudicatedView.badgeClass, 'badge-pass');
    assert.equal(adjudicatedView.isOverridden, true);
    assert.equal(adjudicatedView.subtext, 'Orig: INCONCLUSIVE (Overridden)');
    assert.equal(adjudicatedView.originalOutcome, 'INCONCLUSIVE');

    // Reviewer summary banner reflects adjudicated status
    const summaryView = getStatusBadgeConfig({ inconclusive_rules: 1, failed_rules: 0 }, manager.adjudications);
    assert.equal(summaryView.title, 'EXCEPTIONS ACCEPTED (ADJUDICATED)');
    assert.match(summaryView.subtitle, /Exceptions confirmed by regulatory officer/);
  });

  it('18. should display "Flagged Non-Compliant" distinctly from original outcome after Done Reviewing Flag Non-Compliant', () => {
    const manager = new AdjudicationWorkflowManager();
    const finding = sampleFindings[1]; // INCONCLUSIVE finding

    manager.openDrawer(finding.finding_id, sampleFindings);
    const rec = manager.selectDecision(finding, 'REJECTED_NON_COMPLIANT', 'Insufficient land shortfall exceeds 15%');
    manager.saveAndClose(finding, rec, rec.notes);

    assert.equal(manager.isDrawerOpen, false);
    const decision = manager.getDecisionForFinding(finding.finding_id);

    const adjudicatedView = getAdjudicatedOutcomeView(finding, decision);
    assert.equal(adjudicatedView.displayText, 'Flagged Non-Compliant');
    assert.equal(adjudicatedView.badgeClass, 'badge-fail');
    assert.equal(adjudicatedView.isOverridden, true);
    assert.equal(adjudicatedView.subtext, 'Orig: INCONCLUSIVE (Confirmed)');

    // Summary banner reflects non-compliance
    const summaryView = getStatusBadgeConfig({ inconclusive_rules: 1, failed_rules: 0 }, manager.adjudications);
    assert.equal(summaryView.title, 'NON-COMPLIANT (ADJUDICATED)');
    assert.match(summaryView.subtitle, /Non-compliance confirmed/);
  });

  it('19. should display "Clarification Pending" after Done Reviewing Request Clarification', () => {
    const manager = new AdjudicationWorkflowManager();
    const finding = sampleFindings[1]; // INCONCLUSIVE finding

    manager.openDrawer(finding.finding_id, sampleFindings);
    const rec = manager.selectDecision(finding, 'REQUEST_CLARIFICATION', 'Upload latest municipal mutation deed');
    manager.saveAndClose(finding, rec, rec.notes);

    assert.equal(manager.isDrawerOpen, false);
    const decision = manager.getDecisionForFinding(finding.finding_id);

    const adjudicatedView = getAdjudicatedOutcomeView(finding, decision);
    assert.equal(adjudicatedView.displayText, 'Clarification Pending');
    assert.equal(adjudicatedView.badgeClass, 'badge-inconclusive');
    assert.equal(adjudicatedView.isOverridden, true);
    assert.equal(adjudicatedView.subtext, 'Orig: INCONCLUSIVE (Clarifying)');

    // Summary banner reflects pending clarification
    const summaryView = getStatusBadgeConfig({ inconclusive_rules: 1, failed_rules: 0 }, manager.adjudications);
    assert.equal(summaryView.title, 'CLARIFICATION PENDING (ADJUDICATED)');
    assert.match(summaryView.subtitle, /Clarification requested/);
  });

  it('20. should retain decision and remarks when reopening drawer after Done Reviewing', () => {
    const manager = new AdjudicationWorkflowManager();
    const finding = sampleFindings[0];

    // First review session
    manager.openDrawer(finding.finding_id, sampleFindings);
    const customNote = 'NOC validated against regional director database record #4982.';
    const rec = manager.selectDecision(finding, 'CONFIRMED_VALID', customNote);
    manager.saveAndClose(finding, rec, customNote);
    assert.equal(manager.isDrawerOpen, false);

    // Reopen drawer
    manager.openDrawer(finding.finding_id, sampleFindings);
    assert.equal(manager.isDrawerOpen, true);
    const restored = manager.getDecisionForFinding(finding.finding_id);
    assert.equal(restored.decision, 'CONFIRMED_VALID');
    assert.equal(restored.notes, customNote);
    assert.equal(manager.getDraftCount(sampleFindings), 1);
  });

  it('21. should ensure original validation outcome and evidence are not destroyed or misrepresented', () => {
    const manager = new AdjudicationWorkflowManager();
    const finding = { ...sampleFindings[1] }; // Shallow copy

    manager.openDrawer(finding.finding_id, sampleFindings);
    const rec = manager.selectDecision(finding, 'CONFIRMED_VALID', 'Accepted exception');
    manager.saveAndClose(finding, rec, rec.notes);

    // Original finding data structure must not be mutated into PASS
    assert.equal(finding.outcome, 'INCONCLUSIVE');
    assert.equal(finding.rule_id, 'VAL_LAND_AREA_INCONCL');
    assert.deepEqual(finding.affected_fields, ['land_area_acres']);

    // Derived display clearly marks it as an override without pretending it passed natively
    const adjudicatedView = getAdjudicatedOutcomeView(finding, manager.getDecisionForFinding(finding.finding_id));
    assert.equal(adjudicatedView.displayText, 'Exception Accepted');
    assert.equal(adjudicatedView.originalOutcome, 'INCONCLUSIVE');
    assert.ok(adjudicatedView.subtext.includes('Overridden'));
  });

  it('22. should verify unrelated findings remain completely unchanged', () => {
    const manager = new AdjudicationWorkflowManager();
    const findingToAdjudicate = sampleFindings[0];
    const unrelatedFinding = sampleFindings[1];

    // Adjudicate only finding 0
    manager.openDrawer(findingToAdjudicate.finding_id, sampleFindings);
    const rec = manager.selectDecision(findingToAdjudicate, 'CONFIRMED_VALID');
    manager.saveAndClose(findingToAdjudicate, rec, rec.notes);

    // Finding 0 has an adjudication
    assert.ok(manager.getDecisionForFinding(findingToAdjudicate.finding_id));
    const view0 = getAdjudicatedOutcomeView(findingToAdjudicate, manager.getDecisionForFinding(findingToAdjudicate.finding_id));
    assert.equal(view0.isOverridden, true);

    // Finding 1 MUST have no adjudication and unchanged original view
    assert.equal(manager.getDecisionForFinding(unrelatedFinding.finding_id), undefined);
    const view1 = getAdjudicatedOutcomeView(unrelatedFinding, manager.getDecisionForFinding(unrelatedFinding.finding_id));
    assert.equal(view1.isOverridden, false);
    assert.equal(view1.displayText, 'Inconclusive');
    assert.equal(view1.originalOutcome, 'INCONCLUSIVE');
    assert.equal(manager.getDraftCount(sampleFindings), 1);
  });
});
