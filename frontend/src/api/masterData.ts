import { apiClient } from './client';

// Client Types
export interface ClientCreateData {
  name: string;
  contact_person?: string | null;
  contact_mobile?: string | null;
  is_active?: boolean;
}

export interface ClientResponseData {
  id: string;
  name: string;
  contact_person?: string | null;
  contact_mobile?: string | null;
  is_active: boolean;
  created_at: string;
}

// Project Types
export interface ProjectCreateData {
  name: string;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  client_id: string;
}

export interface ProjectResponseData {
  id: string;
  name: string;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  client_id: string;
}

// Site Types
export interface SiteCreateData {
  name: string;
  address?: string | null;
  location?: string | null;
  permitted_radius_m?: number | null;
  supervisor_id?: string | null;
  is_active?: boolean;
  project_id: string;
}

export interface SiteResponseData {
  id: string;
  name: string;
  address?: string | null;
  location?: string | null;
  permitted_radius_m?: number | null;
  supervisor_id?: string | null;
  is_active: boolean;
  project_id: string;
}

// Role Types
export interface RoleResponseData {
  id: string;
  name: string;
  description?: string | null;
}

// API Methods
export async function getClientsApi(): Promise<ClientResponseData[]> {
  const res = await apiClient.get<ClientResponseData[]>('/admin/clients');
  return res.data;
}

export async function createClientApi(data: ClientCreateData): Promise<ClientResponseData> {
  const res = await apiClient.post<ClientResponseData>('/admin/clients', data);
  return res.data;
}

export async function getProjectsApi(): Promise<ProjectResponseData[]> {
  const res = await apiClient.get<ProjectResponseData[]>('/admin/projects');
  return res.data;
}

export async function createProjectApi(data: ProjectCreateData): Promise<ProjectResponseData> {
  const res = await apiClient.post<ProjectResponseData>('/admin/projects', data);
  return res.data;
}

export async function getSitesApi(): Promise<SiteResponseData[]> {
  const res = await apiClient.get<SiteResponseData[]>('/admin/sites');
  return res.data;
}

export async function createSiteApi(data: SiteCreateData): Promise<SiteResponseData> {
  const res = await apiClient.post<SiteResponseData>('/admin/sites', data);
  return res.data;
}

export async function getRolesApi(): Promise<RoleResponseData[]> {
  const res = await apiClient.get<RoleResponseData[]>('/admin/roles');
  return res.data;
}

// Work Order Types
export interface WorkOrderCreateData {
  order_number: string;
  project_id: string;
  site_id: string;
  description?: string | null;
  target_quantities?: Record<string, any> | null;
  start_date?: string | null;
  end_date?: string | null;
  billing_basis?: 'per_metre' | 'per_device' | 'lump_sum' | string | null;
  status?: 'draft' | 'open' | 'in_progress' | 'completed' | 'closed' | string;
  is_active?: boolean;
}

export interface WorkOrderUpdateData {
  order_number?: string;
  project_id?: string;
  site_id?: string;
  description?: string | null;
  target_quantities?: Record<string, any> | null;
  start_date?: string | null;
  end_date?: string | null;
  billing_basis?: 'per_metre' | 'per_device' | 'lump_sum' | string | null;
  status?: 'draft' | 'open' | 'in_progress' | 'completed' | 'closed' | string;
  is_active?: boolean;
}

export interface WorkOrderResponseData {
  id: string;
  order_number: string;
  project_id: string;
  site_id: string;
  description?: string | null;
  target_quantities?: Record<string, any> | null;
  start_date?: string | null;
  end_date?: string | null;
  billing_basis?: string | null;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export async function getWorkOrdersApi(): Promise<WorkOrderResponseData[]> {
  const res = await apiClient.get<WorkOrderResponseData[]>('/admin/work-orders');
  return res.data;
}

export async function getWorkOrderByIdApi(id: string): Promise<WorkOrderResponseData> {
  const res = await apiClient.get<WorkOrderResponseData>(`/admin/work-orders/${id}`);
  return res.data;
}

export async function createWorkOrderApi(data: WorkOrderCreateData): Promise<WorkOrderResponseData> {
  const res = await apiClient.post<WorkOrderResponseData>('/admin/work-orders', data);
  return res.data;
}

export async function updateWorkOrderApi(id: string, data: WorkOrderUpdateData): Promise<WorkOrderResponseData> {
  const res = await apiClient.put<WorkOrderResponseData>(`/admin/work-orders/${id}`, data);
  return res.data;
}

// Activity Types
export interface ActivityCreateData {
  name: string;
  unit_of_measure: string;
  approved_rate: number;
  category: 'cable' | 'device' | 'drilling' | 'mounting' | 'testing' | 'commissioning' | string;
  is_active?: boolean;
}

export interface ActivityUpdateData {
  name?: string;
  unit_of_measure?: string;
  approved_rate?: number;
  category?: 'cable' | 'device' | 'drilling' | 'mounting' | 'testing' | 'commissioning' | string;
  is_active?: boolean;
}

export interface ActivityResponseData {
  id: string;
  name: string;
  unit_of_measure: string;
  approved_rate: number;
  category: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export async function getActivitiesApi(): Promise<ActivityResponseData[]> {
  const res = await apiClient.get<ActivityResponseData[]>('/admin/activities');
  return res.data;
}

export async function getActivityByIdApi(id: string): Promise<ActivityResponseData> {
  const res = await apiClient.get<ActivityResponseData>(`/admin/activities/${id}`);
  return res.data;
}

export async function createActivityApi(data: ActivityCreateData): Promise<ActivityResponseData> {
  const res = await apiClient.post<ActivityResponseData>('/admin/activities', data);
  return res.data;
}

export async function updateActivityApi(id: string, data: ActivityUpdateData): Promise<ActivityResponseData> {
  const res = await apiClient.put<ActivityResponseData>(`/admin/activities/${id}`, data);
  return res.data;
}

// Material Types
export interface MaterialCreateData {
  name: string;
  material_code?: string | null;
  description?: string | null;
  unit_of_measure: string;
  category: 'cable' | 'device' | 'tool' | 'consumable' | string;
  purchase_approval_limit: number;
  is_active?: boolean;
}

export interface MaterialUpdateData {
  name?: string;
  material_code?: string | null;
  description?: string | null;
  unit_of_measure?: string;
  category?: 'cable' | 'device' | 'tool' | 'consumable' | string;
  purchase_approval_limit?: number;
  is_active?: boolean;
}

export interface MaterialResponseData {
  id: string;
  name: string;
  material_code?: string | null;
  description?: string | null;
  unit_of_measure: string;
  category: string;
  purchase_approval_limit: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export async function getMaterialsApi(): Promise<MaterialResponseData[]> {
  const res = await apiClient.get<MaterialResponseData[]>('/admin/materials');
  return res.data;
}

export async function getMaterialByIdApi(id: string): Promise<MaterialResponseData> {
  const res = await apiClient.get<MaterialResponseData>(`/admin/materials/${id}`);
  return res.data;
}

export async function createMaterialApi(data: MaterialCreateData): Promise<MaterialResponseData> {
  const res = await apiClient.post<MaterialResponseData>('/admin/materials', data);
  return res.data;
}

export async function updateMaterialApi(id: string, data: MaterialUpdateData): Promise<MaterialResponseData> {
  const res = await apiClient.put<MaterialResponseData>(`/admin/materials/${id}`, data);
  return res.data;
}

