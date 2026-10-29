import { apiClient } from './client';

export type PaymentMethod = 'neft' | 'rtgs' | 'imps' | 'upi' | 'cheque' | 'cash' | 'other';
export type PaymentStatus = 'recorded' | 'voided';

export interface RecordPaymentRequest {
  idempotency_key: string;
  invoice_id: string;
  amount: number;
  payment_date: string;
  payment_method: PaymentMethod;
  reference_number?: string | null;
  notes?: string | null;
  receipt_url?: string | null;
}

export interface VoidPaymentRequest {
  void_idempotency_key: string;
  void_reason: string;
}

export interface ClientPaymentResponse {
  id: string;
  payment_number: string;
  idempotency_key: string;
  invoice_id: string;
  amount: number;
  payment_date: string;
  payment_method: PaymentMethod | string;
  reference_number?: string | null;
  notes?: string | null;
  receipt_url?: string | null;
  status: PaymentStatus | string;
  recorded_by?: string | null;
  recorded_by_name?: string | null;
  voided_by?: string | null;
  voided_by_name?: string | null;
  voided_at?: string | null;
  void_reason?: string | null;
  void_idempotency_key?: string | null;
  created_at: string;
  updated_at: string;
}

export const recordPaymentApi = async (data: RecordPaymentRequest): Promise<ClientPaymentResponse> => {
  const response = await apiClient.post<ClientPaymentResponse>('/client-payments', data);
  return response.data;
};

export const listPaymentsForInvoiceApi = async (invoiceId: string): Promise<ClientPaymentResponse[]> => {
  const response = await apiClient.get<ClientPaymentResponse[]>(`/client-payments/invoice/${invoiceId}`);
  return response.data;
};

export const getPaymentDetailApi = async (paymentId: string): Promise<ClientPaymentResponse> => {
  const response = await apiClient.get<ClientPaymentResponse>(`/client-payments/${paymentId}`);
  return response.data;
};

export const voidPaymentApi = async (
  paymentId: string,
  data: VoidPaymentRequest
): Promise<ClientPaymentResponse> => {
  const response = await apiClient.post<ClientPaymentResponse>(`/client-payments/${paymentId}/void`, data);
  return response.data;
};

export const uploadPaymentReceiptApi = async (
  paymentId: string,
  file: File
): Promise<ClientPaymentResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<ClientPaymentResponse>(
    `/client-payments/${paymentId}/receipt`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

export const downloadPaymentReceiptBlob = async (
  paymentId: string
): Promise<{ blob: Blob; filename: string }> => {
  const response = await apiClient.get(`/client-payments/${paymentId}/receipt`, {
    responseType: 'blob',
  });
  let filename = 'receipt';
  const disposition = response.headers?.['content-disposition'];
  if (disposition) {
    const filenameMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1].replace(/['"]/g, '');
    }
  }
  return { blob: response.data, filename };
};

export const viewPaymentReceipt = async (paymentId: string): Promise<void> => {
  const { blob, filename } = await downloadPaymentReceiptBlob(paymentId);
  const url = window.URL.createObjectURL(blob);
  const isPdfOrImage = blob.type.includes('pdf') || blob.type.includes('image');
  if (isPdfOrImage) {
    const popup = window.open(url, '_blank');
    if (!popup) {
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  } else {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
  setTimeout(() => window.URL.revokeObjectURL(url), 60000);
};

