import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { apiClient } from './client';

// ---------------------------------------------------------------------------
// Shared filter / pagination types
// ---------------------------------------------------------------------------

export interface DashboardFilters {
  date_from: string; // YYYY-MM-DD
  date_to: string; // YYYY-MM-DD
  client_id?: string | null;
  site_id?: string | null;
  employee_id?: string | null;
  supervisor_id?: string | null;
}

export interface ReportQueryParams extends DashboardFilters {
  page?: number;
  page_size?: number;
  // Report-specific optional parameters:
  status?: string | null;
  activity_id?: string | null;
  work_order_id?: string | null;
  transaction_type?: string | null;
  is_high_value?: boolean | null;
  sort_category?: string | null;
}

// ---------------------------------------------------------------------------
// Dashboard metrics types (DSH-001)
// ---------------------------------------------------------------------------

export interface ManpowerMetric {
  total_distinct_employees: number;
}

export interface WorkingHoursMetric {
  total_hours: number | string;
  average_per_employee: number | string | null;
}

export interface SiteProgressEntry {
  site_id: string;
  site_name: string;
  total_quantity: number | string;
  category_breakdown: Record<string, number | string>;
}

export interface CableMetresMetric {
  total: number | string;
}

export interface DevicesInstalledMetric {
  total: number | string;
}

export interface ProductivityByCategoryEntry {
  category: string;
  uom: string;
  total_quantity: number | string;
  ratio: number | string | null;
  ratio_label: string;
}

export interface EmployeeProductivity {
  employee_id: string;
  employee_name: string;
  total_approved_hours: number | string;
  by_category: ProductivityByCategoryEntry[];
}

export interface MaterialCostMetric {
  total_amount: number | string;
  currency: string;
}

export interface ApprovalStatusCounts {
  approved: number;
  submitted: number;
  draft: number;
  rejected: number;
  correction_required: number;
}

export interface ApprovalStatusMetric {
  attendance: ApprovalStatusCounts;
  work_entries: ApprovalStatusCounts;
  materials: ApprovalStatusCounts;
}

export interface DashboardMetricsResponse {
  period: {
    from: string;
    to: string;
  };
  manpower: ManpowerMetric;
  working_hours: WorkingHoursMetric;
  site_progress: SiteProgressEntry[];
  cable_metres: CableMetresMetric;
  devices_installed: DevicesInstalledMetric;
  employee_productivity: EmployeeProductivity[];
  material_cost: MaterialCostMetric;
  approval_status: ApprovalStatusMetric;
}

// ---------------------------------------------------------------------------
// Report row types (DSH-002 through DSH-007)
// ---------------------------------------------------------------------------

export interface AttendanceReportRow {
  attendance_id: string;
  employee_id: string;
  employee_name: string;
  site_id: string;
  site_name: string;
  date: string;
  check_in_time: string | null;
  check_out_time: string | null;
  working_hours: number | string | null;
  overtime_hours: number | string | null;
  status: string;
  is_within_geofence: boolean | null;
}

export interface WorkReportRow {
  entry_id: string;
  employee_id: string;
  employee_name: string;
  site_id: string;
  site_name: string;
  work_date: string;
  activity_name: string;
  category: string;
  quantity: number | string;
  uom: string;
  status: string;
  work_order_id: string | null;
}

export interface MaterialsReportRow {
  transaction_id: string;
  employee_id: string;
  employee_name: string;
  site_id: string;
  site_name: string;
  item_name: string;
  transaction_type: string;
  quantity: number | string;
  amount: number | string;
  is_high_value: boolean;
  status: string;
  created_at: string;
}

export interface ProductivityReportRow {
  employee_id: string;
  employee_name: string;
  total_approved_hours: number | string;
  by_category: ProductivityByCategoryEntry[];
}

export interface PaymentSummaryRow {
  employee_id: string;
  employee_name: string;
  rate_type: string;
  rate_effective_from: string;
  rate_effective_to: string | null;
  approved_days: number;
  approved_quantity: number | string;
  effective_rate: number | string;
  estimated_gross: number | string;
}

export interface InvoiceSummaryRow {
  site_id: string;
  site_name: string;
  client_id: string;
  client_name: string;
  total_labour_days: number;
  total_work_quantity: number | string;
  total_material_cost: number | string;
}

// ---------------------------------------------------------------------------
// Paginated wrappers
// ---------------------------------------------------------------------------

export interface PaginatedReportResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
}

export type AttendanceReportResponse = PaginatedReportResponse<AttendanceReportRow>;
export type WorkReportResponse = PaginatedReportResponse<WorkReportRow>;
export type MaterialsReportResponse = PaginatedReportResponse<MaterialsReportRow>;
export type ProductivityReportResponse = PaginatedReportResponse<ProductivityReportRow>;
export interface PaymentSummaryResponse extends PaginatedReportResponse<PaymentSummaryRow> {
  note?: string;
}
export type InvoiceSummaryResponse = PaginatedReportResponse<InvoiceSummaryRow>;

export type ReportType =
  | 'attendance'
  | 'work'
  | 'materials'
  | 'productivity'
  | 'payment-summary'
  | 'invoice-summary';

// ---------------------------------------------------------------------------
// Clean query parameter helper
// ---------------------------------------------------------------------------

export function cleanQueryParams(params: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      result[key] = value;
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// API methods
// ---------------------------------------------------------------------------

export async function getDashboardMetricsApi(
  filters: DashboardFilters
): Promise<DashboardMetricsResponse> {
  const res = await apiClient.get<DashboardMetricsResponse>('/dashboard/metrics', {
    params: cleanQueryParams(filters),
  });
  return res.data;
}

export async function getAttendanceReportApi(
  params: ReportQueryParams
): Promise<AttendanceReportResponse> {
  const res = await apiClient.get<AttendanceReportResponse>('/reports/attendance', {
    params: cleanQueryParams(params),
  });
  return res.data;
}

export async function getWorkReportApi(params: ReportQueryParams): Promise<WorkReportResponse> {
  const res = await apiClient.get<WorkReportResponse>('/reports/work', {
    params: cleanQueryParams(params),
  });
  return res.data;
}

export async function getMaterialsReportApi(
  params: ReportQueryParams
): Promise<MaterialsReportResponse> {
  const res = await apiClient.get<MaterialsReportResponse>('/reports/materials', {
    params: cleanQueryParams(params),
  });
  return res.data;
}

export async function getProductivityReportApi(
  params: ReportQueryParams
): Promise<ProductivityReportResponse> {
  const res = await apiClient.get<ProductivityReportResponse>('/reports/productivity', {
    params: cleanQueryParams(params),
  });
  return res.data;
}

export async function getPaymentSummaryReportApi(
  params: ReportQueryParams
): Promise<PaymentSummaryResponse> {
  const res = await apiClient.get<PaymentSummaryResponse>('/reports/payment-summary', {
    params: cleanQueryParams(params),
  });
  return res.data;
}

export async function getInvoiceSummaryReportApi(
  params: ReportQueryParams
): Promise<InvoiceSummaryResponse> {
  const res = await apiClient.get<InvoiceSummaryResponse>('/reports/invoice-summary', {
    params: cleanQueryParams(params),
  });
  return res.data;
}

export async function fetchReportDataApi(
  reportType: ReportType,
  params: ReportQueryParams
): Promise<PaginatedReportResponse<any>> {
  switch (reportType) {
    case 'attendance':
      return getAttendanceReportApi(params);
    case 'work':
      return getWorkReportApi(params);
    case 'materials':
      return getMaterialsReportApi(params);
    case 'productivity':
      return getProductivityReportApi(params);
    case 'payment-summary':
      return getPaymentSummaryReportApi(params);
    case 'invoice-summary':
      return getInvoiceSummaryReportApi(params);
    default:
      throw new Error(`Unsupported report type: ${reportType}`);
  }
}

/**
 * Downloads report in requested format (xlsx or pdf).
 * Reuses the EXACT active filters object.
 */
export async function downloadReportExport(
  reportType: ReportType | string,
  format: 'xlsx' | 'pdf',
  filters: Record<string, any>
): Promise<void> {
  const params = cleanQueryParams({ ...filters, format });
  const response = await apiClient.get(`/reports/${reportType}/export`, {
    params,
    responseType: 'blob',
  });

  let filename = `${reportType}_report.${format}`;
  let disposition: string | undefined;
  if (response.headers) {
    if (typeof (response.headers as any).get === 'function') {
      disposition = (response.headers as any).get('content-disposition');
    } else if (response.headers['content-disposition']) {
      disposition = String(response.headers['content-disposition']);
    }
  }
  if (typeof disposition === 'string') {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match?.[1]) {
      filename = match[1];
    }
  }

  const blob = new Blob([response.data], {
    type:
      format === 'xlsx'
        ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        : 'application/pdf',
  });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.setAttribute('download', filename);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.parentNode?.removeChild(anchor);
  window.URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// React Query hooks
// ---------------------------------------------------------------------------

export function useDashboardMetrics(
  filters: DashboardFilters,
  enabled: boolean = true
): UseQueryResult<DashboardMetricsResponse, Error> {
  return useQuery({
    queryKey: ['dashboard-metrics', filters],
    queryFn: () => getDashboardMetricsApi(filters),
    enabled: Boolean(enabled && filters.date_from && filters.date_to),
  });
}

export function useReportData(
  reportType: ReportType,
  params: ReportQueryParams,
  enabled: boolean = true
): UseQueryResult<PaginatedReportResponse<any>, Error> {
  return useQuery({
    queryKey: ['report-data', reportType, params],
    queryFn: () => fetchReportDataApi(reportType, params),
    enabled: Boolean(enabled && params.date_from && params.date_to),
  });
}
