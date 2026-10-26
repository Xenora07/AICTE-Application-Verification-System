/**
 * frontend/src/components/auth/SignUpForm.tsx - Auditor Registration Form.
 * Includes dynamic password strength meter and regulatory consent acknowledgment.
 */

import React, { useState, useMemo } from 'react';
import { User, Mail, Lock, Eye, EyeOff, UserPlus, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface SignUpFormProps {
  onSuccess: () => void;
  onSwitchToLogin: () => void;
}

export const SignUpForm: React.FC<SignUpFormProps> = ({
  onSuccess,
  onSwitchToLogin,
}) => {
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [consent, setConsent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Compute password strength score (0-4)
  const passwordStrength = useMemo(() => {
    if (!password) return { score: 0, label: 'None', color: 'transparent', percent: 0 };
    let score = 0;
    if (password.length >= 8) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[a-z]/.test(password) && /\d/.test(password)) score += 1;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 1;

    switch (score) {
      case 1:
        return { score: 1, label: 'Weak', color: '#ef4444', percent: 25 };
      case 2:
        return { score: 2, label: 'Fair', color: '#f59e0b', percent: 50 };
      case 3:
        return { score: 3, label: 'Good', color: '#3b82f6', percent: 75 };
      case 4:
        return { score: 4, label: 'Strong & Compliant', color: '#10b981', percent: 100 };
      default:
        return { score: 0, label: 'Too Weak', color: '#ef4444', percent: 10 };
    }
  }, [password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Please provide your full official name.');
      return;
    }
    if (!email.trim()) {
      setError('Please provide an official institutional email address.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (!consent) {
      setError('You must acknowledge regulatory auditing obligations under AICTE norms.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        consent_acknowledged: consent,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
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

      {/* Name Input */}
      <div className="auth-form-group">
        <label className="auth-form-label" htmlFor="register-name">
          Full Official Name & Title
        </label>
        <div className="auth-input-wrapper">
          <User size={16} className="input-icon" />
          <input
            id="register-name"
            type="text"
            className="auth-input"
            placeholder="e.g., Dr. Ananya Sen, Scrutiny Officer"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoComplete="name"
          />
        </div>
      </div>

      {/* Email Input */}
      <div className="auth-form-group">
        <label className="auth-form-label" htmlFor="register-email">
          Institutional Email Address
        </label>
        <div className="auth-input-wrapper">
          <Mail size={16} className="input-icon" />
          <input
            id="register-email"
            type="email"
            className="auth-input"
            placeholder="officer@aicte-india.org"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>
      </div>

      {/* Password Input */}
      <div className="auth-form-group">
        <label className="auth-form-label" htmlFor="register-password">
          Password (Min. 8 characters, uppercase, digit, symbol)
        </label>
        <div className="auth-input-wrapper">
          <Lock size={16} className="input-icon" />
          <input
            id="register-password"
            type={showPassword ? 'text' : 'password'}
            className="auth-input"
            placeholder="Create compliant password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
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

        {/* Strength Meter */}
        {password && (
          <div className="pwd-strength-container">
            <div className="pwd-strength-bar-bg">
              <div
                className="pwd-strength-bar-fill"
                style={{
                  width: `${passwordStrength.percent}%`,
                  backgroundColor: passwordStrength.color,
                }}
              />
            </div>
            <div className="pwd-strength-label" style={{ color: passwordStrength.color }}>
              <span>Strength</span>
              <span>{passwordStrength.label}</span>
            </div>
          </div>
        )}
      </div>

      {/* Confirm Password */}
      <div className="auth-form-group">
        <label className="auth-form-label" htmlFor="register-confirm-password">
          Confirm Password
        </label>
        <div className="auth-input-wrapper">
          <Lock size={16} className="input-icon" />
          <input
            id="register-confirm-password"
            type={showPassword ? 'text' : 'password'}
            className="auth-input"
            placeholder="Re-enter password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
        </div>
      </div>

      {/* Compliance Terms Checkbox */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '11.5px', marginTop: '2px' }}>
        <input
          id="regulatory-consent-checkbox"
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          style={{ accentColor: 'var(--color-brand)', marginTop: '2px', cursor: 'pointer' }}
          required
        />
        <label htmlFor="regulatory-consent-checkbox" style={{ color: 'var(--text-secondary)', cursor: 'pointer', lineHeight: '1.4' }}>
          I certify that I am an authorized regulatory auditor and agree to maintain confidentiality of institutional evaluation records in compliance with AICTE norms.
        </label>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        className="auth-submit-btn"
        disabled={isSubmitting || !consent}
        id="register-submit-btn"
      >
        <UserPlus size={15} />
        <span>{isSubmitting ? 'Registering...' : 'Register Auditor Account'}</span>
      </button>

      {/* Footer Nav */}
      <div className="auth-footer-nav">
        <span>Already have an auditor account?</span>
        <button
          type="button"
          className="auth-link-btn"
          onClick={onSwitchToLogin}
        >
          Sign in
        </button>
      </div>
    </form>
  );
};
