import React, { useState } from 'react';
import { FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { downloadReportExport } from '../../api/dashboard';
import styles from './ExportButtonGroup.module.css';

export interface ExportButtonGroupProps {
  reportType: string;
  filters: Record<string, any>;
  disabled?: boolean;
}

export const ExportButtonGroup: React.FC<ExportButtonGroupProps> = ({
  reportType,
  filters,
  disabled = false,
}) => {
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = async (format: 'xlsx' | 'pdf') => {
    setExportError(null);
    if (format === 'xlsx') {
      setIsExportingExcel(true);
    } else {
      setIsExportingPdf(true);
    }

    try {
      // Passes the EXACT active filters applied on screen
      await downloadReportExport(reportType, format, filters);
    } catch (err: any) {
      console.error(`Export failed for ${reportType} (${format}):`, err);
      const msg = err.response?.data?.detail || err.message || 'Export failed. Please try again.';
      setExportError(msg);
    } finally {
      if (format === 'xlsx') {
        setIsExportingExcel(false);
      } else {
        setIsExportingPdf(false);
      }
    }
  };

  const isBusy = isExportingExcel || isExportingPdf;

  return (
    <div>
      <div className={styles.group} data-testid="export-button-group">
        <button
          type="button"
          className={`${styles.exportBtn} ${styles.excelBtn}`}
          onClick={() => handleExport('xlsx')}
          disabled={disabled || isBusy}
          data-testid="export-excel-btn"
          aria-label="Export report to Excel"
        >
          {isExportingExcel ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <FileSpreadsheet size={16} />
          )}
          <span>{isExportingExcel ? 'Exporting...' : 'Export Excel'}</span>
        </button>

        <button
          type="button"
          className={`${styles.exportBtn} ${styles.pdfBtn}`}
          onClick={() => handleExport('pdf')}
          disabled={disabled || isBusy}
          data-testid="export-pdf-btn"
          aria-label="Export report to PDF"
        >
          {isExportingPdf ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <FileText size={16} />
          )}
          <span>{isExportingPdf ? 'Exporting...' : 'Export PDF'}</span>
        </button>
      </div>

      {exportError && (
        <div className={styles.errorToast} role="alert" data-testid="export-error-alert">
          {exportError}
        </div>
      )}
    </div>
  );
};
