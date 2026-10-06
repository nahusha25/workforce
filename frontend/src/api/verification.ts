import { apiClient } from './client';

export type EntityType = 'attendance' | 'daily_work' | 'material' | 'material_transaction';
export type VerificationAction = 'approved' | 'rejected' | 'correction_required';

/**
 * Substring marker raised by backend InvalidVerificationStateError when target record
 * is not in a valid state for the requested verification action (e.g. already approved/rejected).
 */
export const STATE_CONFLICT_MARKER = 'Target must be submitted.';

export interface VerificationHistoryEvent {
  id: string;
  action: string;
  remarks: string | null;
  verified_by: string;
  verified_by_name: string;
  verified_at: string;
}

export interface VerificationSummaryItem {
  employee_id: string;
  employee_name: string;
  employee_code: string;
  site_id: string | null;
  site_name: string | null;
  attendance_record_id: string | null;
  attendance_status: string | null;
  check_in_time: string | null;
  check_out_time: string | null;
  working_hours: number | null;
  work_entry_count: number;
  photo_count: number;
  material_count: number;
  total_material_cost: string | number;
  exception_flags: string[];
  has_pending_verification: boolean;
}

export interface VerificationSummaryResponse {
  date: string;
  site_id: string | null;
  items: VerificationSummaryItem[];
  total_employees: number;
  pending_verification_count: number;
}

export interface EmployeeDayAttendanceDetail {
  id: string;
  date: string;
  session_number: number | null;
  check_in_time: string | null;
  check_in_distance_m: number | null;
  check_out_time: string | null;
  check_out_distance_m: number | null;
  is_within_geofence: boolean | null;
  working_hours: number | null;
  overtime_hours: number | null;
  status: string;
  override_by: string | null;
  verification_record_id: string | null;
  verification_action: string | null;
  verification_remarks: string | null;
  history: VerificationHistoryEvent[];
}

export interface EmployeeDayPhotoDetail {
  id: string;
  daily_work_entry_id: string;
  image_url: string;
  thumbnail_url: string | null;
  file_size_bytes: number | null;
  uploaded_at: string;
}

export interface EmployeeDayMaterialDetail {
  id: string;
  daily_work_entry_id: string;
  material_id: string | null;
  site_id: string;
  transaction_type: string;
  item_name: string;
  quantity: string | number;
  amount: string | number;
  bill_image_url: string | null;
  is_high_value: boolean;
  status: string;
  verification_record_id: string | null;
  verification_action: string | null;
  verification_remarks: string | null;
  history: VerificationHistoryEvent[];
}

export interface EmployeeDayWorkEntryDetail {
  id: string;
  idempotency_key: string;
  activity_id: string;
  activity_name: string;
  activity_category: string | null;
  work_order_id: string | null;
  work_order_number: string | null;
  work_date: string;
  quantity: string | number;
  uom: string;
  status: string;
  remarks: string | null;
  verification_record_id: string | null;
  verification_action: string | null;
  verification_remarks: string | null;
  history: VerificationHistoryEvent[];
  photos: EmployeeDayPhotoDetail[];
  materials: EmployeeDayMaterialDetail[];
}

export interface EmployeeDayDetailResponse {
  employee_id: string;
  employee_name: string;
  employee_code: string;
  date: string;
  site_id: string | null;
  site_name: string | null;
  attendance: EmployeeDayAttendanceDetail | null;
  work_entries: EmployeeDayWorkEntryDetail[];
  exception_flags: string[];
  all_verified: boolean;
}

export interface VerificationActionRequest {
  entity_type: EntityType;
  idempotency_key: string;
  remarks?: string | null;
}

export interface VerificationActionResponse {
  id: string;
  verification_record_id: string | null;
  idempotency_key: string;
  target_id: string;
  entity_type: string;
  action: string;
  status: string | null;
  target_status: string;
  remarks: string | null;
  verified_by: string;
  verified_at: string;
  is_replay: boolean;
}

/**
 * Generate a fresh UUID v4 for action idempotency.
 */
export function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/**
 * VER-001: Get verification summary for the team on a given date with optional site filter.
 */
export async function getVerificationSummary(
  date: string,
  siteId?: string | null
): Promise<VerificationSummaryResponse> {
  const params: Record<string, string> = { date };
  if (siteId) {
    params.site_id = siteId;
  }
  const res = await apiClient.get<VerificationSummaryResponse>('/verification/summary', { params });
  return res.data;
}

/**
 * VER-002: Get employee consolidated day detail for verification review.
 */
export async function getEmployeeDayDetail(
  employeeId: string,
  date: string
): Promise<EmployeeDayDetailResponse> {
  const res = await apiClient.get<EmployeeDayDetailResponse>(`/verification/summary/${employeeId}`, {
    params: { date },
  });
  return res.data;
}

export interface ActionOptions {
  entity_type: EntityType;
  remarks?: string | null;
  /** Pass an existing idempotency_key when retrying the same user action */
  idempotency_key?: string;
}

/**
 * VER-003: Approve an entity (attendance, work entry, material).
 * Generates a fresh idempotency_key if not provided, or reuses the passed key on retry.
 */
export async function approveEntity(
  targetId: string,
  options: ActionOptions
): Promise<VerificationActionResponse> {
  const idempotency_key = options.idempotency_key || generateIdempotencyKey();
  const payload: VerificationActionRequest = {
    entity_type: options.entity_type,
    idempotency_key,
    remarks: options.remarks ?? null,
  };
  const res = await apiClient.post<VerificationActionResponse>(`/verification/${targetId}/approve`, payload);
  return res.data;
}

/**
 * VER-004: Reject an entity with mandatory remarks.
 */
export async function rejectEntity(
  targetId: string,
  options: ActionOptions & { remarks: string }
): Promise<VerificationActionResponse> {
  const idempotency_key = options.idempotency_key || generateIdempotencyKey();
  const payload: VerificationActionRequest = {
    entity_type: options.entity_type,
    idempotency_key,
    remarks: options.remarks,
  };
  const res = await apiClient.post<VerificationActionResponse>(`/verification/${targetId}/reject`, payload);
  return res.data;
}

/**
 * VER-005: Return an entity for correction with mandatory remarks.
 */
export async function returnEntity(
  targetId: string,
  options: ActionOptions & { remarks: string }
): Promise<VerificationActionResponse> {
  const idempotency_key = options.idempotency_key || generateIdempotencyKey();
  const payload: VerificationActionRequest = {
    entity_type: options.entity_type,
    idempotency_key,
    remarks: options.remarks,
  };
  const res = await apiClient.post<VerificationActionResponse>(`/verification/${targetId}/return`, payload);
  return res.data;
}
