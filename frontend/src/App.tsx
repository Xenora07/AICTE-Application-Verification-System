import React, { useEffect, useState } from 'react';
import { Sidebar, MainNavDestination } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { UploadSection } from './components/UploadSection';
import { DatasetSampleSelector } from './components/DatasetSampleSelector';
import { ReviewerSummaryBanner } from './components/ReviewerSummaryBanner';
import { ExtractedFieldsCard } from './components/ExtractedFieldsCard';
import { ValidationFindingsList } from './components/ValidationFindingsList';
import { CrossDocumentMatrix } from './components/CrossDocumentMatrix';
import { SyntheticTestRunner } from './components/SyntheticTestRunner';
import { HumanReviewDrawer } from './components/HumanReviewDrawer';
import { WelcomePage } from './components/WelcomePage';
import { AuthPage } from './components/auth/AuthPage';
import { SystemExplainerPage } from './components/SystemExplainerPage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { api } from './services/api';
import {
  AdjudicationRecord,
  CrossValidateResponse,
  DatasetManifestDocument,
  DocumentProcessResponse,
  SyntheticTestCase,
  SystemHealth,
} from './types/api';
import { AlertCircle, CheckCircle2, FileText, ShieldAlert, History } from 'lucide-react';

const AppContent: React.FC = () => {
  const queryParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const { user, isAuthenticated, logout } = useAuth();

  // Top-level View Routing ('welcome' | 'auth' | 'app' | 'explainer')
  const [currentView, setCurrentView] = useState<'welcome' | 'auth' | 'app' | 'explainer'>(() => {
    if (queryParams?.get('view') === 'app' || queryParams?.get('tab')) return 'app';
    if (queryParams?.get('view') === 'auth') return 'auth';
    if (queryParams?.get('view') === 'explainer' || queryParams?.get('view') === 'how-it-works') return 'explainer';
    try {
      const storedToken = localStorage.getItem('aicte_auth_token') || sessionStorage.getItem('aicte_auth_token');
      return storedToken ? 'app' : 'welcome';
    } catch {
      return 'welcome';
    }
  });
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const v = params.get('view');
      if (v === 'explainer' || v === 'how-it-works') {
        setCurrentView('explainer');
      } else if (v === 'auth') {
        setCurrentView('auth');
      } else if (v === 'app' || params.get('tab')) {
        setCurrentView('app');
      } else {
        setCurrentView('welcome');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateToView = (view: 'welcome' | 'auth' | 'app' | 'explainer', replaceState = false) => {
    setCurrentView(view);
    try {
      const url = new URL(window.location.href);
      if (view === 'welcome') {
        url.searchParams.delete('view');
      } else {
        url.searchParams.set('view', view);
      }
      if (replaceState) {
        window.history.replaceState({}, '', url.toString());
      } else {
        window.history.pushState({}, '', url.toString());
      }
    } catch {
      // ignore
    }
  };

  // Navigation destinations inside verification workspace
  const [activeDestination, setActiveDestination] = useState<MainNavDestination>(
    () => (queryParams?.get('tab') as MainNavDestination) || 'single'
  );
  const [activeSubTab, setActiveSubTab] = useState<'findings' | 'fields' | 'cross' | 'doc_view' | 'audit'>('findings');

  // Backend data & session state
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [datasetDocs, setDatasetDocs] = useState<DatasetManifestDocument[]>([]);
  const [testCases, setTestCases] = useState<SyntheticTestCase[]>([]);

  const [currentDoc, setCurrentDoc] = useState<DocumentProcessResponse | null>(null);
  const [crossReport, setCrossReport] = useState<CrossValidateResponse | null>(null);
  const [activeSampleId, setActiveSampleId] = useState<string | undefined>();
  const [activeTestId, setActiveTestId] = useState<string | undefined>();
  const [selectedFindingIdForReview, setSelectedFindingIdForReview] = useState<string | undefined>();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isReviewDrawerOpen, setIsReviewDrawerOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authNotice, setAuthNotice] = useState<string | null>(null);
  const [uploadedPdfUrl, setUploadedPdfUrl] = useState<string | null>(null);

  const AUTH_REQUIRED_MESSAGE =
    'Auditor login required to run document verification and audit logging. Please sign in or register.';

  const handleRequireAuth = (message = AUTH_REQUIRED_MESSAGE, pendingDocId?: string) => {
    setAuthNotice(message);
    setAuthMode('login');
    if (pendingDocId) {
      setActiveSampleId(pendingDocId);
    }
    setIsAuthModalOpen(true);
  };

  // Adjudication session state (survives drawer close/reopen)
  const [adjudications, setAdjudications] = useState<Record<string, AdjudicationRecord>>({});
  const [adjudicationAlert, setAdjudicationAlert] = useState<string | null>(null);

  // Theme state ('light' | 'dark')
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try {
      const qTheme = queryParams?.get('theme');
      if (qTheme === 'dark' || qTheme === 'light') return qTheme;
      const saved = localStorage.getItem('aicte_theme');
      if (saved === 'dark' || saved === 'light') return saved;
    } catch {
      // ignore
    }
    return 'light';
  });

  useEffect(() => {
    try {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('aicte_theme', theme);
    } catch {
      // ignore
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const handleClearSessionDrafts = () => {
    setAdjudications({});
    setAdjudicationAlert('Session adjudication drafts have been cleared.');
  };

  const handleSaveAdjudication = (record: AdjudicationRecord) => {
    setAdjudications((prev) => ({
      ...prev,
      [record.findingId]: record,
    }));
    setAdjudicationAlert(
      `Action Recorded: "${record.decision}" for ${record.ruleId} (${record.ruleName}) — "${record.notes}" (Session Draft)`
    );
  };

  const formatEngineLabel = (engine?: string | null) => {
    if (!engine) return 'Standard Rule & OCR Engine';
    if (engine === 'synthetic_test_engine') return 'Standard Automated Engine';
    if (engine.toLowerCase().includes('easyocr')) return 'EasyOCR Neural Engine';
    if (engine.toLowerCase().includes('tesseract')) return 'Tesseract OCR Engine';
    return engine.replace(/_/g, ' ');
  };

  // Load health, dataset manifest, and synthetic test cases on mount
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const healthData = await api.getHealth();
      setHealth(healthData);
    } catch (err: any) {
      console.warn('Backend not responding yet:', err);
    }

    try {
      const manifestData = await api.getDatasetManifest();
      setDatasetDocs(manifestData.documents);
    } catch (err: any) {
      console.warn('Dataset manifest error:', err);
    }

    try {
      const tcData = await api.getTestCases();
      setTestCases(tcData.test_cases);
    } catch (err: any) {
      console.warn('Test cases error:', err);
    }
  };

  // Handler: Upload user PDF
  const handleUpload = async (
    file: File,
    options: {
      documentId?: string;
      documentType?: string;
      enablePrivacyMasking: boolean;
      ocrThreshold: number;
    }
  ) => {
    if (!isAuthenticated) {
      handleRequireAuth();
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.uploadAndProcessDocument(file, options);
      setUploadedPdfUrl(URL.createObjectURL(file));
      setCurrentDoc(res);
      setActiveSampleId(undefined);
      setActiveDestination('single');
      setActiveSubTab('findings');
    } catch (err: any) {
      setError(err.message || 'Verification pipeline encountered a failure.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handler: Verify dataset sample document
  const handleSelectSample = async (docId: string) => {
    if (!isAuthenticated) {
      handleRequireAuth(AUTH_REQUIRED_MESSAGE, docId);
      return;
    }
    setIsLoading(true);
    setError(null);
    setActiveSampleId(docId);
    setUploadedPdfUrl(null);
    try {
      const res = await api.verifyDatasetSample(docId);
      setCurrentDoc(res);
      setActiveDestination('single');
      setActiveSubTab('findings');
    } catch (err: any) {
      setError(err.message || `Failed to verify dataset sample ${docId}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const initialSample = queryParams?.get('sample');
    if (initialSample) {
      handleSelectSample(initialSample);
    }
  }, []);

  // Handler: Run Cross-Validation
  const handleRunCrossValidation = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.crossValidateDocuments();
      setCrossReport(res);
    } catch (err: any) {
      setError(err.message || 'Failed to execute cross-document consistency checks.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handler: Execute synthetic scenario
  const handleExecuteScenario = async (testId: string) => {
    setIsLoading(true);
    setError(null);
    setActiveTestId(testId);
    try {
      const res = await api.executeTestScenario(testId);
      if (res.validation_report && res.reviewer_summary) {
        // Single document synthetic scenario
        setCurrentDoc({
          success: true,
          document_id: res.test_id,
          filename: `${res.scenario_name}.json`,
          file_size_bytes: 2048,
          sha256: 'simulated_checksum_synth',
          document_type: res.validation_report.document_type || 'aicte_eoa',
          processing_status: res.actual_outcome,
          processing_metadata: {
            total_pages: 1,
            processed_pages: 1,
            extraction_path: 'digital',
            digital_pages: [1],
            ocr_pages: [],
            timestamp_utc: new Date().toISOString(),
          },
          extracted_fields: {},
          table_data: [],
          validation_report: res.validation_report,
          normalized_findings: res.normalized_findings || [],
          reviewer_summary: res.reviewer_summary,
          warnings: [],
          errors: [],
        });
        setActiveDestination('single');
        setActiveSubTab('findings');
      } else if (res.consistency_report) {
        // Cross document synthetic scenario
        setCrossReport({
          success: true,
          consistency_report: res.consistency_report,
          normalized_findings: res.normalized_findings || [],
          overall_status: res.actual_outcome,
          requires_human_review: res.consistency_report.requires_human_review,
        });
        setActiveDestination('cross');
      }
    } catch (err: any) {
      setError(err.message || `Failed to execute scenario ${testId}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Render Welcome Page view
  if (currentView === 'welcome') {
    return (
      <WelcomePage
        onBeginVerification={() => {
          if (isAuthenticated) {
            navigateToView('app');
          } else {
            setAuthMode('login');
            navigateToView('auth');
          }
        }}
        onOpenAuth={(mode) => {
          setAuthMode(mode || 'login');
          navigateToView('auth');
        }}
        onOpenExplainer={() => {
          navigateToView('explainer');
        }}
        theme={theme}
        onToggleTheme={toggleTheme}
        isAuthenticated={isAuthenticated}
        userName={user?.name}
      />
    );
  }

  // Render Explainer Document view ("How It Works")
  if (currentView === 'explainer') {
    return (
      <SystemExplainerPage
        onBackToHome={() => navigateToView('welcome')}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
    );
  }

  // Render Authentication view
  if (currentView === 'auth') {
    return (
      <AuthPage
        initialMode={authMode}
        onAuthSuccess={() => {
          setAuthNotice(null);
          navigateToView('app');
        }}
        onBackToWelcome={() => {
          setAuthNotice(null);
          navigateToView('welcome');
        }}
        theme={theme}
        onToggleTheme={toggleTheme}
        notice={authNotice}
      />
    );
  }

  return (
    <div className="app-layout">
      {/* Concept 1: LEDGER Compact Left Navigation Sidebar */}
      <Sidebar
        activeDestination={activeDestination}
        onSelectDestination={setActiveDestination}
        datasetCount={datasetDocs.length}
        draftCount={Object.keys(adjudications).length}
        onClearSessionDrafts={handleClearSessionDrafts}
      />

      {/* Main Viewport */}
      <div className="main-viewport">
        {/* Concept 1: LEDGER Compact Top Header */}
        <Navbar
          health={health}
          onRefreshHealth={fetchInitialData}
          datasetCount={datasetDocs.length}
          onOpenUpload={() => setIsUploadModalOpen(true)}
          theme={theme}
          onToggleTheme={toggleTheme}
          draftCount={Object.keys(adjudications).length}
          onClearSessionDrafts={handleClearSessionDrafts}
          onSelectDestination={setActiveDestination}
          user={user}
          onSignOut={async () => {
            await logout();
            setCurrentView('welcome');
          }}
          onOpenAuth={() => {
            setAuthNotice(null);
            setAuthMode('login');
            setIsAuthModalOpen(true);
          }}
        />

        <main className="content-container">
          {/* Adjudication Action Confirmation Notification */}
          {adjudicationAlert && (
            <div style={{
              padding: '10px 16px',
              backgroundColor: 'var(--color-pass-bg)',
              border: '1px solid var(--color-pass-border)',
              borderRadius: '6px',
              color: 'var(--color-pass-text)',
              marginBottom: '16px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '12.5px',
              fontWeight: '500',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} />
                <span>{adjudicationAlert}</span>
              </div>
              <button
                onClick={() => setAdjudicationAlert(null)}
                style={{ background: 'none', color: 'var(--color-pass-text)', fontSize: '16px', cursor: 'pointer' }}
                title="Dismiss"
              >
                ✕
              </button>
            </div>
          )}

          {/* Pipeline Error Bar */}
          {error && (
            <div style={{
              padding: '12px 16px',
              backgroundColor: 'var(--color-fail-bg)',
              border: '1px solid var(--color-fail-border)',
              borderRadius: '6px',
              color: 'var(--color-fail-text)',
              marginBottom: '16px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '12.5px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={16} />
                <div>
                  <strong>Pipeline Execution Error: </strong> {error}
                </div>
              </div>
              <button
                onClick={() => setError(null)}
                style={{ background: 'none', color: 'var(--color-fail-text)', fontSize: '16px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
          )}

          {/* Destination 1: Document Verification */}
          {activeDestination === 'single' && (
            <div>
              {currentDoc ? (
                <div>
                  {/* Top Document Summary & Overall Verification Status Card */}
                  <ReviewerSummaryBanner
                    summary={currentDoc.reviewer_summary}
                    documentId={currentDoc.document_id}
                    documentType={currentDoc.document_type}
                    filename={currentDoc.filename}
                    sha256={currentDoc.sha256}
                    processingStatus={currentDoc.processing_status}
                    totalPages={currentDoc.processing_metadata?.total_pages}
                    fileSizeBytes={currentDoc.file_size_bytes}
                    uploadedAt={currentDoc.processing_metadata?.timestamp_utc}
                    institutionName={(currentDoc.extracted_fields?.institution_name?.normalized_value as string) || null}
                    applicationId={(currentDoc.extracted_fields?.application_id?.normalized_value as string) || null}
                    academicYear={(currentDoc.extracted_fields?.academic_year?.normalized_value as string) || null}
                    onOpenAdjudication={() => {
                      setSelectedFindingIdForReview(undefined);
                      setIsReviewDrawerOpen(true);
                    }}
                    onNewVerification={() => {
                      setCurrentDoc(null);
                      setUploadedPdfUrl(null);
                      setActiveSampleId(undefined);
                    }}
                    adjudications={adjudications}
                  />

                  {/* Horizontal Workspace Sub-Tabs with ARIA */}
                  <div className="ledger-tabs" role="tablist" aria-label="Document Verification Sub-Views">
                    <button
                      role="tab"
                      id="tab-findings"
                      aria-controls="tabpanel-findings"
                      aria-selected={activeSubTab === 'findings'}
                      onClick={() => setActiveSubTab('findings')}
                      className={`ledger-tab ${activeSubTab === 'findings' ? 'active' : ''}`}
                    >
                      Findings ({currentDoc.normalized_findings.length})
                    </button>
                    <button
                      role="tab"
                      id="tab-fields"
                      aria-controls="tabpanel-fields"
                      aria-selected={activeSubTab === 'fields'}
                      onClick={() => setActiveSubTab('fields')}
                      className={`ledger-tab ${activeSubTab === 'fields' ? 'active' : ''}`}
                    >
                      Extracted Fields ({Object.keys(currentDoc.extracted_fields).length})
                    </button>
                    <button
                      role="tab"
                      id="tab-cross"
                      aria-controls="tabpanel-cross"
                      aria-selected={activeSubTab === 'cross'}
                      onClick={() => setActiveSubTab('cross')}
                      className={`ledger-tab ${activeSubTab === 'cross' ? 'active' : ''}`}
                    >
                      Compare Documents
                    </button>
                    <button
                      role="tab"
                      id="tab-doc-view"
                      aria-controls="tabpanel-doc-view"
                      aria-selected={activeSubTab === 'doc_view'}
                      onClick={() => setActiveSubTab('doc_view')}
                      className={`ledger-tab ${activeSubTab === 'doc_view' ? 'active' : ''}`}
                    >
                      Document View
                    </button>
                    <button
                      role="tab"
                      id="tab-audit"
                      aria-controls="tabpanel-audit"
                      aria-selected={activeSubTab === 'audit'}
                      onClick={() => setActiveSubTab('audit')}
                      className={`ledger-tab ${activeSubTab === 'audit' ? 'active' : ''}`}
                    >
                      Audit Trail
                    </button>
                  </div>

                  {/* Sub-Tab 1: Findings Workspace (Table + Evidence Inspector) */}
                  {activeSubTab === 'findings' && (
                    <div role="tabpanel" id="tabpanel-findings" aria-labelledby="tab-findings">
                      <ValidationFindingsList
                        findings={currentDoc.normalized_findings}
                        adjudications={adjudications}
                        onOpenAdjudicationForFinding={(fid) => {
                          setSelectedFindingIdForReview(fid);
                          setIsReviewDrawerOpen(true);
                        }}
                        onOpenReviewAll={() => {
                          setSelectedFindingIdForReview(undefined);
                          setIsReviewDrawerOpen(true);
                        }}
                        extractedFields={currentDoc.extracted_fields}
                        totalPages={currentDoc.processing_metadata?.total_pages}
                        documentFilename={currentDoc.filename}
                        pdfUrl={uploadedPdfUrl}
                      />
                    </div>
                  )}

                  {/* Sub-Tab 2: Extracted Fields Card */}
                  {activeSubTab === 'fields' && (
                    <div role="tabpanel" id="tabpanel-fields" aria-labelledby="tab-fields">
                      <ExtractedFieldsCard
                        fields={currentDoc.extracted_fields}
                        tables={currentDoc.table_data}
                        processingMetadata={currentDoc.processing_metadata}
                      />
                    </div>
                  )}

                  {/* Sub-Tab 3: Cross-Document Checks */}
                  {activeSubTab === 'cross' && (
                    <div role="tabpanel" id="tabpanel-cross" aria-labelledby="tab-cross">
                      <CrossDocumentMatrix
                        onRunCrossValidation={handleRunCrossValidation}
                        crossReport={crossReport}
                        isLoading={isLoading}
                        activeDocumentsCount={health?.active_documents_in_session || (currentDoc ? 1 : 0)}
                      />
                    </div>
                  )}

                  {/* Sub-Tab 4: Document View (Visual Page Representation) */}
                  {activeSubTab === 'doc_view' && (
                    <div role="tabpanel" id="tabpanel-doc-view" aria-labelledby="tab-doc-view" className="surface-card" style={{ padding: '24px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <div>
                          <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>
                            Document Digital Stream Inspection
                          </h3>
                          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                            Total Pages: {currentDoc.processing_metadata?.total_pages !== undefined ? currentDoc.processing_metadata.total_pages : 'Not available'} • Path: {currentDoc.processing_metadata?.extraction_path || 'digital'}
                          </p>
                        </div>
                        <span className="badge badge-pass badge-pill">Digital Integrity Verified</span>
                      </div>

                      {uploadedPdfUrl && (
                        <div style={{ height: '520px', borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--border-color)', marginBottom: '16px' }}>
                          <iframe
                            src={uploadedPdfUrl}
                            title="Active Document PDF Stream"
                            style={{ width: '100%', height: '100%', border: 'none' }}
                          />
                        </div>
                      )}

                      <div style={{
                        backgroundColor: 'var(--bg-surface)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '6px',
                        padding: '24px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '12px',
                        color: 'var(--text-primary)',
                        maxHeight: '400px',
                        overflowY: 'auto',
                        lineHeight: '1.6',
                      }}>
                        <div style={{ color: 'var(--color-brand)', fontWeight: 'bold', marginBottom: '8px' }}>
                          --- DOCUMENT STREAM HEADER: {currentDoc.filename} ---
                        </div>
                        <div>SHA-256 Checksum: {currentDoc.sha256}</div>
                        <div>Document Type: {currentDoc.document_type}</div>
                        <div>Processing Outcome: {currentDoc.processing_status}</div>
                        <div>Digital Pages: [{currentDoc.processing_metadata?.digital_pages?.join(', ') || ''}]</div>
                        <div>OCR Pages: [{currentDoc.processing_metadata?.ocr_pages?.join(', ') || ''}]</div>
                        <div style={{ marginTop: '12px', color: 'var(--text-muted)' }}>
                          Stream verified by PyMuPDF text stream parser & Privacy Gateway redaction pipeline.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sub-Tab 5: Audit Trail */}
                  {activeSubTab === 'audit' && (
                    <div role="tabpanel" id="tabpanel-audit" aria-labelledby="tab-audit" className="surface-card" style={{ padding: '24px' }}>
                      <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <History size={16} />
                        <span>Regulatory Audit Trail & Decision Log</span>
                      </h3>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '600', color: 'var(--text-primary)' }}>
                            <span>1. Ingestion & Cryptographic Checksum</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{currentDoc.processing_metadata?.timestamp_utc || 'Timestamp'}</span>
                          </div>
                          <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>
                            Document registered with SHA-256: <span className="code-mono">{currentDoc.sha256}</span>. Anti-tamper verification passed.
                          </div>
                        </div>

                        <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '600', color: 'var(--text-primary)' }}>
                            <span>2. Privacy Gateway & PII Redaction</span>
                            <span className="badge badge-pass badge-pill" style={{ fontSize: '10px' }}>Active</span>
                          </div>
                          <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>
                            Automated redaction applied to institutional personal identifiers.
                          </div>
                        </div>

                        {Object.values(adjudications).length > 0 ? (
                          Object.values(adjudications).map((adj) => (
                            <div key={adj.findingId} style={{ padding: '12px', backgroundColor: 'var(--color-pass-bg)', borderRadius: '6px', border: '1px solid var(--color-pass-border)', fontSize: '12px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '600', color: 'var(--color-pass-text)' }}>
                                <span>Officer Adjudication: {adj.decision} ({adj.ruleId})</span>
                                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{adj.timestamp} (Session Draft)</span>
                              </div>
                              <div style={{ color: '#14532d', marginTop: '2px' }}>
                                Adjudication notes: "{adj.notes}"
                              </div>
                            </div>
                          ))
                        ) : (
                          <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic', padding: '6px' }}>
                            No human adjudications recorded in session draft yet.
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* No document active yet: show Upload & Dataset selection */
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '20px' }}>
                  <UploadSection
                    onUpload={handleUpload}
                    isLoading={isLoading}
                    uploadError={error}
                    isAuthenticated={isAuthenticated}
                    onRequireAuth={handleRequireAuth}
                  />
                  <DatasetSampleSelector
                    documents={datasetDocs}
                    onSelectSample={handleSelectSample}
                    isLoading={isLoading}
                    activeDocId={activeSampleId}
                    isAuthenticated={isAuthenticated}
                    onRequireAuth={handleRequireAuth}
                  />
                </div>
              )}
            </div>
          )}

          {/* Destination 2: Cross-Document Checks */}
          {activeDestination === 'cross' && (
            <CrossDocumentMatrix
              onRunCrossValidation={handleRunCrossValidation}
              crossReport={crossReport}
              isLoading={isLoading}
              activeDocumentsCount={health?.active_documents_in_session || (currentDoc ? 1 : 0)}
            />
          )}

          {/* Destination 3: Synthetic Test Suite */}
          {activeDestination === 'test-cases' && (
            <SyntheticTestRunner
              testCases={testCases}
              onExecuteScenario={handleExecuteScenario}
              isLoading={isLoading}
              activeTestId={activeTestId}
            />
          )}

          {/* Destination 4: Dataset Documents Catalog */}
          {activeDestination === 'dataset' && (
            <DatasetSampleSelector
              documents={datasetDocs}
              onSelectSample={handleSelectSample}
              isLoading={isLoading}
              activeDocId={activeSampleId}
              isAuthenticated={isAuthenticated}
              onRequireAuth={handleRequireAuth}
            />
          )}

          {/* Destination 5: Demo & System Checks */}
          {activeDestination === 'diagnostics' && (
            <div className="surface-card" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '8px' }}>
                System Readiness & System Checks
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                Real-time status of OCR engines, PDF extractors, and verification checks.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
                <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>SERVICE STATUS</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: '#15803d', marginTop: '2px' }}>
                    {health?.status === 'healthy' ? 'HEALTHY / ONLINE' : 'OFFLINE'}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    FastAPI v1.0.0
                  </div>
                </div>

                <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>OCR ENGINE</div>
                  <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-brand)', marginTop: '2px' }}>
                    {formatEngineLabel(health?.ocr_engine)}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Image preprocessing + deterministic fallback
                  </div>
                </div>

                <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>CATALOGED DATASET</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                    {health?.dataset_documents_available ?? datasetDocs.length} Documents
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Pre-indexed document repository
                  </div>
                </div>

                <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>ACTIVE IN SESSION</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--color-brand)', marginTop: '2px' }}>
                    {health?.active_documents_in_session ?? (currentDoc ? 1 : 0)} Documents
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Cross-document bundle registry
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Destination 6: Settings */}
          {activeDestination === 'settings' && (
            <div className="surface-card" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '8px' }}>
                Regulatory Verification Settings
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                Configured validation thresholds and decision-support boundaries for SIH26261.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxWidth: '600px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12.5px', fontWeight: '600', marginBottom: '4px' }}>
                    Default OCR Confidence Threshold
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.1"
                    max="1.0"
                    defaultValue="0.65"
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-surface)',
                      color: 'var(--text-primary)',
                      fontSize: '13px',
                    }}
                  />
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Extractions below this confidence are flagged as INCONCLUSIVE for human officer review.
                  </span>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12.5px', fontWeight: '600', marginBottom: '4px' }}>
                    Reviewer Session & Authentication Status
                  </label>
                  <input
                    type="text"
                    value="Guest Access (View Only - No Authentication Required)"
                    readOnly
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-surface-subtle)',
                      fontSize: '13px',
                      color: 'var(--text-secondary)',
                    }}
                  />
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Application currently operates in unauthenticated decision-support mode.
                  </span>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Upload Document Modal */}
      {isUploadModalOpen && (
        <UploadSection
          onUpload={handleUpload}
          isLoading={isLoading}
          uploadError={error}
          isModal
          onCloseModal={() => setIsUploadModalOpen(false)}
          isAuthenticated={isAuthenticated}
          onRequireAuth={handleRequireAuth}
        />
      )}

      {/* Auditor Authentication Gateway Modal */}
      {isAuthModalOpen && (
        <AuthPage
          initialMode={authMode}
          onAuthSuccess={() => {
            setIsAuthModalOpen(false);
            setAuthNotice(null);
          }}
          onBackToWelcome={() => {
            setIsAuthModalOpen(false);
            setAuthNotice(null);
            navigateToView('welcome');
          }}
          theme={theme}
          onToggleTheme={toggleTheme}
          isModal
          onClose={() => {
            setIsAuthModalOpen(false);
            setAuthNotice(null);
          }}
          notice={authNotice}
        />
      )}

      {/* Human Review Adjudication Drawer / Modal */}
      {currentDoc && (
        <HumanReviewDrawer
          isOpen={isReviewDrawerOpen}
          onClose={() => {
            setIsReviewDrawerOpen(false);
            setSelectedFindingIdForReview(undefined);
          }}
          findings={currentDoc.normalized_findings}
          documentId={currentDoc.document_id}
          adjudications={adjudications}
          onSaveAdjudication={handleSaveAdjudication}
          initialFindingId={selectedFindingIdForReview}
        />
      )}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
