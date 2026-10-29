import { apiClient } from './client';

export interface RateOverrideItem {
  source_id: string;
  unit_rate: number;
  rate_override_reason: string;
}

export interface InvoiceLinePreviewItem {
  source_type: 'work' | 'material';
  source_id: string;
  source_date: string;
  item_description: string;
  quantity: number;
  uom: string;
  standard_rate: number;
  unit_rate: number;
  line_amount: number;
}

export interface InvoicePreviewResponse {
  client_id: string;
  client_name: string;
  project_id: string;
  project_name: string;
  site_id: string;
  site_name: string;
  period_start: string;
  period_end: string;
  billable_work_count: number;
  billable_material_count: number;
  subtotal_work: number;
  subtotal_material: number;
  estimated_tax: number;
  estimated_total: number;
  items: InvoiceLinePreviewItem[];
}

export interface GenerateInvoiceRequest {
  client_id: string;
  project_id: string;
  site_id: string;
  period_start: string;
  period_end: string;
  idempotency_key: string;
  client_po_number?: string | null;
  notes?: string | null;
  remarks?: string | null;
  tax_amount?: number;
  rate_overrides?: RateOverrideItem[] | null;
}

export interface UpdateDraftInvoiceRequest {
  client_po_number?: string | null;
  notes?: string | null;
  remarks?: string | null;
  tax_amount?: number | null;
  due_date?: string | null;
  rate_overrides?: RateOverrideItem[] | null;
}

export interface IssueInvoiceRequest {
  issue_date?: string | null;
  due_date?: string | null;
}

export interface CancelInvoiceRequest {
  cancellation_reason: string;
}

export interface InvoiceLineItem {
  id: string;
  invoice_id: string;
  line_type: 'work' | 'material';
  source_daily_work_entry_id?: string | null;
  source_material_transaction_id?: string | null;
  source_date: string;
  item_description: string;
  quantity: number;
  uom: string;
  standard_rate: number;
  unit_rate: number;
  line_amount: number;
  rate_override_reason?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface InvoiceResponse {
  id: string;
  invoice_number: string;
  idempotency_key: string;
  client_id: string;
  client_name?: string | null;
  project_id: string;
  project_name?: string | null;
  site_id: string;
  site_name?: string | null;
  period_start: string;
  period_end: string;
  status: 'draft' | 'issued' | 'partially_paid' | 'paid' | 'cancelled';
  subtotal_work: number;
  subtotal_material: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  issue_date?: string | null;
  due_date?: string | null;
  client_po_number?: string | null;
  notes?: string | null;
  remarks?: string | null;
  created_by?: string | null;
  issued_by?: string | null;
  issued_at?: string | null;
  cancelled_by?: string | null;
  cancelled_at?: string | null;
  cancellation_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvoiceDetailResponse extends InvoiceResponse {
  lines: InvoiceLineItem[];
}

export interface ListInvoicesParams {
  client_id?: string;
  project_id?: string;
  site_id?: string;
  status?: string;
  period_start?: string;
  period_end?: string;
  limit?: number;
  offset?: number;
}

export interface PreviewInvoiceParams {
  client_id: string;
  project_id: string;
  site_id: string;
  period_start: string;
  period_end: string;
}

export const previewInvoiceApi = async (params: PreviewInvoiceParams): Promise<InvoicePreviewResponse> => {
  const response = await apiClient.get<InvoicePreviewResponse>('/invoices/preview', { params });
  return response.data;
};

export const generateInvoiceApi = async (data: GenerateInvoiceRequest): Promise<InvoiceDetailResponse> => {
  const response = await apiClient.post<InvoiceDetailResponse>('/invoices/generate', data);
  return response.data;
};

export const listInvoicesApi = async (params?: ListInvoicesParams): Promise<InvoiceResponse[]> => {
  const response = await apiClient.get<InvoiceResponse[]>('/invoices', { params });
  return response.data;
};

export const getInvoiceApi = async (invoiceId: string): Promise<InvoiceDetailResponse> => {
  const response = await apiClient.get<InvoiceDetailResponse>(`/invoices/${invoiceId}`);
  return response.data;
};

export const updateDraftInvoiceApi = async (
  invoiceId: string,
  data: UpdateDraftInvoiceRequest,
): Promise<InvoiceDetailResponse> => {
  const response = await apiClient.patch<InvoiceDetailResponse>(`/invoices/${invoiceId}`, data);
  return response.data;
};

export const issueInvoiceApi = async (
  invoiceId: string,
  data?: IssueInvoiceRequest,
): Promise<InvoiceDetailResponse> => {
  const response = await apiClient.post<InvoiceDetailResponse>(`/invoices/${invoiceId}/issue`, data || {});
  return response.data;
};

export const cancelInvoiceApi = async (
  invoiceId: string,
  data: CancelInvoiceRequest,
): Promise<InvoiceDetailResponse> => {
  const response = await apiClient.post<InvoiceDetailResponse>(`/invoices/${invoiceId}/cancel`, data);
  return response.data;
};
