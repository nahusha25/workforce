import { apiClient } from './client';
import type { EmployeeProfile, TokenResponse } from '../types/auth';

export async function requestOtpApi(mobile: string): Promise<{ message: string }> {
  const res = await apiClient.post<{ message: string }>('/auth/otp/request', { mobile });
  return res.data;
}

export async function verifyOtpApi(mobile: string, otp: string): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>('/auth/otp/verify', { mobile, otp });
  return res.data;
}

export async function refreshTokenApi(): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>('/auth/refresh');
  return res.data;
}

export async function logoutApi(): Promise<{ message: string }> {
  const res = await apiClient.post<{ message: string }>('/auth/logout');
  return res.data;
}

export async function getProfileApi(): Promise<EmployeeProfile> {
  const res = await apiClient.get<EmployeeProfile>('/employees/me');
  return res.data;
}
