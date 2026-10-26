/**
 * frontend/src/components/auth/LoginForm.tsx - Auditor Login Form.
 */

import React, { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, LogIn, AlertCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface LoginFormProps {
  onSuccess: () => void;
  onSwitchToSignUp: () => void;
  onForgotPassword: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  onSwitchToSignUp,
  onForgotPassword,
}) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError('Please provide both email address and password.');
      return;
    }
    setIsSubmitting(true);
    try {
      await login({
        email: email.trim(),
        password,
        remember_me: rememberMe,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      {error && (
        <div className="auth-alert-error" role="alert">
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span>{error}</span>
        </div>
      )}

      {/* Email Input */}
      <div className="auth-form-group">
        <label className="auth-form-label" htmlFor="login-email">
          Institutional Email Address
        </label>
        <div className="auth-input-wrapper">
          <Mail size={16} className="input-icon" />
          <input
            id="login-email"
            type="email"
            className="auth-input"
            placeholder="auditor@aicte.gov.in"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>
      </div>

      {/* Password Input */}
      <div className="auth-form-group">
        <div className="auth-form-label">
          <label htmlFor="login-password">Password</label>
          <button
            type="button"
            className="auth-link-btn"
            onClick={onForgotPassword}
            style={{ fontSize: '11.5px', textDecoration: 'none' }}
          >
            Forgot password?
          </button>
        </div>
        <div className="auth-input-wrapper">
          <Lock size={16} className="input-icon" />
          <input
            id="login-password"
            type={showPassword ? 'text' : 'password'}
            className="auth-input"
            placeholder="Enter secure password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <button
            type="button"
            className="auth-toggle-pwd-btn"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </div>

      {/* Remember Me */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px' }}>
        <input
          id="remember-me-checkbox"
          type="checkbox"
          checked={rememberMe}
          onChange={(e) => setRememberMe(e.target.checked)}
          style={{ accentColor: 'var(--color-brand)', cursor: 'pointer' }}
        />
        <label htmlFor="remember-me-checkbox" style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}>
          Remember this session on this workstation
        </label>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        className="auth-submit-btn"
        disabled={isSubmitting}
        id="login-submit-btn"
      >
        <LogIn size={15} />
        <span>{isSubmitting ? 'Authenticating...' : 'Sign In as Auditor'}</span>
      </button>

      {/* Footer Nav */}
      <div className="auth-footer-nav">
        <span>New regulatory officer?</span>
        <button
          type="button"
          className="auth-link-btn"
          onClick={onSwitchToSignUp}
        >
          Create an auditor account
        </button>
      </div>
    </form>
  );
};
