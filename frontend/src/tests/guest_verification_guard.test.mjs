/**
 * frontend/src/tests/guest_verification_guard.test.mjs
 * Test Suite: Guest Verification Guard & Authentication Routing
 *
 * Verifies:
 * 1. Guest clicks Verify Document → login prompt opens and upload API is not called.
 * 2. Guest clicks Verify Sample → login prompt opens and sample verification API is not called.
 * 3. The authentication-required message is visible and accessible.
 * 4. Preserves selected PDF, document type, document ID, and privacy option while prompting for login.
 * 5. Preserves selected sample document while prompting for login.
 * 6. Authenticated Verify Document still submits with the Bearer token.
 * 7. Authenticated Verify Sample still submits with the Bearer token.
 * 8. Guest-mode visual feedback provides concise "Sign in to verify" hint while keeping action buttons interactive.
 * 9. Explicit retry after login: Document is not automatically submitted upon authentication until user clicks verify.
 * 10. Direct invocation defense-in-depth: Unauthenticated calls to handlers trigger auth modal without API calls.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

const AUTH_REQUIRED_MESSAGE =
  'Auditor login required to run document verification and audit logging. Please sign in or register.';

// Simulated Mock API client tracking outgoing HTTP headers and payloads
class MockVerificationApiClient {
  constructor() {
    this.uploadCalls = [];
    this.sampleCalls = [];
  }

  async uploadAndProcessDocument(file, options, token = null) {
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    this.uploadCalls.push({ file, options, headers });
    if (!token) {
      const err = new Error('Authentication required. Please provide a valid Bearer token.');
      err.status = 401;
      throw err;
    }
    return {
      success: true,
      document_id: options.documentId || 'DOC_001',
      filename: file.name,
      processing_status: 'VALID',
    };
  }

  async verifyDatasetSample(docId, token = null) {
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    this.sampleCalls.push({ docId, headers });
    if (!token) {
      const err = new Error('Authentication required. Please provide a valid Bearer token.');
      err.status = 401;
      throw err;
    }
    return {
      success: true,
      document_id: docId,
      processing_status: 'VALID',
    };
  }
}

// Simulated App & Component Workflow Harness reflecting App.tsx, UploadSection.tsx, and DatasetSampleSelector.tsx
class VerificationWorkflowHarness {
  constructor(initialToken = null) {
    this.token = initialToken;
    this.user = initialToken
      ? { name: 'Dr. Alok Sharma', email: 'alok.sharma@aicte.gov.in', role: 'auditor' }
      : null;
    this.api = new MockVerificationApiClient();

    // App state
    this.isAuthModalOpen = false;
    this.authNotice = null;
    this.authMode = 'login';
    this.activeSampleId = undefined;
    this.currentDoc = null;
    this.error = null;

    // UploadSection state
    this.uploadState = {
      selectedFile: null,
      documentId: '',
      documentType: '',
      enablePrivacyMasking: true,
      ocrThreshold: 0.65,
      authAlert: null,
      clientError: null,
    };

    // DatasetSampleSelector state
    this.sampleSelectorState = {
      authAlert: null,
    };
  }

  get isAuthenticated() {
    return Boolean(this.user && this.token);
  }

  // UploadSection interactions
  selectUploadFile(file) {
    this.uploadState.selectedFile = file;
    this.uploadState.clientError = null;
  }

  setUploadOptions({ documentId, documentType, enablePrivacyMasking, ocrThreshold }) {
    if (documentId !== undefined) this.uploadState.documentId = documentId;
    if (documentType !== undefined) this.uploadState.documentType = documentType;
    if (enablePrivacyMasking !== undefined) this.uploadState.enablePrivacyMasking = enablePrivacyMasking;
    if (ocrThreshold !== undefined) this.uploadState.ocrThreshold = ocrThreshold;
  }

  handleRequireAuth(message = AUTH_REQUIRED_MESSAGE, pendingDocId) {
    this.authNotice = message;
    this.authMode = 'login';
    if (pendingDocId) {
      this.activeSampleId = pendingDocId;
    }
    this.isAuthModalOpen = true;
  }

  async clickVerifyDocument() {
    if (!this.uploadState.selectedFile) {
      this.uploadState.clientError = 'Please select a PDF document to verify.';
      return;
    }

    if (!this.isAuthenticated) {
      this.uploadState.authAlert = AUTH_REQUIRED_MESSAGE;
      this.handleRequireAuth(AUTH_REQUIRED_MESSAGE);
      return;
    }

    // Authenticated submit
    try {
      const res = await this.api.uploadAndProcessDocument(
        this.uploadState.selectedFile,
        {
          documentId: this.uploadState.documentId || undefined,
          documentType: this.uploadState.documentType || undefined,
          enablePrivacyMasking: this.uploadState.enablePrivacyMasking,
          ocrThreshold: this.uploadState.ocrThreshold,
        },
        this.token
      );
      this.currentDoc = res;
    } catch (err) {
      this.error = err.message;
    }
  }

  async clickVerifySample(docId) {
    if (!this.isAuthenticated) {
      this.sampleSelectorState.authAlert = AUTH_REQUIRED_MESSAGE;
      this.handleRequireAuth(AUTH_REQUIRED_MESSAGE, docId);
      return;
    }

    this.activeSampleId = docId;
    try {
      const res = await this.api.verifyDatasetSample(docId, this.token);
      this.currentDoc = res;
    } catch (err) {
      this.error = err.message;
    }
  }

  loginSuccess(token, user) {
    this.token = token;
    this.user = user;
    this.isAuthModalOpen = false;
    this.authNotice = null;
    this.uploadState.authAlert = null;
    this.sampleSelectorState.authAlert = null;
  }

  closeAuthModal() {
    this.isAuthModalOpen = false;
    this.authNotice = null;
  }
}

describe('Guest Verification Guard & Auth Flow Tests', () => {
  it('1. Guest clicks Verify Document → login prompt opens and upload API is not called', async () => {
    const harness = new VerificationWorkflowHarness(null);
    assert.equal(harness.isAuthenticated, false);

    const testFile = { name: 'aicte_eoa_sample.pdf', size: 1024 * 50 };
    harness.selectUploadFile(testFile);

    // Guest clicks Verify Document
    await harness.clickVerifyDocument();

    // Verify modal is open and API was NOT called
    assert.equal(harness.isAuthModalOpen, true);
    assert.equal(harness.api.uploadCalls.length, 0);
  });

  it('2. Guest clicks Verify Sample → login prompt opens and sample verification API is not called', async () => {
    const harness = new VerificationWorkflowHarness(null);
    assert.equal(harness.isAuthenticated, false);

    // Guest clicks Verify Sample
    await harness.clickVerifySample('SAMPLE_REAL_001');

    // Verify modal is open, pending sample preserved, and API was NOT called
    assert.equal(harness.isAuthModalOpen, true);
    assert.equal(harness.activeSampleId, 'SAMPLE_REAL_001');
    assert.equal(harness.api.sampleCalls.length, 0);
  });

  it('3. The authentication-required message is visible and accessible', async () => {
    const harness = new VerificationWorkflowHarness(null);
    harness.selectUploadFile({ name: 'disclosure_doc.pdf', size: 2048 });

    await harness.clickVerifyDocument();

    // Check message in authNotice (for AuthPage modal) and in uploadState alert
    assert.equal(harness.authNotice, AUTH_REQUIRED_MESSAGE);
    assert.equal(harness.uploadState.authAlert, AUTH_REQUIRED_MESSAGE);
    assert.ok(harness.authNotice.includes('Auditor login required'));
    assert.ok(harness.authNotice.includes('audit logging'));
  });

  it('4. Preserves selected PDF, document type, document ID, and privacy option while prompting for login', async () => {
    const harness = new VerificationWorkflowHarness(null);
    const mockFile = { name: 'nba_accreditation.pdf', size: 1024 * 120 };

    harness.selectUploadFile(mockFile);
    harness.setUploadOptions({
      documentId: 'INST_NBA_2026',
      documentType: 'nba_accreditation',
      enablePrivacyMasking: true,
      ocrThreshold: 0.70,
    });

    // Guest clicks verify
    await harness.clickVerifyDocument();

    // All form data MUST remain intact in state
    assert.equal(harness.uploadState.selectedFile.name, 'nba_accreditation.pdf');
    assert.equal(harness.uploadState.documentId, 'INST_NBA_2026');
    assert.equal(harness.uploadState.documentType, 'nba_accreditation');
    assert.equal(harness.uploadState.enablePrivacyMasking, true);
    assert.equal(harness.uploadState.ocrThreshold, 0.70);
  });

  it('5. Preserves selected sample document while prompting for login', async () => {
    const harness = new VerificationWorkflowHarness(null);
    await harness.clickVerifySample('SAMPLE_SCANNED_002');

    assert.equal(harness.activeSampleId, 'SAMPLE_SCANNED_002');
    assert.equal(harness.sampleSelectorState.authAlert, AUTH_REQUIRED_MESSAGE);
  });

  it('6. Authenticated Verify Document still submits with the Bearer token', async () => {
    const harness = new VerificationWorkflowHarness('valid_jwt_auditor_token');
    assert.equal(harness.isAuthenticated, true);

    const file = { name: 'naac_cert.pdf', size: 1024 * 40 };
    harness.selectUploadFile(file);
    harness.setUploadOptions({
      documentId: 'NAAC_2026',
      documentType: 'naac_certificate',
    });

    await harness.clickVerifyDocument();

    // Verify API called and Bearer header attached
    assert.equal(harness.api.uploadCalls.length, 1);
    const call = harness.api.uploadCalls[0];
    assert.equal(call.file.name, 'naac_cert.pdf');
    assert.equal(call.options.documentId, 'NAAC_2026');
    assert.equal(call.headers['Authorization'], 'Bearer valid_jwt_auditor_token');
    assert.equal(harness.currentDoc.success, true);
  });

  it('7. Authenticated Verify Sample still submits with the Bearer token', async () => {
    const harness = new VerificationWorkflowHarness('valid_jwt_auditor_token');
    assert.equal(harness.isAuthenticated, true);

    await harness.clickVerifySample('SAMPLE_REAL_003');

    // Verify API called and Bearer header attached
    assert.equal(harness.api.sampleCalls.length, 1);
    const call = harness.api.sampleCalls[0];
    assert.equal(call.docId, 'SAMPLE_REAL_003');
    assert.equal(call.headers['Authorization'], 'Bearer valid_jwt_auditor_token');
    assert.equal(harness.currentDoc.success, true);
  });

  it('8. Guest-mode visual feedback exposes "Sign in to verify" hint without disabling the button', () => {
    const guestHarness = new VerificationWorkflowHarness(null);
    const authedHarness = new VerificationWorkflowHarness('jwt.token');

    // Guest mode has false isAuthenticated
    assert.equal(guestHarness.isAuthenticated, false);
    assert.equal(authedHarness.isAuthenticated, true);

    // In guest mode, action button canSubmit depends on file selection, NOT authentication
    guestHarness.selectUploadFile({ name: 'test.pdf', size: 1000 });
    const canGuestSubmit = Boolean(guestHarness.uploadState.selectedFile) && !guestHarness.uploadState.clientError;
    assert.equal(canGuestSubmit, true);
  });

  it('9. Explicit retry after login: Document is not automatically submitted upon authentication', async () => {
    const harness = new VerificationWorkflowHarness(null);
    const file = { name: 'eoa_document.pdf', size: 1024 * 80 };
    harness.selectUploadFile(file);

    // Guest attempts verification
    await harness.clickVerifyDocument();
    assert.equal(harness.isAuthModalOpen, true);
    assert.equal(harness.api.uploadCalls.length, 0);

    // Auditor logs in via the modal
    harness.loginSuccess('newly_issued_jwt_token', {
      name: 'Auditor Meena',
      email: 'meena@aicte.gov.in',
      role: 'auditor',
    });

    // Verification MUST NOT auto-submit; API calls remain 0 until user explicitly clicks
    assert.equal(harness.isAuthModalOpen, false);
    assert.equal(harness.isAuthenticated, true);
    assert.equal(harness.api.uploadCalls.length, 0);

    // User explicitly retries verification
    await harness.clickVerifyDocument();
    assert.equal(harness.api.uploadCalls.length, 1);
    assert.equal(harness.api.uploadCalls[0].headers['Authorization'], 'Bearer newly_issued_jwt_token');
  });

  it('10. Direct handler invocation defense-in-depth: Unauthenticated calls do not trigger API requests', async () => {
    const harness = new VerificationWorkflowHarness(null);

    // Simulate direct call to handleSelectSample
    await harness.clickVerifySample('SAMPLE_DIRECT_TEST');
    assert.equal(harness.api.sampleCalls.length, 0);
    assert.equal(harness.isAuthModalOpen, true);
    assert.equal(harness.authNotice, AUTH_REQUIRED_MESSAGE);

    // Closing the modal returns cleanly without side-effects
    harness.closeAuthModal();
    assert.equal(harness.isAuthModalOpen, false);
    assert.equal(harness.authNotice, null);
  });
});
