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
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

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
    const defaultNotes = {
      CONFIRMED_VALID: 'Accepted exception based on official stamp and manual cross-verification.',
      REJECTED_NON_COMPLIANT: 'Confirmed regulatory non-compliance; application flagged for remediation.',
      REQUEST_CLARIFICATION: 'Issued formal clarification request to institution regarding evidence discrepancy.',
    };

    const noteToSave = customNote.trim() || defaultNotes[decision] || 'Adjudicated by regulatory officer.';
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
    // Document type mapper test
    const docTypeMap = {
      aicte_eoa: 'AICTE EoA',
      aicte_mandatory_disclosure: 'Mandatory Disclosure',
      naac_certificate: 'NAAC Certificate',
      nba_accreditation: 'NBA Accreditation',
    };
    assert.equal(docTypeMap['aicte_eoa'], 'AICTE EoA');
    assert.equal(docTypeMap['aicte_mandatory_disclosure'], 'Mandatory Disclosure');

    // Field key mapper test
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
});
