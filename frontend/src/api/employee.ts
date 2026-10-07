import { apiClient } from './client';
import type { SystemRole } from '../types/auth';

export interface EmployeeCreateData {
  name: string;
  mobile_number: string;
  employee_code: string;
  system_role: SystemRole;
  trade_role_ids: string[];
  rate_type: string;
  rate_amount: number;
  supervisor_id?: string | null;
  site_ids: string[];
}

export interface EmployeeResponseData {
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

export async function createEmployeeApi(data: EmployeeCreateData): Promise<EmployeeResponseData> {
  const res = await apiClient.post<EmployeeResponseData>('/employees', data);
  return res.data;
}

export async function getEmployeesApi(skip: number = 0, limit: number = 100): Promise<EmployeeResponseData[]> {
  const res = await apiClient.get<EmployeeResponseData[]>('/employees', {
    params: { skip, limit },
  });
  return res.data;
}

export async function getAllEmployeesApi(pageSize: number = 100): Promise<EmployeeResponseData[]> {
  const allEmployees: EmployeeResponseData[] = [];
  let skip = 0;

  while (true) {
    const page = await getEmployeesApi(skip, pageSize);
    allEmployees.push(...page);
    if (page.length < pageSize) {
      break;
    }
    skip += pageSize;
  }

  return allEmployees;
}

export interface EmployeeUpdateData {
  name?: string;
  mobile_number?: string;
  system_role?: SystemRole;
  trade_role_ids?: string[];
  rate_type?: string;
  rate_amount?: number;
  supervisor_id?: string | null;
  site_ids?: string[];
  is_active?: boolean;
}

export async function deleteEmployeeApi(id: string): Promise<{ status: string; message: string }> {
  const res = await apiClient.delete<{ status: string; message: string }>(`/employees/${id}`);
  return res.data;
}

export async function updateEmployeeApi(
  id: string,
  data: EmployeeUpdateData
): Promise<EmployeeResponseData> {
  const res = await apiClient.put<EmployeeResponseData>(`/employees/${id}`, data);
  return res.data;
}


