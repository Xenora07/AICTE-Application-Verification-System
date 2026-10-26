/**
 * frontend/src/context/AuthContext.tsx - React Context for AICTE Authentication & Session State.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  UserProfile,
  authApi,
  authStorage,
  GenericMessageResponse,
} from '../services/auth';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: { email: string; password: string; remember_me?: boolean }) => Promise<void>;
  register: (payload: {
    name: string;
    email: string;
    password: string;
    consent_acknowledged: boolean;
  }) => Promise<void>;
  logout: () => Promise<void>;
  requestPasswordReset: (email: string) => Promise<GenericMessageResponse>;
  resetPassword: (payload: { reset_token: string; new_password: string }) => Promise<GenericMessageResponse>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(() => authStorage.getToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Re-verify session on mount
  useEffect(() => {
    let isMounted = true;
    const verifySession = async () => {
      const storedToken = authStorage.getToken();
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
        return;
      }
      try {
        const profile = await authApi.getMe(storedToken);
        if (isMounted) {
          setUser(profile);
          setToken(storedToken);
        }
      } catch {
        // Token expired, revoked, or server restarted
        authStorage.clearToken();
        if (isMounted) {
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    verifySession();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (payload: { email: string; password: string; remember_me?: boolean }) => {
    setIsLoading(true);
    try {
      const res = await authApi.login(payload);
      authStorage.setToken(res.access_token, payload.remember_me ?? false);
      setToken(res.access_token);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: {
    name: string;
    email: string;
    password: string;
    consent_acknowledged: boolean;
  }) => {
    setIsLoading(true);
    try {
      const res = await authApi.register(payload);
      authStorage.setToken(res.access_token, false);
      setToken(res.access_token);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setToken(null);
      setIsLoading(false);
    }
  };

  const requestPasswordReset = async (email: string) => {
    return authApi.requestPasswordReset(email);
  };

  const resetPassword = async (payload: { reset_token: string; new_password: string }) => {
    return authApi.resetPassword(payload);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        logout,
        requestPasswordReset,
        resetPassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
