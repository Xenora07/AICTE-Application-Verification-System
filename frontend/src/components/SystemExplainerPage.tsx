/**
 * frontend/src/components/SystemExplainerPage.tsx
 * AICTE Application Verification System — Detailed System Explainer Document View.
 * Faithfully implements the full content and interactive architecture of SIH26261.html:
 * - Problem statement & need for automated first-level screening
 * - 9-stage complete system architecture with expandable stages & simple overview toggle
 * - SVG diagrams: OCR extraction, two validation gates, privacy gateway, cross-consistency, anomaly signals, findings engine
 * - Interactive data flow diagram
 * - Interactive 7-step end-to-end walkthrough with tabbed Input/Operation/Output/Evidence inspector & Prev/Next controls
 * - Findings and severity matrix (High, Medium, Low) with interactive dashboard preview & review actions
 * - Security and trust principles
 * - Explicit MVP scope boundaries (In-Scope vs Out-of-Scope)
 * - Styled in project's warm ivory / espresso palette with full Light & Dark mode support
 * - Prominent "Back to Home" navigation and browser history synchronization
 */

import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Sun,
  Moon,
  Printer,
  Pause,
  Play,
  Layers,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  AlertTriangle,
  FileSearch,
  Cpu,
  Lock,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import aicteLogo from '../assets/aicte_logo.png';
import '../styles/SystemExplainerPage.css';

interface SystemExplainerPageProps {
  onBackToHome: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

interface StageItem {
  id: string;
  stageNum: string;
  title: string;
  summary: string;
  detail: string;
  note: string;
  group: 'g1' | 'g2';
}

const STAGES_DATA: StageItem[] = [
  {
    id: 'stage-1',
    stageNum: 'STAGE 01',
    title: 'Application Submission',
    summary: 'Applicant uploads the form and supporting documents (PDFs, images).',
    detail: 'Handles initial ingestion of academic dossiers, land title records, and mandatory compliance filings.',
    note: 'Accepted file types and sizes are checked at upload.',
    group: 'g1',
  },
  {
    id: 'stage-2',
    stageNum: 'STAGE 02',
    title: 'OCR + Document Understanding',
    summary: 'PyMuPDF for digital PDFs; PaddleOCR for scans and images; OpenCV preprocessing and rotation correction.',
    detail: 'Documents classified and fields mapped to structured keys with page references and coordinates.',
    note: 'Keeps OCR evidence, page refs, coordinates where available, confidence; uncertain fields flagged.',
    group: 'g1',
  },
  {
    id: 'stage-3',
    stageNum: 'STAGE 03',
    title: 'Secure Storage',
    summary: 'Originals kept unchanged beside OCR text, fields, metadata and evidence references.',
    detail: 'Cryptographic hashing (SHA-256) locks original file provenance in immutable storage vaults.',
    note: 'Original files are separate from derived data.',
    group: 'g2',
  },
  {
    id: 'stage-4',
    stageNum: 'STAGE 04',
    title: 'Deterministic + Pydantic Validation',
    summary: 'Rule checks (required fields, lengths, formats, dates, file limits) then Pydantic schema checks (types, enums, conditionals).',
    detail: 'Deterministic statutory rule evaluation runs first, followed by strict schema parsing and validation.',
    note: 'Business rules and schema validation stay distinct.',
    group: 'g2',
  },
  {
    id: 'stage-5',
    stageNum: 'STAGE 05',
    title: 'Privacy Gateway',
    summary: 'Sensitive fields found via schema metadata and detection rules; purpose-based masking; scoped, keyed tokenization where appropriate.',
    detail: 'Redacts personally identifiable information (PII) before logs or reviewer views are generated.',
    note: 'Original file and raw OCR are never overwritten; sensitive logs redacted.',
    group: 'g2',
  },
  {
    id: 'stage-6',
    stageNum: 'STAGE 06',
    title: 'Cross-Document Consistency',
    summary: 'Compares IDs, certificate numbers, dates, programme details and intake across submitted documents.',
    detail: 'Detects conflicting declarations across university affiliation letters, state NOCs, and AICTE forms.',
    note: 'Submitted documents only; no live external records.',
    group: 'g2',
  },
  {
    id: 'stage-7',
    stageNum: 'STAGE 07',
    title: 'Authenticity + Anomaly Detection',
    summary: 'SHA-256 duplicate detection, PDF metadata and structural checks, limited visual checks.',
    detail: 'Flags anomalies such as font metric irregularities, mismatched creation/modification timestamps, and identical hashes.',
    note: 'Results are “Possible anomaly” or “Review signal”, not proof of forgery.',
    group: 'g1',
  },
  {
    id: 'stage-8',
    stageNum: 'STAGE 08',
    title: 'Unified Findings Engine',
    summary: 'Normalizes, deduplicates, assigns rule-based severity, attaches evidence, keeps source layer and explanation, tracks review status.',
    detail: 'Merges validation errors, consistency mismatches, and anomaly signals into a single unified audit queue.',
    note: 'Single queue from all analysis layers.',
    group: 'g1',
  },
  {
    id: 'stage-9',
    stageNum: 'STAGE 09',
    title: 'Output Window + Reviewer Dashboard',
    summary: 'Unified assessment: status, counts, prioritised findings, evidence beside originals, review actions, audit history.',
    detail: 'Presents verified findings to human scrutiny officers with side-by-side document evidence and adjudication tools.',
    note: 'Recommends next actions; humans decide.',
    group: 'g1',
  },
];

interface WalkthroughStep {
  name: string;
  input: string;
  operation: string;
  output: string;
  evidence: string;
}

const WALKTHROUGH_STEPS: WalkthroughStep[] = [
  {
    name: 'Upload',
    input: 'Demo form + 2 documents from “Demo Institute of Technology” (fictional).',
    operation: 'Receive and store originals.',
    output: 'Originals stored unchanged.',
    evidence: 'Stage 01 · 03',
  },
  {
    name: 'OCR',
    input: 'Scanned page of document 2.',
    operation: 'PaddleOCR text extraction, field mapping.',
    output: 'Institution ID DEMO-001; Intake 100 at low confidence.',
    evidence: 'Page 2, region 3, confidence score',
  },
  {
    name: 'Validation',
    input: 'Extracted fields from the form.',
    operation: 'Rule + Pydantic schema checks.',
    output: 'Mandatory field “Affiliation date” missing.',
    evidence: 'Rule R-12 on form page 1',
  },
  {
    name: 'Consistency',
    input: 'Form intake 120 and document 2 intake 100.',
    operation: 'Compare same field across documents.',
    output: 'Mismatch, manual review required.',
    evidence: 'Form p1 vs doc 2 p2',
  },
  {
    name: 'Anomaly',
    input: 'Two uploaded files.',
    operation: 'SHA-256 hash comparison.',
    output: 'Identical hashes: possible duplicate file.',
    evidence: 'Hash a91f…c2 (review signal)',
  },
  {
    name: 'Findings',
    input: 'Results from all layers.',
    operation: 'Normalize, dedupe, assign severity.',
    output: '4 findings in one queue (illustrative).',
    evidence: 'Source layer + evidence kept per finding',
  },
  {
    name: 'Review',
    input: 'Findings queue.',
    operation: 'Dashboard shows evidence beside originals.',
    output: 'Reviewer marks, resolves or dismisses with reason.',
    evidence: 'Audit trail entry per action',
  },
];

export const SystemExplainerPage: React.FC<SystemExplainerPageProps> = ({
  onBackToHome,
  theme,
  onToggleTheme,
}) => {
  // Explainer interactive states
  const [isAnimationPaused, setIsAnimationPaused] = useState(false);
  const [isSimpleView, setIsSimpleView] = useState(false);
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({
    'stage-1': true,
    'stage-2': false,
    'stage-3': false,
    'stage-4': false,
    'stage-5': false,
    'stage-6': false,
    'stage-7': false,
    'stage-8': false,
    'stage-9': false,
  });
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [dashboardFindingStatus, setDashboardFindingStatus] = useState<string>('Open');
  const [lastActionMessage, setLastActionMessage] = useState<string | null>(null);

  // Toggle stage card expansion
  const toggleStage = (id: string) => {
    setExpandedStages((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleNextStep = () => {
    setActiveStepIndex((prev) => Math.min(WALKTHROUGH_STEPS.length - 1, prev + 1));
  };

  const handlePrevStep = () => {
    setActiveStepIndex((prev) => Math.max(0, prev - 1));
  };

  const activeStep = WALKTHROUGH_STEPS[activeStepIndex];

  return (
    <div className={`explainer-document-container ${isAnimationPaused ? 'static-motion' : ''}`}>
      {/* Sticky Top Document Bar */}
      <header className="explainer-top-bar">
        <div className="explainer-bar-inner">
          <div className="explainer-brand-group">
            <button
              type="button"
              onClick={onBackToHome}
              className="explainer-btn-back"
              title="Return to Welcome Page"
            >
              <ArrowLeft size={15} />
              <span>Back to Home</span>
            </button>
            <div className="explainer-brand-lockup">
              <img src={aicteLogo} alt="AICTE Emblem" className="explainer-logo-icon" />
              <div className="explainer-brand-title">
                <b>SIH26261</b>
                <span>Technical Architecture Explainer</span>
              </div>
            </div>
          </div>

          <div className="explainer-actions-group">
            <button
              type="button"
              className={`explainer-tool-btn ${isAnimationPaused ? 'active' : ''}`}
              onClick={() => setIsAnimationPaused((prev) => !prev)}
              aria-pressed={isAnimationPaused}
              title="Toggle SVG flowline animations"
            >
              {isAnimationPaused ? <Play size={13} /> : <Pause size={13} />}
              <span>{isAnimationPaused ? 'Play animation' : 'Pause animation'}</span>
            </button>

            <button
              type="button"
              className={`explainer-tool-btn ${isSimpleView ? 'active' : ''}`}
              onClick={() => setIsSimpleView((prev) => !prev)}
              aria-pressed={isSimpleView}
              title="Collapse or expand stage descriptions"
            >
              <Layers size={13} />
              <span>{isSimpleView ? 'Detailed view' : 'Simple overview'}</span>
            </button>

            <button
              type="button"
              className="explainer-tool-btn"
              onClick={() => window.print()}
              title="Print document or save as PDF"
            >
              <Printer size={13} />
              <span>Print / Save PDF</span>
            </button>

            <button
              type="button"
              onClick={onToggleTheme}
              className="explainer-tool-btn explainer-theme-toggle"
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
              title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            >
              {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
            </button>
          </div>

          {/* Quick Anchor Navigation */}
          <nav className="explainer-quick-nav" aria-label="Explainer document sections">
            <a href="#section-overview">Overview</a>
            <a href="#section-problem">Problem</a>
            <a href="#section-architecture">Architecture</a>
            <a href="#section-dataflow">Data Flow</a>
            <a href="#section-example">Walkthrough</a>
            <a href="#section-severity">Severity</a>
            <a href="#section-trust">Trust &amp; Security</a>
            <a href="#section-scope">Scope Boundaries</a>
          </nav>
        </div>
      </header>

      {/* Main Document Content */}
      <main className="explainer-content-wrapper">
        {/* ===================================================================
            SECTION 1: Technical Hero & Overview
            =================================================================== */}
        <section className="explainer-section explainer-hero-section" id="section-overview">
          <div className="explainer-tag-badge">SIH26261 · SYSTEM EXPLAINER</div>
          <h1 className="explainer-main-title">
            AI-Powered Application Validation, Document Authentication and Regulatory Compliance Verification
          </h1>
          <p className="explainer-main-subtitle">
            An automated first-level screening system that checks institutional applications and supporting
            documents, identifies compliance issues, and provides evidence-backed findings for human review.
          </p>

          <div className="explainer-flow-strip" aria-label="Pipeline Stages Summary">
            <span>SUBMIT</span>
            <span>EXTRACT</span>
            <span>VALIDATE</span>
            <span>ANALYZE</span>
            <span>CONSOLIDATE</span>
            <span>REVIEW</span>
          </div>

          {/* Master Architectural Overview SVG Diagram */}
          <div className="explainer-diagram-card">
            <div className="diagram-scroll-container">
              <svg
                viewBox="0 0 900 250"
                role="img"
                aria-label="Application form and documents enter a pipeline of validation and analysis components and produce a reviewer dashboard"
              >
                <defs>
                  <marker id="ar" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                    <path d="M0 0L8 4L0 8z" fill="#c27838" />
                  </marker>
                </defs>
                <g fill="var(--bg-surface)" stroke="#c27838">
                  <rect x="20" y="40" width="80" height="100" rx="6" />
                  <rect x="40" y="60" width="80" height="100" rx="6" />
                  <rect x="60" y="80" width="80" height="100" rx="6" />
                </g>
                <g stroke="#3e2719" strokeWidth="3">
                  <path d="M75 110h50M75 125h50M75 140h35" />
                </g>
                <text x="100" y="205" fill="var(--text-muted)" fontSize="12" textAnchor="middle">
                  Form + documents
                </text>
                <g fill="#3e2719" stroke="#c27838">
                  <rect x="200" y="30" width="110" height="44" rx="8" />
                  <rect x="330" y="30" width="110" height="44" rx="8" />
                  <rect x="200" y="100" width="110" height="44" rx="8" />
                  <rect x="330" y="100" width="110" height="44" rx="8" />
                  <rect x="265" y="170" width="110" height="44" rx="8" />
                </g>
                <g fill="#ffffff" fontSize="12" textAnchor="middle">
                  <text x="255" y="57">OCR</text>
                  <text x="385" y="57">Validation</text>
                  <text x="255" y="127">Privacy</text>
                  <text x="385" y="127">Consistency</text>
                  <text x="320" y="197">Anomaly checks</text>
                </g>
                <path
                  className="explainer-flowline"
                  d="M150 125H195M445 100L520 125M445 135L520 125"
                  stroke="#c27838"
                  strokeWidth="2"
                  fill="none"
                  markerEnd="url(#ar)"
                />
                <rect x="520" y="55" width="110" height="140" rx="8" fill="#e69d45" />
                <text x="575" y="130" textAnchor="middle" fontSize="13" fill="#141518" fontWeight="700">
                  Unified findings
                </text>
                <path
                  className="explainer-flowline"
                  d="M635 125H690"
                  stroke="#c27838"
                  strokeWidth="2"
                  markerEnd="url(#ar)"
                />
                <rect x="695" y="35" width="190" height="180" rx="8" fill="var(--bg-surface)" stroke="var(--border-color)" />
                <rect x="695" y="35" width="190" height="26" rx="8" fill="#c27838" />
                <text x="790" y="53" textAnchor="middle" fontSize="12" fill="#ffffff" fontWeight="700">
                  Reviewer dashboard
                </text>
                <g fill="#dc2626">
                  <rect x="710" y="78" width="160" height="14" rx="3" />
                </g>
                <g fill="#f59e0b">
                  <rect x="710" y="102" width="130" height="14" rx="3" />
                </g>
                <g fill="#16a34a">
                  <rect x="710" y="126" width="150" height="14" rx="3" />
                </g>
                <rect x="710" y="160" width="160" height="40" rx="4" fill="var(--bg-surface-subtle)" />
              </svg>
            </div>
            <div className="diagram-caption">
              System Pipeline Architecture: Multi-tiered validation and anomaly engines feed into the unified findings engine, driving evidence-linked reviewer adjudication.
            </div>
          </div>
        </section>

        {/* ===================================================================
            SECTION 2: The Problem We Address
            =================================================================== */}
        <section className="explainer-section" id="section-problem">
          <h2 className="explainer-h2">The Problem We Address</h2>
          <p className="explainer-sub">
            Reviewers repeat the same checks across large bundles. The system handles first-pass screening
            so scrutiny officers focus attention on flagged anomalies and exceptions.
          </p>

          <div className="explainer-comparison-grid">
            {/* Manual Inspection Card */}
            <div className="explainer-card problem-card">
              <h3 className="explainer-h3">Manual Document Inspection</h3>
              <div className="card-illustration">
                <svg viewBox="0 0 300 110" role="img" aria-label="Many documents with repeated manual checks">
                  <g fill="var(--bg-surface)" stroke="#8a7869">
                    <rect x="10" y="20" width="50" height="70" />
                    <rect x="25" y="12" width="50" height="70" />
                    <rect x="40" y="4" width="50" height="70" />
                  </g>
                  <path d="M110 55h40M170 30v50M200 30v50M230 30v50" stroke="#dc2626" strokeDasharray="4" />
                  <text x="110" y="100" fontSize="11" fill="var(--text-muted)">
                    re-check · compare · note
                  </text>
                </svg>
              </div>
              <ul className="explainer-list bullet-manual">
                <li>Large dossier bundles with multiple technical certificates</li>
                <li>Repetitive manual field and registration checking</li>
                <li>Error-prone cross-document comparison across files</li>
                <li>Missed compliance gaps, expired NOCs, and capacity inconsistencies</li>
                <li>Findings and notes compiled manually without audit links</li>
              </ul>
            </div>

            {/* AI-Assisted First-Level Screening Card */}
            <div className="explainer-card solution-card">
              <h3 className="explainer-h3">AI-Assisted First-Level Screening</h3>
              <div className="card-illustration">
                <svg viewBox="0 0 300 110" role="img" aria-label="Automated checks reduce documents to a short list of flagged findings">
                  <g fill="var(--bg-surface)" stroke="#c27838">
                    <rect x="10" y="20" width="50" height="70" />
                    <rect x="25" y="12" width="50" height="70" />
                  </g>
                  <path className="explainer-flowline" d="M95 50h60" stroke="#c27838" strokeWidth="2" />
                  <rect x="170" y="25" width="110" height="16" rx="3" fill="#dc2626" />
                  <rect x="170" y="48" width="90" height="16" rx="3" fill="#f59e0b" />
                  <rect x="170" y="71" width="70" height="16" rx="3" fill="#8a7869" />
                </svg>
              </div>
              <ul className="explainer-list bullet-ai">
                <li>Fields extracted, validated, and normalized automatically</li>
                <li>Cross-checks documents against declared application values</li>
                <li>Generates prioritized, evidence-linked findings for review</li>
                <li>Directs reviewer attention immediately to non-compliant items</li>
                <li>Maintains tamper-evident audit history across review actions</li>
              </ul>
            </div>
          </div>

          <p className="explainer-disclaimer-note">
            Clarification note: No performance figures or artificial acceleration percentages are claimed; none have been formally benchmarked.
          </p>
        </section>

        {/* ===================================================================
            SECTION 3: Complete 9-Stage System Architecture
            =================================================================== */}
        <section className="explainer-section" id="section-architecture">
          <h2 className="explainer-h2">Complete System Architecture</h2>
          <p className="explainer-sub">
            Nine stages in order of execution. Select any stage card to inspect architectural details.
            Toggle “Simple overview” above to collapse expanded text.
          </p>

          <div className={`stages-grid ${isSimpleView ? 'simple-mode' : ''}`}>
            {STAGES_DATA.map((stage) => {
              const isExpanded = !isSimpleView && expandedStages[stage.id];
              return (
                <div
                  key={stage.id}
                  className={`stage-interactive-card ${stage.group} ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => toggleStage(stage.id)}
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      toggleStage(stage.id);
                    }
                  }}
                >
                  <div className="stage-card-num">{stage.stageNum}</div>
                  <h3 className="stage-card-title">{stage.title}</h3>
                  <div className="stage-card-summary">{stage.summary}</div>
                  {isExpanded && (
                    <div className="stage-card-more">
                      <p>{stage.detail}</p>
                      <span className="stage-card-note">{stage.note}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Deep-Dive Stage Diagram Grid */}
          <div className="deep-dive-diagrams-grid">
            {/* Stage 02: OCR to Structured Fields */}
            <div className="explainer-card diagram-box">
              <h3 className="explainer-h3">Stage 02 · OCR to Structured Fields</h3>
              <svg viewBox="0 0 360 170" role="img" aria-label="Scanned document becomes text then structured field cards; one field has low confidence">
                <rect x="5" y="10" width="70" height="95" fill="var(--bg-surface)" stroke="var(--border-color)" transform="rotate(-4 40 60)" />
                <path d="M15 30h50M15 42h50M15 54h40" stroke="#aab" strokeWidth="3" transform="rotate(-4 40 60)" />
                <path className="explainer-flowline" d="M85 60h35" stroke="#c27838" strokeWidth="2" />
                <rect x="125" y="20" width="70" height="80" fill="#3e2719" rx="4" />
                <text x="132" y="45" fontSize="9" fill="#c27838" fontFamily="monospace">AICT-DEMO</text>
                <text x="132" y="60" fontSize="9" fill="#c27838" fontFamily="monospace">C-0042</text>
                <text x="132" y="75" fontSize="9" fill="#c27838" fontFamily="monospace">12/06/2024</text>
                <text x="132" y="90" fontSize="9" fill="#c27838" fontFamily="monospace">1?0</text>
                <path className="explainer-flowline" d="M205 60h30" stroke="#c27838" strokeWidth="2" />
                <g fontSize="10">
                  <rect x="240" y="8" width="115" height="30" rx="4" fill="var(--bg-surface-subtle)" stroke="#16a34a" />
                  <text x="246" y="27" fill="var(--text-primary)">Institution ID ✓</text>
                  <rect x="240" y="44" width="115" height="30" rx="4" fill="var(--bg-surface-subtle)" stroke="#16a34a" />
                  <text x="246" y="63" fill="var(--text-primary)">Certificate No. ✓</text>
                  <rect x="240" y="80" width="115" height="30" rx="4" fill="var(--bg-surface-subtle)" stroke="#16a34a" />
                  <text x="246" y="99" fill="var(--text-primary)">Issue Date ✓</text>
                  <rect x="240" y="116" width="115" height="30" rx="4" fill="rgba(245, 158, 11, 0.15)" stroke="#f59e0b" />
                  <text x="246" y="135" fill="var(--text-primary)">Intake · low confidence</text>
                </g>
              </svg>
              <p className="diagram-note">
                Illustrative example. Each field retains page reference, bounding coordinates, and confidence score. Uncertain fields trigger low-confidence signals.
              </p>
            </div>

            {/* Stage 04: Two Validation Gates */}
            <div className="explainer-card diagram-box">
              <h3 className="explainer-h3">Stage 04 · Two Validation Gates</h3>
              <svg viewBox="0 0 360 170" role="img" aria-label="Document passes rule checks then schema checks">
                <rect x="5" y="55" width="50" height="65" fill="var(--bg-surface)" stroke="var(--border-color)" />
                <path className="explainer-flowline" d="M60 88h40" stroke="#c27838" strokeWidth="2" />
                <rect x="105" y="30" width="100" height="115" rx="8" fill="rgba(245, 158, 11, 0.12)" stroke="#f59e0b" />
                <text x="155" y="50" textAnchor="middle" fontSize="11" fontWeight="700" fill="var(--text-primary)">A · Rule checks</text>
                <text x="112" y="75" fontSize="10" fill="#dc2626">Required field missing</text>
                <text x="112" y="95" fontSize="10" fill="#dc2626">Invalid date format</text>
                <path className="explainer-flowline" d="M210 88h30" stroke="#c27838" strokeWidth="2" />
                <rect x="245" y="30" width="110" height="115" rx="8" fill="var(--bg-surface-subtle)" stroke="#c27838" />
                <text x="300" y="50" textAnchor="middle" fontSize="11" fontWeight="700" fill="var(--text-primary)">B · Schema (Pydantic)</text>
                <text x="252" y="80" fontSize="10" fill="#16a34a">Schema valid</text>
                <text x="252" y="100" fontSize="9" fill="var(--text-muted)">types · enums · structure</text>
              </svg>
              <p className="diagram-note">
                Business rules and schema validation stay distinct. Deterministic regulatory rules check required presence, while Pydantic enforces typing.
              </p>
            </div>

            {/* Stage 05: Privacy Gateway */}
            <div className="explainer-card diagram-box">
              <h3 className="explainer-h3">Stage 05 · Privacy Gateway</h3>
              <svg viewBox="0 0 360 190" role="img" aria-label="Phone number is masked for display and a service receives only needed fields while the original stays in secure storage">
                <rect x="5" y="10" width="130" height="50" rx="6" fill="var(--bg-surface)" stroke="var(--border-color)" />
                <text x="12" y="30" fontSize="10" fill="var(--text-muted)">Phone (original, stored)</text>
                <text x="12" y="48" fontSize="12" fontFamily="monospace" fill="var(--text-primary)">98765 43210</text>
                <rect x="5" y="130" width="130" height="50" rx="6" fill="#3e2719" />
                <text x="12" y="150" fontSize="10" fill="#c27838">Secure vault · unchanged</text>
                <text x="12" y="168" fontSize="10" fill="#ffffff">original + raw OCR</text>
                <path d="M70 60v70" stroke="var(--border-color)" strokeDasharray="3" />
                <rect x="160" y="40" width="70" height="90" rx="8" fill="#3e2719" stroke="#c27838" />
                <text x="195" y="82" textAnchor="middle" fill="#ffffff" fontSize="11">Privacy</text>
                <text x="195" y="96" textAnchor="middle" fill="#ffffff" fontSize="11">Gateway</text>
                <path className="explainer-flowline" d="M135 35h20L170 50M230 60h35M230 110h35" stroke="#c27838" strokeWidth="2" fill="none" />
                <rect x="270" y="20" width="85" height="55" rx="6" fill="var(--bg-surface-subtle)" stroke="#c27838" />
                <text x="276" y="40" fontSize="9" fill="var(--text-muted)">Reviewer view (role)</text>
                <text x="276" y="60" fontSize="12" fontFamily="monospace" fill="var(--text-primary)">•••••• 3210</text>
                <rect x="270" y="90" width="85" height="55" rx="6" fill="var(--bg-surface-subtle)" stroke="#c27838" />
                <text x="276" y="108" fontSize="9" fill="var(--text-muted)">Service: needed fields</text>
                <text x="276" y="128" fontSize="10" fontFamily="monospace" fill="var(--text-primary)">tok_7f3a…</text>
              </svg>
              <p className="diagram-note">
                Masking is purpose-based; tokenization is scoped and keyed. Originals and raw OCR are never overwritten by masking.
              </p>
            </div>

            {/* Stage 06: Cross-Document Consistency */}
            <div className="explainer-card diagram-box">
              <h3 className="explainer-h3">Stage 06 · Cross-Document Consistency</h3>
              <svg viewBox="0 0 360 180" role="img" aria-label="Two documents compared; institution ID matches, intake 120 versus 100 mismatches">
                <rect x="5" y="10" width="120" height="150" rx="6" fill="var(--bg-surface)" stroke="var(--border-color)" />
                <rect x="235" y="10" width="120" height="150" rx="6" fill="var(--bg-surface)" stroke="var(--border-color)" />
                <g fontSize="10" fill="var(--text-primary)">
                  <text x="12" y="28" fontWeight="700">Document A</text>
                  <text x="12" y="55">Inst. ID: DEMO-001</text>
                  <text x="12" y="95">Intake: 120</text>
                  <text x="242" y="28" fontWeight="700">Document B</text>
                  <text x="242" y="55">Inst. ID: DEMO-001</text>
                  <text x="242" y="95">Intake: 100</text>
                </g>
                <path d="M125 52H235" stroke="#16a34a" strokeWidth="2" />
                <path d="M125 92H235" stroke="#dc2626" strokeWidth="2" strokeDasharray="5" />
                <rect x="140" y="110" width="80" height="40" rx="5" fill="rgba(220, 38, 38, 0.12)" stroke="#dc2626" />
                <text x="180" y="127" textAnchor="middle" fontSize="9" fill="#dc2626" fontWeight="700">Mismatch detected</text>
                <text x="180" y="140" textAnchor="middle" fontSize="9" fill="var(--text-muted)">manual review</text>
              </svg>
              <p className="diagram-note">
                Compares values across submitted application files only. Does not query live external databases.
              </p>
            </div>

            {/* Stage 07: Anomaly Signals */}
            <div className="explainer-card diagram-box">
              <h3 className="explainer-h3">Stage 07 · Anomaly Signals</h3>
              <svg viewBox="0 0 360 170" role="img" aria-label="Identical file fingerprints, metadata panel and a visual region with a difference">
                <g fontFamily="monospace" fontSize="9">
                  <rect x="5" y="10" width="110" height="40" rx="4" fill="var(--bg-surface)" stroke="#f59e0b" />
                  <text x="10" y="25" fill="var(--text-primary)">SHA-256 a91f…c2</text>
                  <text x="10" y="40" fill="#c27838">file1.pdf</text>
                  <rect x="5" y="58" width="110" height="40" rx="4" fill="var(--bg-surface)" stroke="#f59e0b" />
                  <text x="10" y="73" fill="var(--text-primary)">SHA-256 a91f…c2</text>
                  <text x="10" y="88" fill="#c27838">file2.pdf</text>
                </g>
                <path d="M60 50v8" stroke="#f59e0b" strokeWidth="3" />
                <rect x="125" y="10" width="110" height="88" rx="4" fill="var(--bg-surface)" stroke="var(--border-color)" />
                <g fontSize="9" fill="var(--text-primary)">
                  <text x="130" y="26" fontWeight="700">PDF metadata</text>
                  <text x="130" y="42">Producer: editor-X</text>
                  <text x="130" y="56">Created ≠ Modified</text>
                  <text x="130" y="70" fill="#c27838" fontWeight="700">Review signal</text>
                </g>
                <rect x="245" y="10" width="110" height="88" rx="4" fill="var(--bg-surface)" stroke="var(--border-color)" />
                <path d="M255 30h90M255 45h90M255 60h60" stroke="#ccd" strokeWidth="4" />
                <rect x="310" y="52" width="38" height="16" fill="none" stroke="#dc2626" strokeDasharray="3" />
                <text x="10" y="130" fontSize="11" fill="var(--text-primary)">Outputs: “Possible anomaly” / “Review signal”.</text>
                <text x="10" y="148" fontSize="11" fill="var(--text-muted)">Never confirmed forgery.</text>
              </svg>
              <p className="diagram-note">
                Signals provide contextual review flags. The system never claims conclusive legal forgery without human adjudication.
              </p>
            </div>
          </div>

          {/* Interactive Findings Engine & Dashboard Simulation */}
          <div className="explainer-card findings-engine-box">
            <h3 className="explainer-h3">Stages 08–09 · Findings Engine Feeding the Reviewer Dashboard</h3>
            <span className="diagram-note">(Illustrative sample data, not a real AICTE application)</span>

            <div className="diagram-scroll-container" style={{ marginTop: '16px' }}>
              <svg viewBox="0 0 900 120" role="img" aria-label="Validation, consistency and anomaly streams merge into the findings engine and then the dashboard">
                <defs>
                  <marker id="a2" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                    <path d="M0 0L8 4L0 8z" fill="#3e2719" />
                  </marker>
                </defs>
                <rect x="10" y="10" width="170" height="26" rx="5" fill="#dc2626" />
                <rect x="10" y="47" width="170" height="26" rx="5" fill="#f59e0b" />
                <rect x="10" y="84" width="170" height="26" rx="5" fill="#c27838" />
                <g fill="#ffffff" fontSize="12" fontWeight="600">
                  <text x="20" y="28">Validation (04)</text>
                  <text x="20" y="65">Consistency (06)</text>
                  <text x="20" y="102">Anomaly (07)</text>
                </g>
                <path
                  className="explainer-flowline"
                  d="M180 23C260 23 270 60 330 60M180 60H330M180 97C260 97 270 60 330 60"
                  stroke="#3e2719"
                  fill="none"
                  strokeWidth="2"
                  markerEnd="url(#a2)"
                />
                <rect x="335" y="20" width="230" height="80" rx="8" fill="#3e2719" stroke="#c27838" />
                <text x="450" y="55" textAnchor="middle" fill="#ffffff" fontSize="14" fontWeight="700">
                  Unified Findings Engine
                </text>
                <text x="450" y="75" textAnchor="middle" fill="#c27838" fontSize="11">
                  normalize · dedupe · severity · evidence
                </text>
                <path
                  className="explainer-flowline"
                  d="M570 60H680"
                  stroke="#3e2719"
                  strokeWidth="2"
                  markerEnd="url(#a2)"
                />
                <rect x="690" y="15" width="200" height="90" rx="8" fill="var(--bg-surface)" stroke="#3e2719" />
                <text x="790" y="65" textAnchor="middle" fontSize="13" fill="var(--text-primary)" fontWeight="700">
                  Reviewer Dashboard
                </text>
              </svg>
            </div>

            {/* Interactive Reviewer Dashboard Preview */}
            <div className="explainer-sim-dashboard">
              <div className="sim-dash-header">
                <span>Application DEMO-APP-0001 · Status: Under Review</span>
                <span className="sim-tag">Illustrative Sample</span>
              </div>
              <div className="sim-dash-body">
                <div className="sim-dash-col">
                  <div className="sim-kpi-row">
                    <span className="badge-pass">14 passed</span>
                    <span className="badge-error">2 errors</span>
                    <span className="badge-warn">2 warnings</span>
                  </div>
                  <table className="sim-findings-table">
                    <thead>
                      <tr>
                        <th>Finding</th>
                        <th>Sev.</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Missing mandatory field</td>
                        <td><span className="sev-pill sev-high">High</span></td>
                        <td>Open</td>
                      </tr>
                      <tr>
                        <td>Cross-document mismatch</td>
                        <td><span className="sev-pill sev-med">Medium</span></td>
                        <td>{dashboardFindingStatus}</td>
                      </tr>
                      <tr>
                        <td>Possible duplicate file</td>
                        <td><span className="sev-pill sev-med">Medium</span></td>
                        <td>Open</td>
                      </tr>
                      <tr>
                        <td>Low-confidence OCR</td>
                        <td><span className="sev-pill sev-low">Low</span></td>
                        <td>Open</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="sim-dash-col sim-evidence-pane">
                  <h4 className="evidence-title">Evidence Inspector</h4>
                  <div className="evidence-preview-row">
                    <div className="evidence-thumb">Original preview (page 2)</div>
                    <div className="evidence-meta">
                      <div><strong>Institution ID:</strong> DEMO-001</div>
                      <div>
                        <strong>Intake:</strong> 100{' '}
                        <span className="sev-pill sev-med" style={{ fontSize: '10px' }}>low confidence</span>
                      </div>
                      <div className="evidence-note">Evidence: doc2 · p2 · region 3</div>
                    </div>
                  </div>

                  <div className="sim-action-buttons">
                    <button
                      type="button"
                      className="sim-btn"
                      onClick={() => {
                        setDashboardFindingStatus('Reviewed');
                        setLastActionMessage('Marked finding as Reviewed by Scrutiny Officer.');
                      }}
                    >
                      Mark Reviewed
                    </button>
                    <button
                      type="button"
                      className="sim-btn"
                      onClick={() => {
                        setDashboardFindingStatus('Resolved');
                        setLastActionMessage('Resolved finding with documented justification.');
                      }}
                    >
                      Resolve
                    </button>
                    <button
                      type="button"
                      className="sim-btn"
                      onClick={() => {
                        setDashboardFindingStatus('Dismissed');
                        setLastActionMessage('Dismissed finding with official auditor reasoning.');
                      }}
                    >
                      Dismiss with reason
                    </button>
                  </div>

                  {lastActionMessage && (
                    <div className="sim-action-alert">
                      <CheckCircle2 size={13} />
                      <span>{lastActionMessage}</span>
                    </div>
                  )}

                  <p className="sim-audit-footer">
                    Audit: 10:02 processed · 10:05 opened by reviewer. Report export: available in workspace. Output is an evidence-backed assessment with next actions, not automatic approval or rejection.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================================
            SECTION 4: How Data Moves Through the System
            =================================================================== */}
        <section className="explainer-section" id="section-dataflow">
          <h2 className="explainer-h2">How Data Moves Through the System</h2>
          <p className="explainer-sub">
            Originals never change; derived data lives elsewhere; sensitive access goes strictly through the privacy gateway.
          </p>

          <div className="explainer-card diagram-box">
            <div className="diagram-scroll-container">
              <svg viewBox="0 0 900 300" role="img" aria-label="Data flow from original documents to extracted data, privacy-filtered views, findings and the reviewer assessment">
                <defs>
                  <marker id="a3" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                    <path d="M0 0L8 4L0 8z" fill="#c27838" />
                  </marker>
                </defs>
                <g stroke="#c27838" fill="none" strokeWidth="2" className="explainer-flowline" markerEnd="url(#a3)">
                  <path d="M170 60H235" />
                  <path d="M170 60C200 120 200 190 235 220" />
                  <path d="M355 60H415" />
                  <path d="M515 60H575" />
                  <path d="M355 220H420M510 220C540 220 545 100 575 75" />
                  <path d="M700 60H745" />
                </g>
                <g fontSize="12" textAnchor="middle">
                  <rect x="20" y="30" width="150" height="60" rx="8" fill="#3e2719" />
                  <text x="95" y="55" fill="#ffffff" fontWeight="700">1 · Original files</text>
                  <text x="95" y="75" fill="#c27838" fontSize="10">unchanged, vault</text>

                  <rect x="240" y="30" width="115" height="60" rx="8" fill="var(--bg-surface)" stroke="#3e2719" />
                  <text x="297" y="55" fill="var(--text-primary)">2 · OCR text +</text>
                  <text x="297" y="72" fill="var(--text-primary)">structured fields</text>

                  <rect x="420" y="30" width="95" height="60" rx="8" fill="#3e2719" />
                  <text x="467" y="55" fill="#ffffff" fontWeight="700">Privacy</text>
                  <text x="467" y="72" fill="#ffffff" fontWeight="700">Gateway</text>

                  <rect x="580" y="30" width="120" height="60" rx="8" fill="var(--bg-surface)" stroke="#3e2719" />
                  <text x="640" y="55" fill="var(--text-primary)">3 · Filtered views</text>
                  <text x="640" y="72" fontSize="10" fill="var(--text-muted)">role + purpose</text>

                  <rect x="240" y="190" width="115" height="60" rx="8" fill="var(--bg-surface)" stroke="#f59e0b" />
                  <text x="297" y="215" fill="var(--text-primary)">Validation +</text>
                  <text x="297" y="232" fill="var(--text-primary)">anomaly checks</text>

                  <rect x="425" y="190" width="85" height="60" rx="8" fill="#3e2719" />
                  <text x="467" y="215" fill="#ffffff" fontWeight="700">4 · Unified</text>
                  <text x="467" y="232" fill="#ffffff" fontWeight="700">Findings</text>

                  <rect x="750" y="30" width="135" height="60" rx="8" fill="#c27838" />
                  <text x="817" y="55" fill="#ffffff" fontWeight="700">5 · Reviewer</text>
                  <text x="817" y="72" fill="#ffffff" fontWeight="700">assessment</text>
                </g>
              </svg>
            </div>
            <p className="diagram-note">
              Findings engine receives validation, consistency, and anomaly results. Originals and raw OCR are never overwritten by masking.
            </p>
          </div>
        </section>

        {/* ===================================================================
            SECTION 5: End-to-End Walkthrough
            =================================================================== */}
        <section className="explainer-section" id="section-example">
          <h2 className="explainer-h2">One Application, End to End</h2>
          <p className="explainer-sub">
            Interactive trace of a single application submission. Fictional institution, demo documents. Not an official verification.
          </p>

          <div className="walkthrough-tab-bar" role="tablist">
            {WALKTHROUGH_STEPS.map((w, idx) => (
              <button
                key={w.name}
                type="button"
                role="tab"
                aria-selected={idx === activeStepIndex}
                className={`walkthrough-tab-btn ${idx === activeStepIndex ? 'selected' : ''}`}
                onClick={() => setActiveStepIndex(idx)}
              >
                {idx + 1}. {w.name}
              </button>
            ))}
          </div>

          <div className="explainer-card walkthrough-stage-card" role="tabpanel">
            <h3 className="walkthrough-step-title">{activeStepIndex + 1}. {activeStep.name}</h3>
            <div className="io-quad-grid">
              <div className="io-box">
                <span className="io-tag">INPUT</span>
                <p>{activeStep.input}</p>
              </div>
              <div className="io-box">
                <span className="io-tag">OPERATION</span>
                <p>{activeStep.operation}</p>
              </div>
              <div className="io-box">
                <span className="io-tag">OUTPUT</span>
                <p>{activeStep.output}</p>
              </div>
              <div className="io-box">
                <span className="io-tag">EVIDENCE</span>
                <p>{activeStep.evidence}</p>
              </div>
            </div>

            <div className="walkthrough-nav-row">
              <button
                type="button"
                className="walkthrough-nav-btn"
                onClick={handlePrevStep}
                disabled={activeStepIndex === 0}
              >
                Previous Step
              </button>
              <span className="walkthrough-indicator">
                Step {activeStepIndex + 1} of {WALKTHROUGH_STEPS.length}
              </span>
              <button
                type="button"
                className="walkthrough-nav-btn"
                onClick={handleNextStep}
                disabled={activeStepIndex === WALKTHROUGH_STEPS.length - 1}
              >
                Next Step
              </button>
            </div>
          </div>
        </section>

        {/* ===================================================================
            SECTION 6: Findings and Severity
            =================================================================== */}
        <section className="explainer-section" id="section-severity">
          <h2 className="explainer-h2">Findings and Severity</h2>
          <p className="explainer-sub">
            Severity comes from configured regulatory rules. It is not an arbitrary probability of fraud.
          </p>

          <div className="explainer-comparison-grid">
            <div className="explainer-card">
              <h3 className="explainer-h3">Configured Severity Tiers</h3>
              <div className="severity-tier-row">
                <span className="sev-pill sev-high">High</span>
                <div>
                  <strong>Significant validation or compliance issue</strong> requiring prompt auditor attention (e.g., missing mandatory statutory approvals or altered intake limits).
                </div>
              </div>
              <div className="severity-tier-row">
                <span className="sev-pill sev-med">Medium</span>
                <div>
                  <strong>Discrepancy or issue requiring investigation</strong> (e.g., cross-document numerical mismatch, duplicate hash signal, or expired affiliation certificate).
                </div>
              </div>
              <div className="severity-tier-row">
                <span className="sev-pill sev-low">Low</span>
                <div>
                  <strong>Informational or lower-priority finding</strong> (e.g., low OCR confidence score, minor formatting irregularity, or non-critical contact update).
                </div>
              </div>
            </div>

            <div className="explainer-card">
              <h3 className="explainer-h3">Sample Finding Record <span className="diagram-note">(Illustrative)</span></h3>
              <table className="explainer-table">
                <tbody>
                  <tr>
                    <td><strong>Finding ID</strong></td>
                    <td><code>F-003</code></td>
                  </tr>
                  <tr>
                    <td><strong>Category</strong></td>
                    <td>Cross-document mismatch</td>
                  </tr>
                  <tr>
                    <td><strong>Severity</strong></td>
                    <td><span className="sev-pill sev-med">Medium</span></td>
                  </tr>
                  <tr>
                    <td><strong>Source Layer</strong></td>
                    <td>Cross-Document Consistency Engine</td>
                  </tr>
                  <tr>
                    <td><strong>Evidence Pointer</strong></td>
                    <td><code>doc A p1 · doc B p2</code></td>
                  </tr>
                  <tr>
                    <td><strong>Explanation</strong></td>
                    <td>Intake declared as 120 in Form vs 100 in Affiliation Letter.</td>
                  </tr>
                  <tr>
                    <td><strong>Status</strong></td>
                    <td><span className="badge-pass" style={{ fontSize: '11px' }}>Open for Review</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ===================================================================
            SECTION 7: Security and Trust
            =================================================================== */}
        <section className="explainer-section" id="section-trust">
          <h2 className="explainer-h2">Security and Trust</h2>
          <p className="explainer-sub">
            Engineered around foundational zero-trust principles protecting sensitive institutional data throughout verification.
          </p>

          <div className="trust-grid">
            <div className="explainer-card trust-card">
              <h3 className="explainer-h3">1. Original Documents Preserved</h3>
              <p>Original files are stored in immutable storage vaults. They are never overwritten by OCR normalization or PII masking.</p>
            </div>
            <div className="explainer-card trust-card">
              <h3 className="explainer-h3">2. Encryption &amp; Access Controls</h3>
              <p>Cryptographic key derivation (Scrypt) and strict token revocation safeguard authentication and storage paths.</p>
            </div>
            <div className="explainer-card trust-card">
              <h3 className="explainer-h3">3. Privacy Gateway</h3>
              <p>Masks personally identifiable information and scopes sensitive credentials before auditor display.</p>
            </div>
            <div className="explainer-card trust-card">
              <h3 className="explainer-h3">4. Role-Based Least Privilege</h3>
              <p>Humans and backend service workers see only the data fields strictly required for their operational mandate.</p>
            </div>
            <div className="explainer-card trust-card">
              <h3 className="explainer-h3">5. Evidence-Linked Findings</h3>
              <p>Every single finding retains an immutable reference back to source document, page number, and bounding box.</p>
            </div>
            <div className="explainer-card trust-card">
              <h3 className="explainer-h3">6. Immutable Audit Trail</h3>
              <p>Adjudication rulings, status transitions, and reviewer notes are permanently logged with timestamps.</p>
            </div>
            <div className="explainer-card trust-card">
              <h3 className="explainer-h3">7. Human-in-the-Loop Review</h3>
              <p>The AI system recommends evidence-backed findings; certified scrutiny officers make final decisions.</p>
            </div>
          </div>

          <p className="explainer-disclaimer-note">
            Clarification note: No formal ISO/SOC2 security certification or statutory compliance standard is claimed for this academic/hackathon prototype.
          </p>
        </section>

        {/* ===================================================================
            SECTION 8: MVP Scope & Limitations (In Scope vs Out of Scope)
            =================================================================== */}
        <section className="explainer-section" id="section-scope">
          <h2 className="explainer-h2">What the 24-Hour MVP Does and Does Not Do</h2>
          <p className="explainer-sub">
            Clear boundaries defining functional capabilities implemented within the SIH hackathon prototype versus future production integrations.
          </p>

          <div className="explainer-comparison-grid">
            {/* In Scope */}
            <div className="explainer-card in-scope-card">
              <div className="scope-card-header">
                <CheckCircle2 size={18} className="text-green" />
                <h3 className="explainer-h3">In Scope (Implemented)</h3>
              </div>
              <ul className="scope-list in-scope-list">
                <li>Multi-file document bundle upload (PDF, PNG, JPG)</li>
                <li>OCR and structured field extraction with bounding boxes</li>
                <li>Deterministic business rules and Pydantic schema validation</li>
                <li>Privacy Gateway with purpose-based PII masking</li>
                <li>Cross-document consistency comparison across submitted files</li>
                <li>Duplicate detection (SHA-256), PDF metadata, and structural checks</li>
                <li>Unified findings normalization and rule-based severity ranking</li>
                <li>Reviewer dashboard with evidence previews and adjudication actions</li>
              </ul>
            </div>

            {/* Out of Scope */}
            <div className="explainer-card out-of-scope-card">
              <div className="scope-card-header">
                <XCircle size={18} className="text-red" />
                <h3 className="explainer-h3">Out of Scope (Explicit Limitations)</h3>
              </div>
              <ul className="scope-list out-of-scope-list">
                <li>Issuing-authority API or external portal integration</li>
                <li>Live government-record or central database verification</li>
                <li>Mock institutional registry module</li>
                <li>Separate QR code or digital PKI signature validation module</li>
                <li>Custom deep-learning generative forgery detector</li>
                <li>Automatic final statutory approval or rejection issuance</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Back to Home Action Bar */}
        <div className="explainer-bottom-bar">
          <button
            type="button"
            onClick={onBackToHome}
            className="welcome-btn-primary welcome-btn-lg"
          >
            <ArrowLeft size={16} />
            <span>Return to AICTE Verification System</span>
          </button>
        </div>
      </main>

      {/* Explainer Footer */}
      <footer className="explainer-footer">
        <div className="explainer-footer-flow">
          <span>DOCUMENTS IN</span>
          <span>STRUCTURED INFORMATION</span>
          <span>VALIDATION + PRIVACY</span>
          <span>CONSISTENCY + ANOMALY ANALYSIS</span>
          <span>UNIFIED FINDINGS</span>
          <span>HUMAN REVIEW</span>
        </div>
        <p className="explainer-footer-summary">
          An explainable, privacy-aware first-level screening system that helps AICTE reviewers identify application issues faster and make informed decisions.
        </p>
      </footer>
    </div>
  );
};
