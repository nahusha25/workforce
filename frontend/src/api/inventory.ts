import { apiClient } from './client';

export interface SiteInventoryItem {
  material_id: string;
  material_code?: string | null;
  material_name: string;
  unit_of_measure: string;
  category: string;
  quantity_available: number;
  last_movement_at?: string | null;
  is_active: boolean;
}

export interface SiteInventoryListResponse {
  items: SiteInventoryItem[];
  total: number;
  skip: number;
  limit: number;
  site_id: string;
  site_name: string;
}

export interface StockInwardPayload {
  site_id: string;
  material_id: string;
  quantity: number;
  idempotency_key: string;
  remarks?: string;
}

export interface StockInwardResponse {
  movement_id: string;
  site_id: string;
  material_id: string;
  material_name: string;
  material_code?: string | null;
  unit_of_measure: string;
  movement_type: string;
  quantity: number;
  balance_after: number;
  idempotency_key: string;
  remarks?: string | null;
  created_by: string;
  created_at: string;
}

export interface StockMovementItem {
  movement_id: string;
  site_id: string;
  material_id: string;
  movement_type: 'inward' | 'consumed' | 'returned' | 'adjustment' | string;
  quantity: number;
  balance_after: number;
  material_transaction_id?: string | null;
  idempotency_key: string;
  remarks?: string | null;
  created_by: string;
  actor_name?: string | null;
  created_at: string;
}

export interface StockMovementHistoryResponse {
  items: StockMovementItem[];
  total: number;
  skip: number;
  limit: number;
  site_id: string;
  material_id: string;
  material_name: string;
  material_code?: string | null;
  unit_of_measure: string;
}

export interface MaterialStockResponse {
  site_id: string;
  site_name: string;
  material_id: string;
  material_code?: string | null;
  material_name: string;
  unit_of_measure: string;
  category: string;
  quantity_available: number;
  last_movement_at?: string | null;
  is_active: boolean;
}

/**
 * Retrieves catalogue materials and available stock balances for a site.
 * Authorized for Directors, Administrators, and Supervisors (assigned to site).
 */
export const getSiteInventoryApi = async (
  siteId: string,
  params?: {
    skip?: number;
    limit?: number;
    search?: string;
    category?: string;
    is_active?: boolean;
  }
): Promise<SiteInventoryListResponse> => {
  const response = await apiClient.get<SiteInventoryListResponse>(
    `/inventory/sites/${siteId}`,
    { params }
  );
  return response.data;
};

/**
 * Records stock received at a site via the approved inward inventory API.
 * Authorized for Directors, Administrators, and Supervisors (assigned to site).
 */
export const recordStockInwardApi = async (
  payload: StockInwardPayload
): Promise<StockInwardResponse> => {
  const response = await apiClient.post<StockInwardResponse>(
    '/inventory/inward',
    payload
  );
  return response.data;
};

/**
 * Retrieves the stock movement ledger history for a specific material and site.
 * Authorized for Directors, Administrators, and Supervisors (assigned to site).
 */
export const getMaterialStockMovementsApi = async (
  siteId: string,
  materialId: string,
  params?: { skip?: number; limit?: number }
): Promise<StockMovementHistoryResponse> => {
  const response = await apiClient.get<StockMovementHistoryResponse>(
    `/inventory/sites/${siteId}/materials/${materialId}/movements`,
    { params }
  );
  return response.data;
};

/**
 * Narrowly scoped read-only availability check for Daily Work consumption.
 * Authorized for employees actively assigned to site, supervising supervisors, and admins.
 */
export const getMaterialStockAvailabilityApi = async (
  siteId: string,
  materialId: string
): Promise<MaterialStockResponse> => {
  const response = await apiClient.get<MaterialStockResponse>(
    `/daily-work/sites/${siteId}/materials/${materialId}/availability`
  );
  return response.data;
};

export interface InventorySiteItem {
  id: string;
  name: string;
  project_id: string;
  address?: string | null;
  location?: string | null;
  permitted_radius_m?: number | null;
  supervisor_id?: string | null;
  is_active: boolean;
}

/**
 * Retrieves sites authorized for inventory tracking based on current user role:
 * - Administrators and Directors: all active sites.
 * - Supervisors: only assigned/supervised active sites.
 * - Employees: 403 Forbidden.
 */
export const getInventorySitesApi = async (): Promise<InventorySiteItem[]> => {
  const response = await apiClient.get<InventorySiteItem[]>('/inventory/sites');
  return response.data;
};

