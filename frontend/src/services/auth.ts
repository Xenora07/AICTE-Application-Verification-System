/**
 * frontend/src/services/auth.ts - Client API for Native AICTE Authentication & User Management.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://localhost:8000/api/v1' : '/api/v1');

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
  last_login?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface GenericMessageResponse {
  message: string;
  status: string;
  delivery_note?: string;
}

export const authStorage = {
  getToken(): string | null {
    try {
      return localStorage.getItem('aicte_auth_token') || sessionStorage.getItem('aicte_auth_token');
    } catch {
      return null;
    }
  },

  setToken(token: string, rememberMe: boolean = false): void {
    try {
      if (rememberMe) {
        localStorage.setItem('aicte_auth_token', token);
        sessionStorage.removeItem('aicte_auth_token');
      } else {
        sessionStorage.setItem('aicte_auth_token', token);
        localStorage.removeItem('aicte_auth_token');
      }
    } catch {
      // Storage unavailable fallback
    }
  },

  clearToken(): void {
    try {
      localStorage.removeItem('aicte_auth_token');
      sessionStorage.removeItem('aicte_auth_token');
    } catch {
      // Storage unavailable fallback
    }
  },
};

export const authApi = {
  /** Register a new regulatory auditor */
  async register(payload: {
    name: string;
    email: string;
    password: string;
    consent_acknowledged: boolean;
  }): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Registration failed.');
    }
    return res.json();
  },

  /** Authenticate auditor with email and password */
  async login(payload: {
    email: string;
    password: string;
    remember_me?: boolean;
  }): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Invalid email or password.');
    }
    return res.json();
  },

  /** Get profile of currently authenticated user */
  async getMe(token?: string): Promise<UserProfile> {
    const authToken = token || authStorage.getToken();
    if (!authToken) {
      throw new Error('No authentication token available.');
    }
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Session expired or invalid.');
    }
    return res.json();
  },

  /** Revoke token and log out current session */
  async logout(): Promise<void> {
    const token = authStorage.getToken();
    if (token) {
      try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch {
        // Silently clear local credentials even if network fails
      }
    }
    authStorage.clearToken();
  },

  /** Request password reset email / instructions */
  async requestPasswordReset(email: string): Promise<GenericMessageResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Password reset request failed.');
    }
    return res.json();
  },

  /** Execute password reset using single-use reset token */
  async resetPassword(payload: {
    reset_token: string;
    new_password: string;
  }): Promise<GenericMessageResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: payload.reset_token,
        reset_token: payload.reset_token,
        new_password: payload.new_password,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Password reset failed or token expired.');
    }
    return res.json();
  },
};
