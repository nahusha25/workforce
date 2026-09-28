import { apiClient } from './client';

export interface Activity {
  id: string;
  name: string;
  category: string;
  unit_of_measure: string;
  approved_rate: number;
  is_active: boolean;
}

export interface WorkOrder {
  id: string;
  order_number: string;
  project_id: string;
  site_id: string;
  description?: string | null;
  status: string;
  is_active: boolean;
}

export interface WorkPhoto {
  id: string;
  daily_work_entry_id: string;
  image_url: string;
  thumbnail_url?: string | null;
  file_size_bytes?: number | null;
  uploaded_at: string;
}

export interface DailyWorkEntry {
  id: string;
  idempotency_key: string;
  attendance_record_id: string;
  employee_id: string;
  employee_name?: string | null;
  site_id: string;
  site_name?: string | null;
  activity_id: string;
  activity_name?: string | null;
  work_order_id?: string | null;
  work_date: string;
  date?: string;
  quantity: number;
  uom: string;
  status: string;
  remarks?: string | null;
  photos?: WorkPhoto[];
  materials?: MaterialTransaction[];
  created_at?: string;
  updated_at?: string;
}

export interface MaterialTransaction {
  id: string;
  daily_work_entry_id: string;
  material_id?: string | null;
  site_id?: string;
  transaction_type: 'consumed' | 'purchased' | string;
  item_name: string;
  quantity: number | string;
  amount: number | string;
  bill_image_url?: string | null;
  is_high_value: boolean;
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface MaterialTransactionPayload {
  transaction_type: 'consumed' | 'purchased';
  item_name: string;
  quantity: number | string;
  amount?: number | string;
  material_id?: string | null;
  bill_file?: File | null;
}

export interface DailyWorkEntryPayload {
  idempotency_key: string;
  activity_id: string;
  work_order_id?: string | null;
  quantity: number;
  work_date?: string;
  remarks?: string | null;
}

export interface DailyWorkEntryUpdatePayload {
  activity_id?: string;
  work_order_id?: string | null;
  quantity?: number;
  remarks?: string | null;
}

export interface DailyWorkListResponse {
  data: DailyWorkEntry[];
  total: number;
  skip: number;
  limit: number;
  page?: number;
  page_size?: number;
}

/**
 * Fetch available activities for work entry
 */
export const getActivities = async (): Promise<Activity[]> => {
  const response = await apiClient.get<Activity[]>('/daily-work/activities');
  return response.data;
};

/**
 * Fetch work orders for optional assignment
 */
export const getWorkOrders = async (): Promise<WorkOrder[]> => {
  const response = await apiClient.get<WorkOrder[]>('/daily-work/work-orders');
  return response.data;
};

/**
 * Fetch daily work entries (e.g. for today)
 */
export const getDailyWorkEntries = async (date?: string): Promise<DailyWorkEntry[]> => {
  const url = date ? `/daily-work?date=${date}` : '/daily-work';
  const response = await apiClient.get<DailyWorkListResponse>(url);
  return response.data.data;
};

/**
 * Get single daily work entry
 */
export const getDailyWorkEntry = async (id: string): Promise<DailyWorkEntry> => {
  const response = await apiClient.get<DailyWorkEntry>(`/daily-work/${id}`);
  return response.data;
};

/**
 * Create a new daily work draft
 */
export const createDailyWorkEntry = async (
  payload: DailyWorkEntryPayload
): Promise<DailyWorkEntry> => {
  const response = await apiClient.post<DailyWorkEntry>('/daily-work', payload);
  return response.data;
};

/**
 * Update existing daily work entry
 */
export const updateDailyWorkEntry = async (
  id: string,
  payload: DailyWorkEntryUpdatePayload | Partial<DailyWorkEntryPayload>
): Promise<DailyWorkEntry> => {
  const response = await apiClient.put<DailyWorkEntry>(`/daily-work/${id}`, payload);
  return response.data;
};

/**
 * Submit daily work entry for verification
 */
export const submitDailyWorkEntry = async (
  id: string
): Promise<{ id: string; status: string; submitted_at: string }> => {
  const response = await apiClient.post<{ id: string; status: string; submitted_at: string }>(
    `/daily-work/${id}/submit`
  );
  return response.data;
};

/**
 * Fetch photos for a daily work entry
 */
export const getWorkPhotos = async (dailyWorkEntryId: string): Promise<WorkPhoto[]> => {
  const response = await apiClient.get<WorkPhoto[]>(`/daily-work/${dailyWorkEntryId}/photos`);
  return response.data;
};

/**
 * Upload a progress photo for a daily work entry with upload progress callback
 */
export const uploadWorkPhoto = async (
  dailyWorkEntryId: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<WorkPhoto> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<WorkPhoto>(
    `/daily-work/${dailyWorkEntryId}/photos`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    }
  );
  return response.data;
};

/**
 * Delete a work photo
 */
export const deleteWorkPhoto = async (
  photoId: string
): Promise<{ status: string; message: string }> => {
  const response = await apiClient.delete<{ status: string; message: string }>(
    `/daily-work/photos/${photoId}`
  );
  return response.data;
};

/**
 * Fetch material transactions for a daily work entry
 */
export const getMaterialTransactions = async (
  dailyWorkEntryId: string
): Promise<MaterialTransaction[]> => {
  const response = await apiClient.get<MaterialTransaction[]>(
    `/daily-work/${dailyWorkEntryId}/materials`
  );
  return response.data;
};

/**
 * Create a material transaction (supports combined multipart with optional bill upload)
 */
export const createMaterialTransaction = async (
  dailyWorkEntryId: string,
  payload: MaterialTransactionPayload
): Promise<MaterialTransaction> => {
  if (payload.bill_file) {
    const formData = new FormData();
    formData.append('transaction_type', payload.transaction_type);
    formData.append('item_name', payload.item_name);
    formData.append('quantity', String(payload.quantity));
    formData.append('amount', String(payload.amount ?? 0));
    if (payload.material_id) {
      formData.append('material_id', payload.material_id);
    }
    formData.append('bill_file', payload.bill_file);

    const response = await apiClient.post<MaterialTransaction>(
      `/daily-work/${dailyWorkEntryId}/materials`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  const response = await apiClient.post<MaterialTransaction>(
    `/daily-work/${dailyWorkEntryId}/materials`,
    {
      transaction_type: payload.transaction_type,
      item_name: payload.item_name,
      quantity: Number(payload.quantity),
      amount: Number(payload.amount ?? 0),
      material_id: payload.material_id || null,
    }
  );
  return response.data;
};

/**
 * Delete a material transaction
 */
export const deleteMaterialTransaction = async (
  transactionId: string
): Promise<{ status: string; message: string }> => {
  const response = await apiClient.delete<{ status: string; message: string }>(
    `/daily-work/materials/${transactionId}`
  );
  return response.data;
};
