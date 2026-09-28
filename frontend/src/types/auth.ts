export type SystemRole = 'administrator' | 'director' | 'supervisor' | 'employee';

export interface User {
  id: string;
  mobile_id: string;
  role: SystemRole;
  is_active: boolean;
}

export interface EmployeeProfile {
  id: string;
  user_id: string;
  employee_code: string;
  mobile_id: string;
  name: string;
  system_role: SystemRole;
  supervisor_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  trade_roles: Array<{ id: string; name: string }>;
  current_rate?: {
    id: string;
    rate_type: string;
    rate_amount: number;
    effective_from: string;
    effective_to?: string | null;
  } | null;
  active_sites: Array<{ id: string; name: string }>;
}

export interface TokenResponse {
  access_token: string;
  token_type?: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error?: ApiErrorDetail;
  detail?: string | Record<string, unknown> | Array<Record<string, unknown>>;
}
