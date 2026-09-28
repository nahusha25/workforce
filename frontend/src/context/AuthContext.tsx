import React, { createContext, useContext, useEffect, useState } from 'react';
import { getProfileApi, logoutApi, requestOtpApi, refreshTokenApi, verifyOtpApi } from '../api/auth';
import { getAccessToken, setAccessToken } from '../api/client';
import type { EmployeeProfile, SystemRole } from '../types/auth';

interface AuthContextType {
  user: EmployeeProfile | null;
  role: SystemRole | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  requestOtp: (mobile: string) => Promise<void>;
  verifyOtp: (mobile: string, otp: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<EmployeeProfile | null>(null);
  const [accessToken, setAccessTokenState] = useState<string | null>(getAccessToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const role: SystemRole | null = user?.system_role || null;
  const isAuthenticated = !!accessToken && !!user;

  const fetchProfile = async () => {
    try {
      const profile = await getProfileApi();
      setUser(profile);
    } catch {
      setUser(null);
      setAccessToken(null);
      setAccessTokenState(null);
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const token = getAccessToken();
      if (token) {
        setAccessTokenState(token);
        await fetchProfile();
      } else {
        // Try refresh token from httpOnly cookie
        try {
          const res = await refreshTokenApi();
          if (res.access_token) {
            setAccessToken(res.access_token);
            setAccessTokenState(res.access_token);
            await fetchProfile();
          }
        } catch {
          // No active session
          setUser(null);
          setAccessToken(null);
          setAccessTokenState(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const requestOtp = async (mobile: string) => {
    setError(null);
    try {
      await requestOtpApi(mobile);
    } catch (err: any) {
      setError(err.message || 'Failed to send OTP');
      throw err;
    }
  };

  const verifyOtp = async (mobile: string, otp: string) => {
    setError(null);
    try {
      const res = await verifyOtpApi(mobile, otp);
      setAccessToken(res.access_token);
      setAccessTokenState(res.access_token);
      await fetchProfile();
    } catch (err: any) {
      setError(err.message || 'Failed to verify OTP');
      throw err;
    }
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch {
      // Ignore logout errors
    } finally {
      setAccessToken(null);
      setAccessTokenState(null);
      setUser(null);
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        accessToken,
        isAuthenticated,
        isLoading,
        error,
        requestOtp,
        verifyOtp,
        logout,
        clearError,
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
