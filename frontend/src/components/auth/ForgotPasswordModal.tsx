/**
 * frontend/src/components/auth/ForgotPasswordModal.tsx - Password Recovery Flow.
 * Handles both requesting reset instructions and consuming reset tokens.
 * Accurately communicates email delivery status without false claims.
 */

import React, { useState } from 'react';
import { Mail, KeyRound, Lock, ArrowLeft, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface ForgotPasswordModalProps {
  onBackToLogin: () => void;
  onSuccessReset: () => void;
}

export const ForgotPasswordModal: React.FC<ForgotPasswordModalProps> = ({
  onBackToLogin,
  onSuccessReset,
}) => {
  const { requestPasswordReset, resetPassword } = useAuth();
  const [step, setStep] = useState<'request' | 'reset'>('request');
  const [email, setEmail] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [feedback, setFeedback] = useState<{ message: string; note?: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFeedback(null);
    if (!email.trim()) {
      setError('Please provide your institutional email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await requestPasswordReset(email.trim());
      setFeedback({
        message: res.message,
        note: res.delivery_note,
      });
    } catch (err: any) {
      setError(err.message || 'Unable to request password reset.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!resetToken.trim()) {
      setError('Please enter the reset token.');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await resetPassword({
        reset_token: resetToken.trim(),
        new_password: newPassword,
      });
      onSuccessReset();
    } catch (err: any) {
      setError(err.message || 'Password reset failed or token is invalid/expired.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-form">
      {error && (
        <div className="auth-alert-error" role="alert">
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span>{error}</span>
        </div>
      )}

      {step === 'request' ? (
        <form onSubmit={handleRequestSubmit} className="auth-form">
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.5' }}>
            Enter your registered institutional email. If registered, a time-limited single-use security token will be generated.
          </p>

          {feedback ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div className="auth-alert-success" role="status">
                <CheckCircle2 size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontWeight: 600 }}>{feedback.message}</div>
                  {feedback.note && (
                    <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.9 }}>
                      {feedback.note}
                    </div>
                  )}
                </div>
              </div>

              <div style={{
                backgroundColor: 'var(--bg-surface-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px',
                fontSize: '11.5px',
                color: 'var(--text-secondary)',
                lineHeight: '1.4',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  <Info size={14} />
                  <span>Email Configuration Note</span>
                </div>
                External SMTP delivery is unconfigured in development. The single-use reset token has been dispatched safely to the server console log for security auditing.
              </div>

              <button
                type="button"
                className="auth-submit-btn"
                onClick={() => setStep('reset')}
              >
                <KeyRound size={15} />
                <span>Enter Reset Token & Set Password</span>
              </button>
            </div>
          ) : (
            <>
              <div className="auth-form-group">
                <label className="auth-form-label" htmlFor="forgot-email">
                  Institutional Email
                </label>
                <div className="auth-input-wrapper">
                  <Mail size={16} className="input-icon" />
                  <input
                    id="forgot-email"
                    type="email"
                    className="auth-input"
                    placeholder="auditor@aicte.gov.in"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={isSubmitting}
              >
                <span>{isSubmitting ? 'Requesting...' : 'Request Password Reset'}</span>
              </button>

              <div style={{ textAlign: 'center', marginTop: '4px' }}>
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={() => setStep('reset')}
                  style={{ fontSize: '12px' }}
                >
                  Already have a reset token? Enter it here
                </button>
              </div>
            </>
          )}

          <div className="auth-footer-nav" style={{ marginTop: '8px' }}>
            <button
              type="button"
              className="auth-link-btn"
              onClick={onBackToLogin}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', textDecoration: 'none' }}
            >
              <ArrowLeft size={13} />
              <span>Back to Sign In</span>
            </button>
          </div>
        </form>
      ) : (
        <form onSubmit={handleResetSubmit} className="auth-form">
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.5' }}>
            Enter the 64-character security token along with your new compliant password.
          </p>

          {/* Reset Token Input */}
          <div className="auth-form-group">
            <label className="auth-form-label" htmlFor="reset-token">
              Security Reset Token
            </label>
            <div className="auth-input-wrapper">
              <KeyRound size={16} className="input-icon" />
              <input
                id="reset-token"
                type="text"
                className="auth-input"
                placeholder="Paste reset token from terminal log"
                value={resetToken}
                onChange={(e) => setResetToken(e.target.value)}
                required
                style={{ fontFamily: 'monospace', fontSize: '12px' }}
              />
            </div>
          </div>

          {/* New Password */}
          <div className="auth-form-group">
            <label className="auth-form-label" htmlFor="reset-new-password">
              New Password (Min. 8 characters)
            </label>
            <div className="auth-input-wrapper">
              <Lock size={16} className="input-icon" />
              <input
                id="reset-new-password"
                type="password"
                className="auth-input"
                placeholder="Enter new strong password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Confirm New Password */}
          <div className="auth-form-group">
            <label className="auth-form-label" htmlFor="reset-confirm-password">
              Confirm New Password
            </label>
            <div className="auth-input-wrapper">
              <Lock size={16} className="input-icon" />
              <input
                id="reset-confirm-password"
                type="password"
                className="auth-input"
                placeholder="Re-enter new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={isSubmitting}
          >
            <span>{isSubmitting ? 'Updating...' : 'Update Password & Sign In'}</span>
          </button>

          <div className="auth-footer-nav" style={{ marginTop: '8px' }}>
            <button
              type="button"
              className="auth-link-btn"
              onClick={() => setStep('request')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', textDecoration: 'none' }}
            >
              <ArrowLeft size={13} />
              <span>Back to Request Reset</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
