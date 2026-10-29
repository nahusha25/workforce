import { apiClient } from './client';

export interface RateBandSummaryResponse {
  rate_type: string;
  rate_amount: number;
  rate_effective_from: string;
  rate_effective_to?: string | null;
  approved_days: number;
  approved_quantity: number;
  gross_amount: number;
}

export interface EmployeePaymentLineResponse {
  id: string;
  payment_id: string;
  source_attendance_id?: string | null;
  source_daily_work_entry_id?: string | null;
  source_date: string;
  rate_type: string;
  rate_amount: number;
  rate_effective_from: string;
  rate_effective_to?: string | null;
  days: number;
  quantity: number;
  regular_hours?: number | null;
  overtime_hours?: number | null;
  standard_day_hours?: number | null;
  hourly_equivalent_rate?: number | null;
  overtime_multiplier?: number | null;
  regular_amount?: number | null;
  overtime_amount?: number | null;
  amount: number;
  is_active: boolean;
  created_at: string;
}

export interface EmployeePaymentResponse {
  id: string;
  payment_number: string;
  idempotency_key: string;
  employee_id: string;
  employee_name?: string | null;
  period_start: string;
  period_end: string;
  status: 'draft' | 'approved' | 'paid' | 'cancelled';
  total_amount: number;
  total_regular_amount?: number;
  total_overtime_hours?: number;
  total_overtime_amount?: number;
  total_days: number;
  total_quantity: number;
  payment_date?: string | null;
  payment_method?: string | null;
  reference_number?: string | null;
  remarks?: string | null;
  created_by?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  paid_by?: string | null;
  paid_at?: string | null;
  cancelled_by?: string | null;
  cancelled_at?: string | null;
  cancellation_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmployeePaymentDetailResponse extends EmployeePaymentResponse {
  lines: EmployeePaymentLineResponse[];
  rate_band_summaries: RateBandSummaryResponse[];
}

export interface EmployeePaymentPreviewItem {
  employee_id: string;
  employee_name: string;
  period_start: string;
  period_end: string;
  rate_band_summaries: RateBandSummaryResponse[];
  total_days: number;
  total_quantity: number;
  total_regular_amount?: number;
  total_overtime_hours?: number;
  total_overtime_amount?: number;
  total_amount: number;
  eligible_attendance_count: number;
  eligible_work_entry_count: number;
}

export interface EmployeePaymentPreviewResponse {
  period_start: string;
  period_end: string;
  total_employees: number;
  grand_total_regular_amount?: number;
  grand_total_overtime_hours?: number;
  grand_total_overtime_amount?: number;
  grand_total_amount: number;
  items: EmployeePaymentPreviewItem[];
}

export interface GeneratePaymentRequest {
  period_start: string;
  period_end: string;
  idempotency_key: string;
  employee_id?: string | null;
}

export interface ListEmployeePaymentsParams {
  period_start?: string;
  period_end?: string;
  employee_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface PreviewEmployeePaymentsParams {
  period_start: string;
  period_end: string;
  employee_id?: string;
}

export const previewEmployeePaymentsApi = async (
  params: PreviewEmployeePaymentsParams
): Promise<EmployeePaymentPreviewResponse> => {
  const response = await apiClient.get<EmployeePaymentPreviewResponse>('/employee-payments/preview', { params });
  return response.data;
};

export const generateEmployeePaymentsApi = async (
  data: GeneratePaymentRequest
): Promise<EmployeePaymentResponse[]> => {
  const response = await apiClient.post<EmployeePaymentResponse[]>('/employee-payments/generate', data);
  return response.data;
};

export const listEmployeePaymentsApi = async (
  params?: ListEmployeePaymentsParams
): Promise<EmployeePaymentResponse[]> => {
  const response = await apiClient.get<EmployeePaymentResponse[]>('/employee-payments', { params });
  return response.data;
};

export const getEmployeePaymentApi = async (
  paymentId: string
): Promise<EmployeePaymentDetailResponse> => {
  const response = await apiClient.get<EmployeePaymentDetailResponse>(`/employee-payments/${paymentId}`);
  return response.data;
};

export interface PayPaymentRequest {
  payment_date?: string | null;
  payment_method: string;
  reference_number?: string | null;
  remarks?: string | null;
}

export interface CancelPaymentRequest {
  cancellation_reason: string;
}

export const approveEmployeePaymentApi = async (
  paymentId: string
): Promise<EmployeePaymentDetailResponse> => {
  const response = await apiClient.post<EmployeePaymentDetailResponse>(`/employee-payments/${paymentId}/approve`, {});
  return response.data;
};

export const payEmployeePaymentApi = async (
  paymentId: string,
  data: PayPaymentRequest
): Promise<EmployeePaymentDetailResponse> => {
  const response = await apiClient.post<EmployeePaymentDetailResponse>(`/employee-payments/${paymentId}/pay`, data);
  return response.data;
};

export const cancelEmployeePaymentApi = async (
  paymentId: string,
  data: CancelPaymentRequest
): Promise<EmployeePaymentDetailResponse> => {
  const response = await apiClient.post<EmployeePaymentDetailResponse>(`/employee-payments/${paymentId}/cancel`, data);
  return response.data;
};

