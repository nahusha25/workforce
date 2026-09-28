import { apiClient } from './client';

export interface AttendanceRecord {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  site_id: string | null;
  site_name?: string | null;
  date: string;
  check_in_time: string;
  check_out_time: string | null;
  status: string;
  working_hours?: number | null;
  is_within_geofence?: boolean | null;
}

export interface CheckInPayload {
  latitude: number;
  longitude: number;
}

export interface CheckOutPayload {
  latitude: number;
  longitude: number;
}

export interface CheckOutResponse {
  status: string;
  record_id: string;
  requires_confirmation?: boolean;
  warning?: string | null;
}

export interface OverridePayload {
  override_reason: string;
}

export const getAttendanceRecords = async (date?: string): Promise<AttendanceRecord[]> => {
  const url = date ? `/attendance?date=${date}` : '/attendance';
  const response = await apiClient.get<{ data: AttendanceRecord[], total: number }>(url);
  return response.data.data;
};

export const checkIn = async (payload: CheckInPayload): Promise<AttendanceRecord> => {
  const response = await apiClient.post<AttendanceRecord>('/attendance/check-in', payload);
  return response.data;
};

export const checkOut = async (payload: CheckOutPayload): Promise<CheckOutResponse> => {
  const response = await apiClient.post<CheckOutResponse>('/attendance/check-out', payload);
  return response.data;
};

export const overrideAttendance = async (
  id: string,
  payload: OverridePayload | string
): Promise<{ status: string; record_id: string }> => {
  const body = typeof payload === 'string' ? { override_reason: payload } : payload;
  const response = await apiClient.post<{ status: string; record_id: string }>(
    `/attendance/${id}/override`,
    body
  );
  return response.data;
};

