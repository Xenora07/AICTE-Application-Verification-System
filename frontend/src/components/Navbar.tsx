import React, { useState, useRef, useEffect } from 'react';
import { Database, Upload, Sun, Moon, User, Settings, Activity, ChevronDown, XCircle, LogOut, LogIn } from 'lucide-react';
import { SystemHealth } from '../types/api';

interface NavbarProps {
  health: SystemHealth | null;
  onRefreshHealth: () => void;
  datasetCount: number;
  onOpenUpload: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  draftCount?: number;
  onClearSessionDrafts?: () => void;
  onSelectDestination?: (dest: any) => void;
  user?: { id: string; name: string; email: string; role: string } | null;
  onSignOut?: () => void;
  onOpenAuth?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  onRefreshHealth,
  datasetCount,
  onOpenUpload,
  theme,
  onToggleTheme,
  draftCount = 0,
  onClearSessionDrafts,
  onSelectDestination,
  user,
  onSignOut,
  onOpenAuth,
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
    <header className="app-header">
      {/* Title & Tagline */}
      <div>
        <h1 style={{
          fontSize: '17px',
          fontWeight: '700',
          letterSpacing: '-0.02em',
          color: 'var(--text-primary)',
          lineHeight: '1.2',
        }}>
          AICTE Application Verification System
        </h1>
        <p style={{
          fontSize: '11.5px',
          color: 'var(--text-secondary)',
          marginTop: '2px',
        }}>
          Check Rules • Verify Documents • Find Mismatches
        </p>
      </div>

      {/* Status, Counters & CTAs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Backend Online status indicator */}
        <div
          onClick={onRefreshHealth}
          title={`Click to re-check API health • Engine: ${
            health?.ocr_engine === 'synthetic_test_engine'
              ? 'Standard Rule & OCR Engine'
              : health?.ocr_engine || 'Regulatory Pipeline'
          }`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '7px',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '4px 10px',
            borderRadius: '999px',
            backgroundColor: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <span
            className={health?.status === 'healthy' ? 'status-dot-pulse' : ''}
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              backgroundColor: health?.status === 'healthy' ? '#22c55e' : health ? '#ef4444' : '#f59e0b',
              display: 'inline-block',
              boxShadow: health?.status === 'healthy' ? '0 0 6px #22c55e' : '0 0 6px #f59e0b',
            }}
          />
          <span style={{ fontWeight: '500' }}>
            {health?.status === 'healthy'
              ? 'System Online'
              : health
              ? `Status: ${health.status}`
              : 'Connecting...'}
          </span>
        </div>

        {/* Theme button */}
        <button
          type="button"
          onClick={onToggleTheme}
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? <Sun size={15} style={{ color: '#f59e0b' }} /> : <Moon size={15} />}
        </button>

        {/* Guest / Auditor Profile Dropdown in Header */}
        <div style={{ position: 'relative' }} ref={profileRef}>
          <button
            type="button"
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px 4px 6px',
              borderRadius: '999px',
              backgroundColor: isProfileOpen ? 'var(--bg-active)' : 'var(--bg-hover)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'background-color 0.15s ease',
            }}
            title={user ? `Reviewer Profile: ${user.name} (${user.email})` : 'Guest Access • View Only'}
            aria-expanded={isProfileOpen}
            aria-haspopup="true"
          >
            <div style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
              backgroundColor: user ? 'var(--color-brand)' : 'var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: user ? '#ffffff' : 'var(--text-secondary)',
              fontSize: '11px',
              fontWeight: '700',
            }}>
              {user ? user.name.charAt(0).toUpperCase() : <User size={13} />}
            </div>
            <span style={{ fontSize: '11.5px', fontWeight: '600' }}>
              {user ? user.name.split(' ')[0] : 'Guest'}
            </span>
            <ChevronDown
              size={12}
              style={{
                color: 'var(--text-muted)',
                transform: isProfileOpen ? 'rotate(180deg)' : 'none',
                transition: 'transform 0.2s ease',
              }}
            />
          </button>

          {isProfileOpen && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                right: 0,
                width: '280px',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                boxShadow: 'var(--shadow-dropdown)',
                padding: '14px',
                zIndex: 60,
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              {/* Header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
                <div style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '50%',
                  backgroundColor: user ? 'var(--color-brand)' : 'var(--bg-hover)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: user ? '#ffffff' : 'var(--text-secondary)',
                  fontWeight: '700',
                  fontSize: '14px',
                  flexShrink: 0,
                }}>
                  {user ? user.name.charAt(0).toUpperCase() : <User size={17} />}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {user ? user.name : 'Guest Access'}
                    </span>
                    <span className="badge badge-pill" style={{
                      fontSize: '9px',
                      padding: '1px 5px',
                      backgroundColor: user ? '#dcfce7' : 'var(--bg-hover)',
                      color: user ? '#15803d' : 'var(--text-muted)',
                    }}>
                      {user ? 'Authenticated' : 'Unauthenticated'}
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user ? user.email : 'View Only'}
                  </div>
                </div>
              </div>

              {/* Status details */}
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
                  <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                    {user ? `${user.role.charAt(0).toUpperCase() + user.role.slice(1)} (Official)` : 'Auditor (Guest)'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Adjudications:</span>
                  <span style={{ fontWeight: '600', color: draftCount > 0 ? '#15803d' : 'var(--text-muted)' }}>
                    {draftCount > 0 ? `${draftCount} draft(s)` : 'None'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Persistence:</span>
                  <span style={{ color: user ? '#15803d' : '#b45309' }}>
                    {user ? 'JWT Verified' : 'In-Memory Session'}
                  </span>
                </div>
              </div>

              {/* Functional Actions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                {onSelectDestination && (
                  <>
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
                      <span>Audit Settings</span>
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
                      <span>Diagnostics</span>
                    </button>
                  </>
                )}

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
                    <span>Clear Drafts ({draftCount})</span>
                  </button>
                )}

                {user && onSignOut && (
                  <button
                    type="button"
                    onClick={() => {
                      setIsProfileOpen(false);
                      onSignOut();
                    }}
                    className="btn btn-secondary btn-sm"
                    style={{
                      width: '100%',
                      justifyContent: 'flex-start',
                      fontSize: '11.5px',
                      padding: '6px 10px',
                      color: '#b91c1c',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    <LogOut size={13} />
                    <span>Sign Out</span>
                  </button>
                )}

                {!user && onOpenAuth && (
                  <button
                    type="button"
                    onClick={() => {
                      setIsProfileOpen(false);
                      onOpenAuth();
                    }}
                    className="btn btn-primary btn-sm"
                    style={{ width: '100%', justifyContent: 'center', fontSize: '11.5px', padding: '6px 10px' }}
                  >
                    <LogIn size={13} />
                    <span>Sign In</span>
                  </button>
                )}
              </div>

              <div style={{ fontSize: '10px', color: 'var(--text-muted)', lineHeight: '1.3', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
                {user
                  ? '* Auditor session active with cryptographic token verification.'
                  : '* Decisions are stored in session memory and not sent to a remote database.'}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
