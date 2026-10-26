/**
 * frontend/src/components/WelcomePage.tsx
 * Refined AICTE Application Verification System Welcome Page.
 * Conforms strictly to institutional visual reference:
 * - Authentic circular AICTE emblem in header & document (zero halo, transparent, genuine asset)
 * - Horizontal logo + title lockup in document header matching reference
 * - Editorial serif typography (Playfair Display)
 * - Exact asymmetrical document rotations: front (-2.5deg), mid (3deg), back (-4deg), stage (1deg)
 * - Front document reduced by 15-20% for optimal desktop framing
 * - Fully unclipped 3D metallic paperclip naturally attached over top document edge
 * - Continuous glowing amber vertical scanning beam with synchronized row highlighting
 * - True natural vertical browser scrolling revealing rich AICTE-specific sections:
 *     1. Multi-Tier Scrutiny Pipeline
 *     2. Core Audit & Forensic Capabilities
 *     3. Regulatory Governance Architecture
 *     4. Executive Audit Call to Action
 * - Smooth scroll-triggered entrance animations (1000ms duration, alternating directions)
 * - Non-overflowing sticky header with fully visible actions (theme, sign in, register)
 * - Preserves Light & Dark modes and all authentication/workspace navigation
 */

import React, { useState, useEffect } from 'react';
import {
  ArrowRight,
  Sun,
  Moon,
  Lock,
  CheckCircle2,
  FileCheck,
  ShieldCheck,
  Cpu,
  Building2,
  Scale,
  FileSearch,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import aicteLogo from '../assets/aicte_logo.png';
import '../styles/WelcomePage.css';

interface WelcomePageProps {
  onBeginVerification: () => void;
  onOpenAuth: (mode?: 'login' | 'signup') => void;
  onOpenExplainer?: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  isAuthenticated: boolean;
  userName?: string;
}

export const WelcomePage: React.FC<WelcomePageProps> = ({
  onBeginVerification,
  onOpenAuth,
  onOpenExplainer,
  theme,
  onToggleTheme,
  isAuthenticated,
  userName,
}) => {
  // Staggered field highlight simulation synchronized with the amber scanning beam
  const [activeScanField, setActiveScanField] = useState<number>(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveScanField((prev) => (prev + 1) % 4);
    }, 1100);
    return () => clearInterval(interval);
  }, []);

  // IntersectionObserver for smooth 1000ms scroll-based entrance animations
  useEffect(() => {
    const observerCallback: IntersectionObserverCallback = (entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target); // Latch once visible to avoid re-triggering jitter
        }
      });
    };

    const observer = new IntersectionObserver(observerCallback, {
      root: null,
      threshold: 0.1,
      rootMargin: '20px 0px 20px 0px',
    });

    const revealElements = document.querySelectorAll('.scroll-reveal');
    revealElements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  return (
    <div className="welcome-page-container">
      {/* Background Architectural University / Secretariat Facade Line Art */}
      <div className="welcome-architectural-bg" aria-hidden="true">
        <svg
          viewBox="0 0 1440 1800"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="xMidYMin meet"
        >
          {/* Institutional Facade & Neoclassical Colonnade */}
          <path
            d="M 60 720 L 1380 720 M 100 720 L 100 360 L 1340 360 L 1340 720"
            stroke="currentColor"
            strokeWidth="1.2"
          />
          {/* Central Neoclassical Dome */}
          <path
            d="M 570 360 C 570 200, 870 200, 870 360 Z"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <line x1="720" y1="200" x2="720" y2="155" stroke="currentColor" strokeWidth="2" />
          <circle cx="720" cy="150" r="5" stroke="currentColor" strokeWidth="1.5" />
          {/* Triangular Pediment */}
          <path
            d="M 490 360 L 720 245 L 950 360 Z"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          {/* Colonnade Pillars */}
          <line x1="535" y1="360" x2="535" y2="720" stroke="currentColor" strokeWidth="1.2" />
          <line x1="610" y1="360" x2="610" y2="720" stroke="currentColor" strokeWidth="1.2" />
          <line x1="685" y1="360" x2="685" y2="720" stroke="currentColor" strokeWidth="1.2" />
          <line x1="755" y1="360" x2="755" y2="720" stroke="currentColor" strokeWidth="1.2" />
          <line x1="830" y1="360" x2="830" y2="720" stroke="currentColor" strokeWidth="1.2" />
          <line x1="905" y1="360" x2="905" y2="720" stroke="currentColor" strokeWidth="1.2" />
          {/* Upper Windows */}
          <rect x="160" y="420" width="45" height="65" rx="22" stroke="currentColor" strokeWidth="1" />
          <rect x="250" y="420" width="45" height="65" rx="22" stroke="currentColor" strokeWidth="1" />
          <rect x="340" y="420" width="45" height="65" rx="22" stroke="currentColor" strokeWidth="1" />
          <rect x="1055" y="420" width="45" height="65" rx="22" stroke="currentColor" strokeWidth="1" />
          <rect x="1145" y="420" width="45" height="65" rx="22" stroke="currentColor" strokeWidth="1" />
          <rect x="1235" y="420" width="45" height="65" rx="22" stroke="currentColor" strokeWidth="1" />
          {/* Lower Windows */}
          <rect x="160" y="540" width="45" height="85" stroke="currentColor" strokeWidth="1" />
          <rect x="250" y="540" width="45" height="85" stroke="currentColor" strokeWidth="1" />
          <rect x="340" y="540" width="45" height="85" stroke="currentColor" strokeWidth="1" />
          <rect x="1055" y="540" width="45" height="85" stroke="currentColor" strokeWidth="1" />
          <rect x="1145" y="540" width="45" height="85" stroke="currentColor" strokeWidth="1" />
          <rect x="1235" y="540" width="45" height="85" stroke="currentColor" strokeWidth="1" />

          {/* Extended Foundation & Blueprint Grid for Natural Page Scrolling */}
          <line x1="0" y1="720" x2="1440" y2="720" stroke="currentColor" strokeWidth="1" />
          <line x1="80" y1="720" x2="80" y2="1750" stroke="currentColor" strokeWidth="0.8" strokeDasharray="4 8" />
          <line x1="1360" y1="720" x2="1360" y2="1750" stroke="currentColor" strokeWidth="0.8" strokeDasharray="4 8" />
          <line x1="720" y1="720" x2="720" y2="1750" stroke="currentColor" strokeWidth="0.8" strokeDasharray="4 8" />
        </svg>
      </div>

      {/* Header Navigation with Authentic AICTE Crest & Hairline Divider (Overflow Protected) */}
      <header className="welcome-header entrance-top">
        <div className="welcome-logo-lockup">
          <img
            src={aicteLogo}
            alt="AICTE Official Emblem"
            className="welcome-aicte-emblem"
          />
          <div className="welcome-logo-divider" aria-hidden="true" />
          <div className="welcome-logo-text">
            <h1 className="welcome-title-full">Application Verification System</h1>
            <h1 className="welcome-title-mobile">AICTE</h1>
            <p>All India Council for Technical Education</p>
          </div>
        </div>

        <div className="welcome-nav-actions">
          <button
            type="button"
            onClick={onToggleTheme}
            className="btn btn-secondary btn-sm welcome-theme-toggle"
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          >
            {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
          </button>

          {isAuthenticated ? (
            <div className="welcome-user-auth-wrap">
              <span className="welcome-user-greeting">
                Welcome, <strong>{userName || 'Auditor'}</strong>
              </span>
              <button
                type="button"
                onClick={onBeginVerification}
                className="welcome-btn-primary welcome-btn-compact"
              >
                Go to Workspace <ArrowRight size={14} />
              </button>
            </div>
          ) : (
            <div className="welcome-guest-auth-wrap">
              <button
                type="button"
                onClick={() => onOpenAuth('login')}
                className="welcome-btn-secondary welcome-btn-compact"
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => onOpenAuth('signup')}
                className="welcome-btn-primary welcome-btn-compact"
              >
                Register
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Split-Screen Section */}
      <main className="welcome-hero-main">
        {/* Left Side: Editorial Typography & Actions */}
        <div className="welcome-hero-left">
          {/* Eyebrow Label */}
          <div className="welcome-eyebrow entrance-left">
            VALIDATE &nbsp;·&nbsp; VERIFY &nbsp;·&nbsp; ENSURE TRUST
          </div>

          {/* Headline in Playfair Display Editorial Serif */}
          <h2 className="welcome-headline entrance-left delay-100">
            Auditing Institutional <br />
            <span className="hero-accent">Trust &amp; Accuracy</span> <br />
            with AI
          </h2>

          <p className="welcome-description entrance-left delay-200">
            Autonomous multi-tier validation for Extension of Approval (EoA),
            Mandatory Disclosures, and Accreditation dossiers. Eliminates manual
            scrutiny bottlenecks with automated forensic authenticity and
            cross-institutional consistency checks.
          </p>

          {/* CTA Buttons */}
          <div className="welcome-cta-group entrance-up delay-350">
            <button
              type="button"
              onClick={onBeginVerification}
              className="welcome-btn-primary"
              id="begin-verification-btn"
            >
              <span>Begin Verification</span>
              <ArrowRight size={16} />
            </button>

            {!isAuthenticated ? (
              <button
                type="button"
                onClick={() => onOpenAuth('login')}
                className="welcome-btn-secondary"
              >
                <Lock size={15} />
                <span>Auditor Sign In</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onBeginVerification}
                className="welcome-btn-secondary"
              >
                <FileCheck size={15} />
                <span>Open Verification Matrix</span>
              </button>
            )}
          </div>

          {/* Institutional Compliance Micro-Badge */}
          <div className="welcome-compliance-strip entrance-up delay-500">
            <span className="compliance-dot" />
            <span>AICTE Approval Process Handbook (APH 2026-27) Compliant</span>
          </div>
        </div>

        {/* Right Side: Layered Tilted Scanned Documents (15-20% Reduced Footprint) */}
        <div className="welcome-hero-right entrance-right delay-200">
          <div className="welcome-document-stage">
            {/* Layer 3: Back document sheet (tilted -4deg) */}
            <div className="welcome-doc-layer welcome-doc-back" aria-hidden="true">
              <div className="doc-layer-peek-header">
                <span className="peek-line w-40" />
                <span className="peek-line w-60" />
              </div>
              <div className="doc-layer-peek-grid">
                <div className="peek-cell" />
                <div className="peek-cell" />
                <div className="peek-cell" />
              </div>
            </div>

            {/* Layer 2: Mid document sheet (tilted +3deg) */}
            <div className="welcome-doc-layer welcome-doc-mid" aria-hidden="true">
              <div className="doc-layer-peek-header">
                <span className="peek-line w-50" />
                <span className="peek-line w-75" />
              </div>
              <div className="doc-layer-peek-body">
                <span className="peek-line w-90" />
                <span className="peek-line w-80" />
                <span className="peek-line w-70" />
              </div>
            </div>

            {/* Layer 1: Foreground Main Scanned Document Sheet (tilted -2.5deg) */}
            <div className="welcome-doc-front">
              {/* Paperclip positioned OVER top edge, fully visible (parent has overflow: visible) */}
              <div
                className="welcome-paperclip"
                title="Attached annexure dossier"
                aria-hidden="true"
              >
                <svg
                  width="26"
                  height="50"
                  viewBox="0 0 26 50"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <defs>
                    <linearGradient id="clipShine" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stopColor="#e5e7eb" />
                      <stop offset="35%" stopColor="#9ca3af" />
                      <stop offset="70%" stopColor="#d1d5db" />
                      <stop offset="100%" stopColor="#6b7280" />
                    </linearGradient>
                    <filter id="clipShadow" x="-20%" y="-10%" width="140%" height="130%">
                      <feDropShadow dx="0" dy="2" stdDeviation="2.5" floodColor="#000000" floodOpacity="0.32" />
                    </filter>
                  </defs>
                  {/* Paperclip Outer & Inner Loops */}
                  <path
                    d="M 8 13 L 8 36 C 8 41 12 45 16.5 45 C 21 45 23 41 23 36 L 23 7 C 23 3.5 19.5 1.5 15 1.5 C 10.5 1.5 4.5 3.5 4.5 9 L 4.5 39 C 4.5 44.5 9.5 48.5 15 48.5 C 19.5 48.5 21 45.5 21 42"
                    stroke="url(#clipShine)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    filter="url(#clipShadow)"
                  />
                  {/* Highlight core */}
                  <path
                    d="M 8 13 L 8 36 C 8 41 12 45 16.5 45 C 21 45 23 41 23 36 L 23 7 C 23 3.5 19.5 1.5 15 1.5 C 10.5 1.5 4.5 3.5 4.5 9 L 4.5 39 C 4.5 44.5 9.5 48.5 15 48.5 C 19.5 48.5 21 45.5 21 42"
                    stroke="#ffffff"
                    strokeWidth="0.7"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    opacity="0.75"
                  />
                </svg>
              </div>

              {/* Internal Content Container with overflow: hidden for scan beam and text containment */}
              <div className="welcome-doc-inner-clip">
                {/* Dynamic Animated Amber Scanning Beam */}
                <div className="welcome-scan-beam" aria-hidden="true">
                  <div className="scan-beam-core" />
                  <div className="scan-beam-glow" />
                </div>

                {/* Realistic Document Header: Logo on Left + Authority Titles on Right */}
                <div className="doc-sim-header">
                  <div className="doc-sim-header-row">
                    <div className="doc-sim-crest-container">
                      <img
                        src={aicteLogo}
                        alt="AICTE Emblem"
                        className="doc-aicte-seal-img"
                      />
                    </div>
                    <div className="doc-sim-header-titles">
                      <h3 className="doc-sim-authority-title">
                        All India Council for Technical Education
                      </h3>
                      <p className="doc-sim-authority-subtitle">
                        (A Statutory Body of the Government of India)
                      </p>
                    </div>
                  </div>

                  <div className="doc-sim-notice-tag">
                    Approval Process 2026-27 • Extension of Approval (EoA)
                  </div>
                </div>

                {/* Document Body: Key Authentic Application Fields */}
                <div className="doc-sim-body">
                  <div
                    className={`doc-sim-field ${activeScanField === 0 ? 'highlighted' : ''}`}
                  >
                    <div className="doc-sim-field-label">
                      Application Permanent ID
                    </div>
                    <div className="doc-sim-field-value">
                      1-432890124 (Eastern Region)
                    </div>
                  </div>

                  <div
                    className={`doc-sim-field ${activeScanField === 1 ? 'highlighted' : ''}`}
                  >
                    <div className="doc-sim-field-label">
                      Name of Institution
                    </div>
                    <div className="doc-sim-field-value">
                      Kalyani Government Engineering College
                    </div>
                  </div>

                  <div
                    className={`doc-sim-field ${activeScanField === 2 ? 'highlighted' : ''}`}
                  >
                    <div className="doc-sim-field-label">
                      Approved Programme &amp; Intake
                    </div>
                    <div className="doc-sim-field-value">
                      Computer Science &amp; Engineering — 60 Seats
                    </div>
                  </div>

                  {/* Course Matrix Micro-Table */}
                  <div
                    className={`doc-sim-field doc-sim-table-field ${
                      activeScanField === 3 ? 'highlighted' : ''
                    }`}
                  >
                    <div className="doc-sim-field-label">
                      Academic Year: 2026 - 2027 • Approved Intake Breakdown
                    </div>
                    <div className="doc-sim-matrix-table">
                      <div className="matrix-row matrix-header-row">
                        <span>Programme</span>
                        <span>Level</span>
                        <span>Intake</span>
                        <span>Status</span>
                      </div>
                      <div className="matrix-row">
                        <span>Computer Science &amp; Engg</span>
                        <span>UG</span>
                        <span>60</span>
                        <span className="matrix-status-ok">VERIFIED</span>
                      </div>
                      <div className="matrix-row">
                        <span>Information Technology</span>
                        <span>UG</span>
                        <span>60</span>
                        <span className="matrix-status-ok">VERIFIED</span>
                      </div>
                    </div>
                  </div>

                  {/* Cryptographic Digest */}
                  <div className="doc-sim-digest">
                    <span className="digest-label">SHA-256 Digest:</span>
                    <span className="digest-value">
                      7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069
                    </span>
                  </div>
                </div>

                {/* Document Footer: Seal & Blue Handwritten Signature */}
                <div className="doc-sim-footer">
                  {/* Official Circular Seal */}
                  <div className="doc-official-stamp">
                    <svg
                      viewBox="0 0 100 100"
                      width="54"
                      height="54"
                      className="stamp-svg"
                      aria-hidden="true"
                    >
                      <circle
                        cx="50"
                        cy="50"
                        r="46"
                        stroke="currentColor"
                        strokeWidth="2"
                        fill="none"
                        strokeDasharray="4 2"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        stroke="currentColor"
                        strokeWidth="1.2"
                        fill="none"
                      />
                      <path
                        id="stampTextCurve"
                        d="M 18,50 A 32,32 0 1,1 82,50"
                        fill="none"
                      />
                      <text
                        fontSize="7.5"
                        fontWeight="bold"
                        fill="currentColor"
                        letterSpacing="0.1em"
                      >
                        <textPath href="#stampTextCurve" startOffset="50%" textAnchor="middle">
                          AICTE • APPROVAL VERIFIED
                        </textPath>
                      </text>
                      <text
                        x="50"
                        y="52"
                        fontSize="8"
                        fontWeight="800"
                        textAnchor="middle"
                        fill="currentColor"
                      >
                        2026-27
                      </text>
                      <text
                        x="50"
                        y="64"
                        fontSize="6.5"
                        fontWeight="600"
                        textAnchor="middle"
                        fill="currentColor"
                      >
                        AUTHORIZED
                      </text>
                    </svg>
                  </div>

                  {/* Blue Ballpoint Signature & Signoff */}
                  <div className="doc-sim-signature-block">
                    <div className="signature-pen-stroke" aria-hidden="true">
                      <svg
                        viewBox="0 0 160 50"
                        width="105"
                        height="32"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M 10 32 C 22 18, 30 10, 38 24 C 42 32, 48 35, 55 22 C 60 12, 65 28, 74 25 C 82 22, 90 14, 98 28 C 104 38, 115 15, 126 22 C 134 27, 142 20, 152 24"
                          stroke="#1d4ed8"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        <path
                          d="M 32 38 C 55 36, 95 34, 138 36"
                          stroke="#1d4ed8"
                          strokeWidth="1.4"
                          strokeLinecap="round"
                        />
                      </svg>
                    </div>
                    <div className="signature-title">Member Secretary, AICTE</div>
                    <div className="signature-subtitle">Competent Authority Signoff</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ===================================================================
          REVEAL SECTION 1: Autonomous Multi-Tier Scrutiny Pipeline
          =================================================================== */}
      <section className="welcome-section welcome-pipeline-section" id="verification-process">
        <div className="section-header-block scroll-reveal reveal-up">
          <div className="welcome-eyebrow">REGULATORY PIPELINE · MULTI-TIER SCRUTINY</div>
          <h2 className="section-title">Autonomous Verification Architecture</h2>
          <p className="section-subtitle">
            Every Extension of Approval (EoA) dossier undergoes multi-stage cryptographic and
            forensic scrutiny enforcing AICTE Approval Process Handbook (APH 2026-27) norms.
          </p>
        </div>

        <div className="pipeline-steps-grid">
          {/* Step 1: Ingestion */}
          <div className="pipeline-step-card scroll-reveal reveal-left delay-100">
            <div className="step-badge">
              <span className="step-num">01</span>
              <FileSearch size={18} className="step-icon" />
            </div>
            <h3 className="step-title">Dossier Ingestion &amp; OCR Extraction</h3>
            <p className="step-desc">
              High-fidelity layout-aware OCR tokenizes institutional affidavits, cadastral survey deeds,
              and fire-safety certificates, computing a SHA-256 digest immediately upon ingestion.
            </p>
            <div className="step-tag">SHA-256 Source</div>
          </div>

          {/* Step 2: Cross Matrix */}
          <div className="pipeline-step-card scroll-reveal reveal-right delay-200">
            <div className="step-badge">
              <span className="step-num">02</span>
              <Cpu size={18} className="step-icon" />
            </div>
            <h3 className="step-title">Cross-Institutional Matrix</h3>
            <p className="step-desc">
              Cross-references approved intake, teacher-to-student ratios (1:15/1:20), and principal
              credentials against regional databases to flag faculty duplication across multiple colleges.
            </p>
            <div className="step-tag">Inter-College Deduplication</div>
          </div>

          {/* Step 3: Forensic Tamper Analysis */}
          <div className="pipeline-step-card scroll-reveal reveal-left delay-300">
            <div className="step-badge">
              <span className="step-num">03</span>
              <ShieldCheck size={18} className="step-icon" />
            </div>
            <h3 className="step-title">Forensic Authenticity Analysis</h3>
            <p className="step-desc">
              Examines typographic inconsistencies, seal boundary geometry, digital signatures,
              and physical layout anomalies, flagging forged approvals or altered intake limits.
            </p>
            <div className="step-tag">Seal &amp; Stamp Geometry</div>
          </div>

          {/* Step 4: Adjudication */}
          <div className="pipeline-step-card scroll-reveal reveal-right delay-400">
            <div className="step-badge">
              <span className="step-num">04</span>
              <Scale size={18} className="step-icon" />
            </div>
            <h3 className="step-title">Auditor Adjudication Record</h3>
            <p className="step-desc">
              Human-in-the-loop review panel enables certified AICTE scrutiny officers to confirm
              exceptions, request clarifications, or log non-compliance rulings with audit logs.
            </p>
            <div className="step-tag">Tamper-Evident Ledger</div>
          </div>
        </div>
      </section>

      {/* ===================================================================
          REVEAL SECTION 2: Core Audit & Verification Capabilities
          =================================================================== */}
      <section className="welcome-section welcome-capabilities-section" id="verification-capabilities">
        <div className="section-header-block scroll-reveal reveal-up">
          <div className="welcome-eyebrow">COMPREHENSIVE AUDIT NORMS</div>
          <h2 className="section-title">Forensic Scrutiny Capabilities</h2>
          <p className="section-subtitle">
            Engineered specifically to address real-world fraud vectors in technical education
            accreditation, affiliation claims, and mandatory disclosure statements.
          </p>
        </div>

        <div className="capabilities-grid">
          {/* Capability 1 */}
          <div className="capability-card scroll-reveal reveal-left delay-100">
            <div className="capability-icon-wrap">
              <ShieldCheck size={26} />
            </div>
            <h3 className="capability-title">Forensic Document Authenticity</h3>
            <p className="capability-desc">
              Automated pixel-level inspection of government letterheads, university signatures,
              and gazette notifications.
            </p>
            <ul className="capability-features">
              <li><CheckCircle2 size={13} /> Font metric &amp; typeface tampering alerts</li>
              <li><CheckCircle2 size={13} /> Circular seal boundary geometry verification</li>
              <li><CheckCircle2 size={13} /> PDF structural metadata &amp; revision delta check</li>
            </ul>
          </div>

          {/* Capability 2 */}
          <div className="capability-card scroll-reveal reveal-up delay-200">
            <div className="capability-icon-wrap">
              <Cpu size={26} />
            </div>
            <h3 className="capability-title">Cross-Document Consistency Matrix</h3>
            <p className="capability-desc">
              Synchronous evaluation of multi-source filings to catch conflicting declarations
              across university, AICTE, and State DTE submissions.
            </p>
            <ul className="capability-features">
              <li><CheckCircle2 size={13} /> Cross-checks Affiliation Letters vs University registrar DB</li>
              <li><CheckCircle2 size={13} /> Validates Mandatory Disclosures against EoA limits</li>
              <li><CheckCircle2 size={13} /> Detects ghost faculty across inter-state colleges</li>
            </ul>
          </div>

          {/* Capability 3 */}
          <div className="capability-card scroll-reveal reveal-right delay-300">
            <div className="capability-icon-wrap">
              <Building2 size={26} />
            </div>
            <h3 className="capability-title">Infrastructure &amp; Land Audit</h3>
            <p className="capability-desc">
              Algorithmic verification of built-up instructional area, barrier-free access,
              and laboratory readiness per program intake.
            </p>
            <ul className="capability-features">
              <li><CheckCircle2 size={13} /> Instructional area vs intake ratio calculus</li>
              <li><CheckCircle2 size={13} /> Cadastral survey map &amp; title deed continuity</li>
              <li><CheckCircle2 size={13} /> Barrier-free environment (PwD) statutory check</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ===================================================================
          REVEAL SECTION 3: Regulatory Review & Governance Hierarchy
          =================================================================== */}
      <section className="welcome-section welcome-governance-section" id="application-workflow">
        <div className="section-header-block scroll-reveal reveal-up">
          <div className="welcome-eyebrow">INSTITUTIONAL GOVERNANCE</div>
          <h2 className="section-title">Application Review Workflow</h2>
          <p className="section-subtitle">
            Enforcing strict multi-level role segregation between preliminary autonomous analysis,
            Regional Scrutiny Committees, and the Member Secretary's office.
          </p>
        </div>

        <div className="governance-timeline scroll-reveal reveal-up delay-150">
          <div className="governance-node scroll-reveal reveal-left delay-100">
            <div className="node-marker">
              <span>1</span>
            </div>
            <div className="node-content">
              <div className="node-role">Level 1 · Autonomous AI Scrutiny</div>
              <h4 className="node-title">Instant Ingestion &amp; Forensic Scoring</h4>
              <p className="node-desc">
                Document parsed, digital signatures checked, and anomalies flagged against APH norms
                within 4.5 seconds per submission.
              </p>
            </div>
          </div>

          <div className="governance-connector" aria-hidden="true" />

          <div className="governance-node scroll-reveal reveal-right delay-200">
            <div className="node-marker">
              <span>2</span>
            </div>
            <div className="node-content">
              <div className="node-role">Level 2 · Regional Scrutiny Committee</div>
              <h4 className="node-title">Auditor Adjudication &amp; Hearing Review</h4>
              <p className="node-desc">
                Certified AICTE reviewers examine flagged exceptions, inspect highlighted document overlays,
                and log formal rulings with officer notes.
              </p>
            </div>
          </div>

          <div className="governance-connector" aria-hidden="true" />

          <div className="governance-node scroll-reveal reveal-left delay-300">
            <div className="node-marker">
              <span>3</span>
            </div>
            <div className="node-content">
              <div className="node-role">Level 3 · Competent Authority Signoff</div>
              <h4 className="node-title">Extension of Approval (EoA) Issuance</h4>
              <p className="node-desc">
                Member Secretary's executive sign-off, cryptographic key derivation, and formal
                QR-secured Extension of Approval issuance to the institution.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ===================================================================
          REVEAL SECTION 4: Final Call To Action Banner
          =================================================================== */}
      <section className="welcome-section welcome-cta-banner-section scroll-reveal reveal-up">
        <div className="cta-banner-inner">
          <div className="cta-banner-badge">
            <Sparkles size={14} />
            <span>SIH26261 · SMART INDIA HACKATHON GATEWAY</span>
          </div>
          <h2 className="cta-banner-title">
            Ready to Begin Institutional Scrutiny?
          </h2>
          <p className="cta-banner-desc">
            Access the official verification matrix, upload institutional affidavits, or evaluate
            curated sample dossiers under APH 2026-27 norms.
          </p>
          <div className="cta-banner-actions">
            <button
              type="button"
              onClick={onOpenExplainer || onBeginVerification}
              className="welcome-btn-primary welcome-btn-lg"
              title="Inspect technical architecture and system details"
            >
              <BookOpen size={16} />
              <span>How It Works</span>
            </button>
            {!isAuthenticated && (
              <button
                type="button"
                onClick={() => onOpenAuth('login')}
                className="welcome-btn-secondary welcome-btn-lg"
              >
                <Lock size={15} />
                <span>Auditor Sign In</span>
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Footer Navigation */}
      <footer className="welcome-footer entrance-top delay-500">
        <div>
          Enforcing AICTE Approval Process Handbook (APH 2026-27) &amp; Regulatory Audit Norms
        </div>
        <div>
          Protected by Scrypt Key Derivation &amp; JWT Token Revocation
        </div>
      </footer>
    </div>
  );
};
