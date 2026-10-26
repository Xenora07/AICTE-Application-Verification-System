/**
 * frontend/src/components/auth/AuthPage.tsx - Container for Login, Registration & Password Recovery.
 */

import React, { useState } from 'react';
import { Shield, ArrowLeft, Sun, Moon, CheckCircle2 } from 'lucide-react';
import { LoginForm } from './LoginForm';
import { SignUpForm } from './SignUpForm';
import { ForgotPasswordModal } from './ForgotPasswordModal';
import aicteLogo from '../../assets/aicte_logo.png';
import '../../styles/Auth.css';

interface AuthPageProps {
  initialMode?: 'login' | 'signup';
  onAuthSuccess: () => void;
  onBackToWelcome: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

export const AuthPage: React.FC<AuthPageProps> = ({
  initialMode = 'login',
  onAuthSuccess,
  onBackToWelcome,
  theme,
  onToggleTheme,
}) => {
  const [mode, setMode] = useState<'login' | 'signup' | 'forgot' | 'reset-success'>(initialMode);

  return (
    <div className="auth-page-container">
      {/* Top Header */}
      <header className="auth-header">
        <button
          type="button"
          onClick={onBackToWelcome}
          className="btn btn-secondary btn-sm"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <ArrowLeft size={14} />
          <span>Back to Welcome</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={onToggleTheme}
            className="btn btn-secondary btn-sm"
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          >
            {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
          </button>
        </div>
      </header>

      {/* Main Card Wrapper */}
      <div className="auth-card-wrapper">
        <div className="auth-card">
          <div className="auth-card-header">
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '14px' }}>
              <img
                src={aicteLogo}
                alt="AICTE Emblem"
                style={{
                  width: '52px',
                  height: '52px',
                  objectFit: 'contain',
                  display: 'block',
                }}
              />
            </div>

            <div className="auth-card-badge">
              <Shield size={12} />
              <span>SIH26261 Security Gateway</span>
            </div>

            <h2 className="auth-card-title">
              {mode === 'login' && 'Auditor Portal Access'}
              {mode === 'signup' && 'Register Auditor Profile'}
              {mode === 'forgot' && 'Reset Security Credentials'}
              {mode === 'reset-success' && 'Password Updated'}
            </h2>

            <p className="auth-card-subtitle">
              {mode === 'login' && 'Sign in to access document verification, cross-checks, and adjudication records.'}
              {mode === 'signup' && 'Join the regulatory scrutiny panel. Accounts are provisioned under AICTE oversight.'}
              {mode === 'forgot' && 'Follow the secure verification process to recover your auditor credentials.'}
              {mode === 'reset-success' && 'Your password has been securely reset. You can now log in.'}
            </p>
          </div>

          {/* Form Rendering */}
          {mode === 'login' && (
            <LoginForm
              onSuccess={onAuthSuccess}
              onSwitchToSignUp={() => setMode('signup')}
              onForgotPassword={() => setMode('forgot')}
            />
          )}

          {mode === 'signup' && (
            <SignUpForm
              onSuccess={onAuthSuccess}
              onSwitchToLogin={() => setMode('login')}
            />
          )}

          {mode === 'forgot' && (
            <ForgotPasswordModal
              onBackToLogin={() => setMode('login')}
              onSuccessReset={() => setMode('reset-success')}
            />
          )}

          {mode === 'reset-success' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="auth-alert-success">
                <CheckCircle2 size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                <span>Your credentials have been updated successfully. Please sign in with your new password.</span>
              </div>
              <button
                type="button"
                className="auth-submit-btn"
                onClick={() => setMode('login')}
              >
                Proceed to Sign In
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
