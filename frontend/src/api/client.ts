import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type { ApiErrorResponse } from '../types/auth';

const API_BASE_URL = '/api/v1';

let memoryAccessToken: string | null = localStorage.getItem('access_token');

export const setAccessToken = (token: string | null) => {
  memoryAccessToken = token;
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    localStorage.removeItem('access_token');
  }
};

export const getAccessToken = (): string | null => {
  return memoryAccessToken;
};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Crucial for sending httpOnly refresh_token cookie
});

// Request Interceptor: Attach Bearer token
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Flag to prevent infinite 401 retry loops
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Response Interceptor: 401 Token Refresh & Error Normalization
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorResponse>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      // Don't retry refresh calls themselves
      if (originalRequest.url?.includes('/auth/refresh') || originalRequest.url?.includes('/auth/otp/verify')) {
        return Promise.reject(normalizeError(error));
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              resolve(apiClient(originalRequest));
            },
            reject: (err) => reject(err),
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshResponse = await axios.post<{ access_token: string }>(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );

        const newAccessToken = refreshResponse.data.access_token;
        setAccessToken(newAccessToken);
        processQueue(null, newAccessToken);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        }
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        setAccessToken(null);
        return Promise.reject(normalizeError(error));
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(normalizeError(error));
  }
);

export function normalizeError(error: AxiosError<ApiErrorResponse>): { code: string; message: string; details: Record<string, unknown> } {
  if (error.response?.data?.error) {
    return {
      code: error.response.data.error.code || 'UNKNOWN_ERROR',
      message: error.response.data.error.message || 'An error occurred',
      details: error.response.data.error.details || {},
    };
  }

  // Handle FastAPI default HTTP exception format
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    const message = typeof detail === 'string' ? detail : 'Validation Error';
    return {
      code: `HTTP_${error.response.status}`,
      message: message,
      details: typeof detail === 'object' ? { errors: detail } : {},
    };
  }

  if (error.response) {
    return {
      code: `HTTP_${error.response.status}`,
      message: error.response.statusText || 'Server error',
      details: {},
    };
  }

  if (error.request) {
    return {
      code: 'NETWORK_ERROR',
      message: 'Network error — please check your connectivity',
      details: {},
    };
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: error.message || 'An unexpected error occurred',
    details: {},
  };
}
