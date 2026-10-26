import React, { useState, useEffect } from 'react';
import {
  FileText,
  CopyCheck,
  FlaskConical,
  Database,
  Activity,
  Settings,
  ChevronDown,
  Code2,
} from 'lucide-react';
import aicteLogo from '../assets/aicte_logo.png';

export type MainNavDestination =
  | 'single'
  | 'cross'
  | 'test-cases'
  | 'dataset'
  | 'diagnostics'
  | 'settings';

interface SidebarProps {
  activeDestination: MainNavDestination;
  onSelectDestination: (dest: MainNavDestination) => void;
  datasetCount?: number;
  draftCount?: number;
  onClearSessionDrafts?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeDestination,
  onSelectDestination,
  datasetCount,
  draftCount = 0,
}) => {
  const isDevActive = activeDestination === 'test-cases' || activeDestination === 'diagnostics';
  const [isDevOpen, setIsDevOpen] = useState(isDevActive);

  // Automatically expand if user navigates to a developer destination
  useEffect(() => {
    if (isDevActive) {
      setIsDevOpen(true);
    }
  }, [isDevActive]);

  return (
    <aside className="app-sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <img
          src={aicteLogo}
          alt="AICTE Emblem"
          style={{
            width: '32px',
            height: '32px',
            objectFit: 'contain',
            flexShrink: 0,
            display: 'block',
          }}
        />
        <div className="sidebar-text">
          <div style={{ fontSize: '15px', fontWeight: '800', letterSpacing: '-0.02em', color: 'var(--text-primary)', lineHeight: '1.2' }}>
            AICTE
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.2', marginTop: '1px' }}>
            Verification System
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        {/* Core Review Workflows */}
        <button
          onClick={() => onSelectDestination('single')}
          className={`sidebar-nav-item ${activeDestination === 'single' ? 'active' : ''}`}
          title="Verify a Document"
        >
          <FileText size={17} style={{ color: activeDestination === 'single' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Verify Document</span>
        </button>

        <button
          onClick={() => onSelectDestination('cross')}
          className={`sidebar-nav-item ${activeDestination === 'cross' ? 'active' : ''}`}
          title="Compare Documents"
        >
          <CopyCheck size={17} style={{ color: activeDestination === 'cross' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Compare Documents</span>
        </button>

        <button
          onClick={() => onSelectDestination('dataset')}
          className={`sidebar-nav-item ${activeDestination === 'dataset' ? 'active' : ''}`}
          title="Sample Documents"
        >
          <Database size={17} style={{ color: activeDestination === 'dataset' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Sample Documents</span>
          {datasetCount !== undefined && datasetCount > 0 && (
            <span style={{
              marginLeft: 'auto',
              fontSize: '10px',
              padding: '1px 6px',
              borderRadius: '999px',
              backgroundColor: 'var(--border-subtle)',
              color: 'var(--text-secondary)',
              fontWeight: '600',
            }}>
              {datasetCount}
            </span>
          )}
        </button>

        <div className="sidebar-divider" />

        {/* Developer & System Tools Collapsible Section */}
        <div>
          <button
            type="button"
            onClick={() => setIsDevOpen(!isDevOpen)}
            className="sidebar-section-header"
            style={{
              width: '100%',
              background: 'none',
              border: 'none',
              textAlign: 'left',
              padding: '6px 12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: isDevActive ? 'var(--color-brand)' : 'var(--text-muted)',
            }}
            title="Toggle Developer & System tools"
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <Code2 size={13} />
              <span>Developer Tools</span>
            </span>
            <ChevronDown
              size={13}
              style={{
                transform: isDevOpen ? 'rotate(0deg)' : 'rotate(-90deg)',
                transition: 'transform 0.15s ease',
              }}
            />
          </button>

          {isDevOpen && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginTop: '4px', paddingLeft: '8px' }}>
              <button
                onClick={() => onSelectDestination('test-cases')}
                className={`sidebar-nav-item ${activeDestination === 'test-cases' ? 'active' : ''}`}
                style={{ fontSize: '12.5px', padding: '8px 10px' }}
                title="Test Tools"
              >
                <FlaskConical size={16} style={{ color: activeDestination === 'test-cases' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
                <span className="sidebar-text">Test Tools</span>
              </button>

              <button
                onClick={() => onSelectDestination('diagnostics')}
                className={`sidebar-nav-item ${activeDestination === 'diagnostics' ? 'active' : ''}`}
                style={{ fontSize: '12.5px', padding: '8px 10px' }}
                title="System Checks"
              >
                <Activity size={16} style={{ color: activeDestination === 'diagnostics' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
                <span className="sidebar-text">System Checks</span>
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Streamlined Footer: Settings & Session Status */}
      <div className="sidebar-footer">
        <button
          onClick={() => onSelectDestination('settings')}
          className={`sidebar-nav-item ${activeDestination === 'settings' ? 'active' : ''}`}
          style={{ width: '100%' }}
          title="Settings"
        >
          <Settings size={16} style={{ color: activeDestination === 'settings' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Settings</span>
        </button>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '7px 9px',
            borderRadius: '6px',
            backgroundColor: 'var(--bg-surface-subtle)',
            fontSize: '11px',
            color: 'var(--text-muted)',
            border: '1px solid var(--border-subtle)',
          }}
          title="Guest Access • View Only"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0 }}>
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: '#10b981',
                flexShrink: 0,
              }}
            />
            <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <span style={{ fontWeight: '600', color: 'var(--text-secondary)' }}>Guest Access</span>
            </div>
          </div>
          {draftCount > 0 ? (
            <span
              style={{
                fontSize: '9.5px',
                padding: '1px 5px',
                borderRadius: '4px',
                backgroundColor: 'var(--color-pass-bg)',
                color: 'var(--color-pass-text)',
                fontWeight: '700',
                whiteSpace: 'nowrap',
              }}
              title={`${draftCount} active draft decision(s)`}
            >
              {draftCount} {draftCount === 1 ? 'draft' : 'drafts'}
            </span>
          ) : (
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>View Only</span>
          )}
        </div>
      </div>
    </aside>
  );
};
