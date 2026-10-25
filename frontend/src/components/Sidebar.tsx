import React, { useState, useRef, useEffect } from 'react';
import {
  FileText,
  CopyCheck,
  FlaskConical,
  Database,
  Activity,
  Settings,
  ChevronsRight,
  ChevronDown,
  User,
  XCircle,
} from 'lucide-react';

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
  onClearSessionDrafts,
}) => {
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsProfileOpen(false);
      }
    };
    if (isProfileOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isProfileOpen]);

  return (
    <aside className="app-sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          backgroundColor: '#b45309',
          background: 'radial-gradient(circle, #d97706 0%, #78350f 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff',
          fontWeight: 'bold',
          fontSize: '13px',
          boxShadow: '0 2px 4px rgba(120, 53, 15, 0.3)',
          flexShrink: 0,
        }}>
          ⚙
        </div>
        <div className="sidebar-text">
          <div style={{ fontSize: '15px', fontWeight: '800', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            AICTE
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1' }}>
            Verification System
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        <button
          onClick={() => onSelectDestination('single')}
          className={`sidebar-nav-item ${activeDestination === 'single' ? 'active' : ''}`}
          title="Document Verification"
        >
          <FileText size={17} style={{ color: activeDestination === 'single' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Document Verification</span>
        </button>

        <button
          onClick={() => onSelectDestination('cross')}
          className={`sidebar-nav-item ${activeDestination === 'cross' ? 'active' : ''}`}
          title="Cross-Document Checks"
        >
          <CopyCheck size={17} style={{ color: activeDestination === 'cross' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Cross-Document Checks</span>
        </button>

        <button
          onClick={() => onSelectDestination('test-cases')}
          className={`sidebar-nav-item ${activeDestination === 'test-cases' ? 'active' : ''}`}
          title="Synthetic Test Suite"
        >
          <FlaskConical size={17} style={{ color: activeDestination === 'test-cases' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Synthetic Test Suite</span>
        </button>

        <div className="sidebar-divider" />

        <button
          onClick={() => onSelectDestination('dataset')}
          className={`sidebar-nav-item ${activeDestination === 'dataset' ? 'active' : ''}`}
          title="Dataset Documents"
        >
          <Database size={17} style={{ color: activeDestination === 'dataset' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Dataset Documents</span>
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

        <button
          onClick={() => onSelectDestination('diagnostics')}
          className={`sidebar-nav-item ${activeDestination === 'diagnostics' ? 'active' : ''}`}
          title="Demo & Diagnostics"
        >
          <Activity size={17} style={{ color: activeDestination === 'diagnostics' ? 'var(--color-brand)' : 'var(--text-secondary)' }} />
          <span className="sidebar-text">Demo & Diagnostics</span>
        </button>
      </nav>

      {/* Footer Profile & Settings */}
      <div className="sidebar-footer" ref={profileRef} style={{ position: 'relative' }}>
        {/* Profile Dropdown Menu */}
        {isProfileOpen && (
          <div
            style={{
              position: 'absolute',
              bottom: 'calc(100% + 8px)',
              left: '10px',
              right: '10px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              boxShadow: 'var(--shadow-dropdown)',
              padding: '14px',
              zIndex: 50,
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            {/* Header info */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
              <div style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                backgroundColor: 'var(--bg-hover)',
                border: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-secondary)',
                flexShrink: 0,
              }}>
                <User size={17} />
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    Guest Session
                  </span>
                  <span className="badge badge-pill" style={{ fontSize: '9.5px', padding: '1px 6px', backgroundColor: 'var(--bg-hover)', color: 'var(--text-muted)' }}>
                    Unauthenticated
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Regulatory Inspection Session
                </div>
              </div>
            </div>

            {/* Session Scope Details */}
            <div style={{
              backgroundColor: 'var(--bg-surface-subtle)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '8px 10px',
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              display: 'flex',
              flexDirection: 'column',
              gap: '5px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Role:</span>
                <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Auditor (Guest)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Scope:</span>
                <span style={{ color: 'var(--text-primary)' }}>Read-Only + Drafts</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Adjudications:</span>
                <span style={{ fontWeight: '600', color: draftCount > 0 ? '#15803d' : 'var(--text-muted)' }}>
                  {draftCount > 0 ? `${draftCount} draft decision(s)` : 'None recorded'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Persistence:</span>
                <span style={{ color: '#b45309' }}>In-Memory Only</span>
              </div>
            </div>

            {/* Functional Menu Actions */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <button
                type="button"
                onClick={() => {
                  setIsProfileOpen(false);
                  onSelectDestination('settings');
                }}
                className="btn btn-secondary btn-sm"
                style={{ width: '100%', justifyContent: 'flex-start', fontSize: '11.5px', padding: '6px 10px' }}
              >
                <Settings size={13} />
                <span>Audit Settings & Thresholds</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setIsProfileOpen(false);
                  onSelectDestination('diagnostics');
                }}
                className="btn btn-secondary btn-sm"
                style={{ width: '100%', justifyContent: 'flex-start', fontSize: '11.5px', padding: '6px 10px' }}
              >
                <Activity size={13} />
                <span>Engine Diagnostics</span>
              </button>

              {onClearSessionDrafts && draftCount > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    onClearSessionDrafts();
                    setIsProfileOpen(false);
                  }}
                  className="btn btn-sm"
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    fontSize: '11.5px',
                    padding: '6px 10px',
                    backgroundColor: 'var(--color-fail-bg)',
                    color: 'var(--color-fail-text)',
                    border: '1px solid var(--color-fail-border)',
                  }}
                >
                  <XCircle size={13} />
                  <span>Clear Draft Decisions ({draftCount})</span>
                </button>
              )}
            </div>

            {/* Note */}
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', lineHeight: '1.3', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
              * No auth credentials configured. Reviewer decisions remain in local session memory.
            </div>
          </div>
        )}

        {/* Profile Trigger Button */}
        <div
          onClick={() => setIsProfileOpen(!isProfileOpen)}
          role="button"
          tabIndex={0}
          aria-expanded={isProfileOpen}
          aria-haspopup="true"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '6px 8px',
            borderRadius: '6px',
            backgroundColor: isProfileOpen ? 'var(--bg-active)' : 'var(--bg-hover)',
            cursor: 'pointer',
            border: isProfileOpen ? '1px solid var(--border-color)' : '1px solid transparent',
            transition: 'all 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              backgroundColor: 'var(--border-color)',
              color: 'var(--text-secondary)',
              fontSize: '11px',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <User size={15} />
            </div>
            <div className="sidebar-text">
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)', lineHeight: '1.2' }}>
                Guest Session
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                Not authenticated
              </div>
            </div>
          </div>
          <ChevronDown
            size={14}
            style={{
              color: 'var(--text-muted)',
              transform: isProfileOpen ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.2s ease',
            }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 4px' }}>
          <button
            onClick={() => onSelectDestination('settings')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'none',
              color: activeDestination === 'settings' ? 'var(--color-brand)' : 'var(--text-secondary)',
              fontSize: '12px',
            }}
          >
            <Settings size={15} />
            <span className="sidebar-text">Settings</span>
          </button>
          <ChevronsRight size={14} style={{ color: 'var(--text-light)', cursor: 'pointer' }} />
        </div>
      </div>
    </aside>
  );
};
