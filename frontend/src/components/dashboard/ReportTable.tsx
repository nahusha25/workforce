import React from 'react';
import { ChevronLeft, ChevronRight, Info } from 'lucide-react';
import { formatDecimal } from '../MaterialTransactionEntry';
import { StatusBadge } from '../ui/StatusBadge';
import type {
  ReportType,
  AttendanceReportRow,
  WorkReportRow,
  MaterialsReportRow,
  ProductivityReportRow,
  PaymentSummaryRow,
  InvoiceSummaryRow,
} from '../../api/dashboard';
import styles from './ReportTable.module.css';

export interface ReportTableProps {
  reportType: ReportType;
  data: any[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  onPageSizeChange?: (newSize: number) => void;
  isLoading?: boolean;
}

export const ReportTable: React.FC<ReportTableProps> = ({
  reportType,
  data,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  isLoading = false,
}) => {
  const totalPages = Math.ceil(total / pageSize) || 1;

  const renderTableHeaders = () => {
    switch (reportType) {
      case 'attendance':
        return (
          <tr>
            <th>Employee</th>
            <th>Site</th>
            <th>Date</th>
            <th>Check In</th>
            <th>Check Out</th>
            <th>Working Hours</th>
            <th>Overtime</th>
            <th>Geofence</th>
            <th>Status</th>
          </tr>
        );
      case 'work':
        return (
          <tr>
            <th>Employee</th>
            <th>Site</th>
            <th>Work Date</th>
            <th>Activity</th>
            <th>Category</th>
            <th>Quantity</th>
            <th>UOM</th>
            <th>Status</th>
          </tr>
        );
      case 'materials':
        return (
          <tr>
            <th>Date</th>
            <th>Employee</th>
            <th>Site</th>
            <th>Item</th>
            <th>Type</th>
            <th>Quantity</th>
            <th>Amount</th>
            <th>Flag</th>
            <th>Status</th>
          </tr>
        );
      case 'productivity':
        return (
          <tr>
            <th>Employee</th>
            <th>Approved Hours</th>
            <th>Output by Category & Rate</th>
          </tr>
        );
      case 'payment-summary':
        return (
          <tr>
            <th>Employee</th>
            <th>Rate Type</th>
            <th>Effective Band</th>
            <th>Approved Days</th>
            <th>Approved Quantity</th>
            <th>Effective Rate</th>
            <th>Estimated Gross</th>
          </tr>
        );
      case 'invoice-summary':
        return (
          <tr>
            <th>Client</th>
            <th>Site</th>
            <th>Total Labour Days</th>
            <th>Total Work Qty</th>
            <th>Total Material Cost</th>
          </tr>
        );
      default:
        return null;
    }
  };

  const renderTableRows = () => {
    if (isLoading) {
      return (
        <tr>
          <td colSpan={10} className={styles.loadingOverlay} data-testid="report-table-loading">
            Loading report records...
          </td>
        </tr>
      );
    }

    if (!data || data.length === 0) {
      return (
        <tr>
          <td colSpan={10} className={styles.emptyState} data-testid="report-table-empty">
            No report records found for the selected criteria.
          </td>
        </tr>
      );
    }

    switch (reportType) {
      case 'attendance':
        return (data as AttendanceReportRow[]).map((row) => (
          <tr key={row.attendance_id} data-testid={`attendance-row-${row.attendance_id}`}>
            <td style={{ fontWeight: 600 }}>{row.employee_name}</td>
            <td>{row.site_name}</td>
            <td>{row.date}</td>
            <td>{row.check_in_time ? new Date(row.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}</td>
            <td>{row.check_out_time ? new Date(row.check_out_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}</td>
            <td>{row.working_hours !== null ? `${Number(row.working_hours).toFixed(2)}h` : '-'}</td>
            <td>{row.overtime_hours !== null ? `${Number(row.overtime_hours).toFixed(2)}h` : '-'}</td>
            <td>
              {row.is_within_geofence === true && <span style={{ color: '#16a34a' }}>Inside</span>}
              {row.is_within_geofence === false && <span style={{ color: '#dc2626' }}>Outside</span>}
              {row.is_within_geofence === null && <span style={{ color: '#94a3b8' }}>-</span>}
            </td>
            <td>
              <StatusBadge status={row.status} />
            </td>
          </tr>
        ));

      case 'work':
        return (data as WorkReportRow[]).map((row) => (
          <tr key={row.entry_id} data-testid={`work-row-${row.entry_id}`}>
            <td style={{ fontWeight: 600 }}>{row.employee_name}</td>
            <td>{row.site_name}</td>
            <td>{row.work_date}</td>
            <td>{row.activity_name}</td>
            <td>
              <span className={styles.categoryTag}>{row.category}</span>
            </td>
            <td style={{ fontWeight: 600 }}>{Number(row.quantity)}</td>
            <td>{row.uom}</td>
            <td>
              <StatusBadge status={row.status} />
            </td>
          </tr>
        ));

      case 'materials':
        return (data as MaterialsReportRow[]).map((row) => (
          <tr key={row.transaction_id} data-testid={`materials-row-${row.transaction_id}`}>
            <td>{new Date(row.created_at).toLocaleDateString()}</td>
            <td style={{ fontWeight: 600 }}>{row.employee_name}</td>
            <td>{row.site_name}</td>
            <td>{row.item_name}</td>
            <td style={{ textTransform: 'capitalize' }}>{row.transaction_type}</td>
            <td>{Number(row.quantity)}</td>
            <td style={{ fontWeight: 600 }}>₹{formatDecimal(row.amount)}</td>
            <td>
              {row.is_high_value && <span className={`${styles.badge} ${styles.badgeHighValue}`}>High Value</span>}
            </td>
            <td>
              <StatusBadge status={row.status} />
            </td>
          </tr>
        ));

      case 'productivity':
        return (data as ProductivityReportRow[]).map((row) => (
          <tr key={row.employee_id} data-testid={`productivity-row-${row.employee_id}`}>
            <td style={{ fontWeight: 600 }}>{row.employee_name}</td>
            <td>{Number(row.total_approved_hours).toFixed(2)} hrs</td>
            <td>
              <div className={styles.categoryBreakdown}>
                {row.by_category.length === 0 ? (
                  <span style={{ color: '#94a3b8' }}>No recorded activity</span>
                ) : (
                  row.by_category.map((cat) => (
                    <span key={cat.category} className={styles.categoryTag} data-testid={`cat-tag-${cat.category}`}>
                      <strong>{cat.category}:</strong> {Number(cat.total_quantity)} {cat.uom} ({cat.ratio_label})
                    </span>
                  ))
                )}
              </div>
            </td>
          </tr>
        ));

      case 'payment-summary':
        return (data as PaymentSummaryRow[]).map((row, idx) => (
          <tr key={`${row.employee_id}-${row.rate_effective_from}-${idx}`} data-testid={`payment-row-${idx}`}>
            <td style={{ fontWeight: 600 }}>{row.employee_name}</td>
            <td style={{ textTransform: 'capitalize' }}>{row.rate_type}</td>
            <td>
              {row.rate_effective_from} to {row.rate_effective_to || 'Present'}
            </td>
            <td>{row.approved_days} days</td>
            <td>{Number(row.approved_quantity)}</td>
            <td>₹{formatDecimal(row.effective_rate)}</td>
            <td style={{ fontWeight: 700, color: '#047857' }}>₹{formatDecimal(row.estimated_gross)}</td>
          </tr>
        ));

      case 'invoice-summary':
        return (data as InvoiceSummaryRow[]).map((row) => (
          <tr key={row.site_id} data-testid={`invoice-row-${row.site_id}`}>
            <td style={{ fontWeight: 600 }}>{row.client_name}</td>
            <td>{row.site_name}</td>
            <td>{row.total_labour_days} days</td>
            <td>{Number(row.total_work_quantity)}</td>
            <td style={{ fontWeight: 700 }}>₹{formatDecimal(row.total_material_cost)}</td>
          </tr>
        ));

      default:
        return null;
    }
  };

  return (
    <div className={styles.tableWrapper} data-testid="report-table-wrapper">
      {reportType === 'payment-summary' && (
        <div className={styles.disclaimerBanner} data-testid="payment-disclaimer-banner">
          <Info size={16} />
          <span>
            <strong>Preview Only:</strong> Rates reflect effective-dated values from employee rate history. No payment records have been finalized.
          </span>
        </div>
      )}

      <div className={styles.tableContainer}>
        <table className={styles.table} data-testid="report-table">
          <thead>{renderTableHeaders()}</thead>
          <tbody>{renderTableRows()}</tbody>
        </table>
      </div>

      <div className={styles.paginationBar}>
        <div>
          Showing {data.length > 0 ? (page - 1) * pageSize + 1 : 0} to{' '}
          {Math.min(page * pageSize, total)} of {total} records
        </div>

        <div className={styles.pageControls}>
          {onPageSizeChange && (
            <select
              className={styles.pageSizeSelect}
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              disabled={isLoading}
              data-testid="page-size-select"
            >
              <option value={20}>20 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          )}

          <button
            type="button"
            className={styles.pageBtn}
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || isLoading}
            data-testid="prev-page-btn"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>

          <span>
            Page {page} of {totalPages}
          </span>

          <button
            type="button"
            className={styles.pageBtn}
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || isLoading}
            data-testid="next-page-btn"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
