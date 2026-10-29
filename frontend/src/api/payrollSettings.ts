import { apiClient } from './client';

export interface PayrollOvertimeSettingsResponse {
  id: string;
  standard_workday_hours: string | number;
  overtime_multiplier: string | number;
  effective_from: string;
  effective_to?: string | null;
  description?: string | null;
  created_by?: string | null;
  created_at: string;
}

export interface PayrollOvertimeSettingsCreateRequest {
  standard_workday_hours: number;
  overtime_multiplier: number;
  effective_from: string;
  description?: string;
}

export async function getOvertimeSettingsHistoryApi(): Promise<PayrollOvertimeSettingsResponse[]> {
  const res = await apiClient.get<PayrollOvertimeSettingsResponse[]>('/payroll-settings/overtime');
  return res.data;
}

export async function getEffectiveOvertimeSettingApi(date?: string): Promise<PayrollOvertimeSettingsResponse> {
  const res = await apiClient.get<PayrollOvertimeSettingsResponse>('/payroll-settings/overtime/effective', {
    params: date ? { date } : undefined,
  });
  return res.data;
}

export async function createOvertimeSettingApi(
  data: PayrollOvertimeSettingsCreateRequest
): Promise<PayrollOvertimeSettingsResponse> {
  const res = await apiClient.post<PayrollOvertimeSettingsResponse>('/payroll-settings/overtime', data);
  return res.data;
}
