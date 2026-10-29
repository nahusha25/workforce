import { apiClient } from './client';
import type { SiteResponseData } from './masterData';

export type AssetConditionType = 'new' | 'good' | 'fair' | 'damaged' | 'unusable';
export type AssetStatusType =
  | 'available'
  | 'under_maintenance'
  | 'damaged'
  | 'lost'
  | 'retired'
  | 'issued_employee';
export type LocationType = 'warehouse' | 'site';

export interface AssetResponse {
  id: string;
  asset_tag: string;
  name: string;
  category: string;
  serial_number?: string | null;
  manufacturer?: string | null;
  model_number?: string | null;
  purchase_date?: string | null;
  purchase_cost?: number | string | null;
  warranty_expiry_date?: string | null;
  condition: AssetConditionType;
  status: AssetStatusType;
  location_type: LocationType;
  current_site_id?: string | null;
  current_site_name?: string | null;
  current_custodian_id?: string | null;
  current_custodian_name?: string | null;
  description?: string | null;
  is_active: boolean;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssetTransactionResponse {
  id: string;
  asset_id: string;
  transaction_type: string;
  from_location_type?: string | null;
  to_location_type?: string | null;
  from_site_id?: string | null;
  to_site_id?: string | null;
  from_site_name?: string | null;
  to_site_name?: string | null;
  from_employee_id?: string | null;
  to_employee_id?: string | null;
  from_employee_name?: string | null;
  to_employee_name?: string | null;
  condition_before?: string | null;
  condition_after?: string | null;
  transaction_date: string;
  performed_by?: string | null;
  remarks?: string | null;
  idempotency_key?: string | null;
  created_at: string;
}

export interface AssetDetailResponse extends AssetResponse {
  transactions: AssetTransactionResponse[];
}

export interface AssetListResponse {
  items: AssetResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface ListAssetsParams {
  skip?: number;
  limit?: number;
  search?: string;
  location_type?: LocationType | '';
  site_id?: string;
  category?: string;
  status?: string;
  condition?: string;
  is_active?: boolean;
}

export interface AssetRegisterRequest {
  asset_tag?: string | null;
  name: string;
  category: string;
  serial_number?: string | null;
  manufacturer?: string | null;
  model_number?: string | null;
  purchase_date?: string | null;
  purchase_cost?: number | string | null;
  warranty_expiry_date?: string | null;
  condition?: AssetConditionType;
  status?: Exclude<AssetStatusType, 'issued_employee'>;
  location_type: LocationType;
  current_site_id?: string | null;
  site_id?: string | null;
  description?: string | null;
  remarks?: string | null;
  idempotency_key?: string | null;
}

export interface AssetIssueRequest {
  employee_id: string;
  remarks?: string | null;
  idempotency_key?: string | null;
}

export interface AssetReturnRequest {
  employee_id: string;
  condition?: AssetConditionType | null;
  status?: Exclude<AssetStatusType, 'issued_employee'> | null;
  remarks?: string | null;
  idempotency_key?: string | null;
}

export interface AssetReassignRequest {
  target_location_type: LocationType;
  target_site_id?: string | null;
  site_id?: string | null;
  remarks?: string | null;
  idempotency_key?: string | null;
}

export const listAssetsApi = async (params?: ListAssetsParams): Promise<AssetListResponse> => {
  const cleanedParams: Record<string, any> = {};
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        cleanedParams[k] = v;
      }
    });
  }
  const response = await apiClient.get<AssetListResponse>('/assets', { params: cleanedParams });
  return response.data;
};

export const getAssetApi = async (assetId: string): Promise<AssetDetailResponse> => {
  const response = await apiClient.get<AssetDetailResponse>(`/assets/${assetId}`);
  return response.data;
};

export const registerAssetApi = async (data: AssetRegisterRequest): Promise<AssetResponse> => {
  const response = await apiClient.post<AssetResponse>('/assets', data);
  return response.data;
};

export const issueAssetApi = async (
  assetId: string,
  data: AssetIssueRequest,
): Promise<AssetResponse> => {
  const response = await apiClient.post<AssetResponse>(`/assets/${assetId}/issue`, data);
  return response.data;
};

export const returnAssetApi = async (
  assetId: string,
  data: AssetReturnRequest,
): Promise<AssetResponse> => {
  const response = await apiClient.post<AssetResponse>(`/assets/${assetId}/return`, data);
  return response.data;
};

export const reassignAssetApi = async (
  assetId: string,
  data: AssetReassignRequest,
): Promise<AssetResponse> => {
  const response = await apiClient.post<AssetResponse>(`/assets/${assetId}/reassign`, data);
  return response.data;
};

export const getAssetDestinationSitesApi = async (
  assetId: string,
): Promise<SiteResponseData[]> => {
  const response = await apiClient.get<SiteResponseData[]>(`/assets/${assetId}/destination-sites`);
  return response.data;
};

export const getAssetSitesApi = async (): Promise<SiteResponseData[]> => {
  const response = await apiClient.get<SiteResponseData[]>('/assets/sites');
  return response.data;
};

