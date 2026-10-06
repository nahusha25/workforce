import React, { useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type {
  DashboardMetricsResponse,
  SiteProgressEntry,
  EmployeeProductivity,
} from '../../api/dashboard';
import styles from './DashboardCharts.module.css';

export interface DashboardChartsProps {
  data: DashboardMetricsResponse;
  isLoading?: boolean;
}

export const DashboardCharts: React.FC<DashboardChartsProps> = ({ data, isLoading = false }) => {
  // Extract all distinct categories across employee_productivity
  const availableCategories = useMemo(() => {
    const cats = new Set<string>();
    (data.employee_productivity || []).forEach((emp) => {
      (emp.by_category || []).forEach((c) => {
        if (c.category) cats.add(c.category);
      });
    });
    return Array.from(cats);
  }, [data.employee_productivity]);

  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Chart 1: Site Progress Data
  const siteProgressData = useMemo(() => {
    return (data.site_progress || []).map((site: SiteProgressEntry) => ({
      name: site.site_name,
      totalQuantity: Number(site.total_quantity) || 0,
      breakdown: site.category_breakdown || {},
    }));
  }, [data.site_progress]);

  // Chart 2: Employee Productivity Data - per category breakdown
  const productivityChartData = useMemo(() => {
    return (data.employee_productivity || []).map((emp: EmployeeProductivity) => {
      const row: Record<string, any> = {
        name: emp.employee_name,
        hours: Number(emp.total_approved_hours) || 0,
        by_category: emp.by_category || [],
      };

      // Populate category-specific quantities and ratios
      (emp.by_category || []).forEach((catEntry) => {
        const catKey = catEntry.category;
        row[`${catKey}_qty`] = Number(catEntry.total_quantity) || 0;
        row[`${catKey}_ratio`] = catEntry.ratio !== null ? Number(catEntry.ratio) : null;
        row[`${catKey}_label`] = catEntry.ratio_label;
        row[`${catKey}_uom`] = catEntry.uom;
      });

      return row;
    });
  }, [data.employee_productivity]);

  // Chart 3: Approval Status by Domain
  const approvalStatusData = useMemo(() => {
    const att = data.approval_status?.attendance || {
      approved: 0,
      submitted: 0,
      draft: 0,
      rejected: 0,
      correction_required: 0,
    };
    const wrk = data.approval_status?.work_entries || {
      approved: 0,
      submitted: 0,
      draft: 0,
      rejected: 0,
      correction_required: 0,
    };
    const mat = data.approval_status?.materials || {
      approved: 0,
      submitted: 0,
      draft: 0,
      rejected: 0,
      correction_required: 0,
    };

    return [
      {
        domain: 'Attendance',
        Approved: att.approved,
        Submitted: att.submitted,
        Draft: att.draft,
        Rejected: att.rejected,
        'Correction Req': att.correction_required,
      },
      {
        domain: 'Work Entries',
        Approved: wrk.approved,
        Submitted: wrk.submitted,
        Draft: wrk.draft,
        Rejected: wrk.rejected,
        'Correction Req': wrk.correction_required,
      },
      {
        domain: 'Materials',
        Approved: mat.approved,
        Submitted: mat.submitted,
        Draft: mat.draft,
        Rejected: mat.rejected,
        'Correction Req': mat.correction_required,
      },
    ];
  }, [data.approval_status]);

  if (isLoading) {
    return (
      <div className={styles.container} data-testid="dashboard-charts-loading">
        <div className={styles.chartsGrid}>
          <div className={styles.chartCard}>
            <div className={styles.chartBody}>
              <div className={styles.emptyChart}>Loading charts...</div>
            </div>
          </div>
          <div className={styles.chartCard}>
            <div className={styles.chartBody}>
              <div className={styles.emptyChart}>Loading charts...</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Category palette
  const categoryColors: Record<string, string> = {
    cable: '#0284c7',
    device: '#10b981',
    drilling: '#f59e0b',
    mounting: '#8b5cf6',
    testing: '#ec4899',
    commissioning: '#06b6d4',
  };

  return (
    <div className={styles.container} data-testid="dashboard-charts">
      <div className={styles.chartsGrid}>
        {/* Chart 1: Site Progress */}
        <div className={styles.chartCard} data-testid="site-progress-chart">
          <div className={styles.chartHeader}>
            <div>
              <h4 className={styles.chartTitle}>Site Output Progress</h4>
              <p className={styles.chartSubtitle}>Total approved work quantity across active sites</p>
            </div>
          </div>
          <div className={styles.chartBody}>
            {siteProgressData.length === 0 ? (
              <div className={styles.emptyChart}>No site progress data for period</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={siteProgressData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div
                          style={{
                            background: '#ffffff',
                            border: '1px solid #e2e8f0',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                          }}
                        >
                          <strong>{d.name}</strong>
                          <div style={{ color: '#0284c7', marginTop: '4px' }}>
                            Total Quantity: {d.totalQuantity}
                          </div>
                          {Object.keys(d.breakdown).length > 0 && (
                            <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b' }}>
                              Breakdown:
                              {Object.entries(d.breakdown).map(([cat, qty]) => (
                                <div key={cat}>
                                  {cat}: {Number(qty)}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="totalQuantity" fill="#0284c7" radius={[4, 4, 0, 0]} name="Total Quantity" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 2: Employee Productivity (Per-Category Breakdown) */}
        <div className={styles.chartCard} data-testid="employee-productivity-chart">
          <div className={styles.chartHeader}>
            <div>
              <h4 className={styles.chartTitle}>Employee Productivity Breakdown</h4>
              <p className={styles.chartSubtitle}>
                Output rates per category (never averaged across different units)
              </p>
            </div>
            {availableCategories.length > 0 && (
              <div className={styles.categorySelector}>
                <label htmlFor="productivity-cat-select" style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Category:
                </label>
                <select
                  id="productivity-cat-select"
                  className={styles.categorySelect}
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  data-testid="productivity-category-select"
                >
                  <option value="all">All Categories (Grouped)</option>
                  {availableCategories.map((c) => (
                    <option key={c} value={c}>
                      {c.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className={styles.chartBody}>
            {productivityChartData.length === 0 ? (
              <div className={styles.emptyChart}>No employee productivity data for period</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={productivityChartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div
                          style={{
                            background: '#ffffff',
                            border: '1px solid #e2e8f0',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                          }}
                        >
                          <strong>{d.name}</strong>
                          <div style={{ color: '#475569', fontSize: '12px' }}>
                            Approved Hours: {d.hours} hrs
                          </div>
                          <div style={{ marginTop: '6px', fontSize: '12px' }}>
                            <strong>Category Output:</strong>
                            {d.by_category.map((cat: any) => (
                              <div key={cat.category} style={{ color: categoryColors[cat.category] || '#0284c7' }}>
                                • {cat.category}: {cat.total_quantity} {cat.uom} ({cat.ratio_label})
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Legend />
                  {selectedCategory === 'all' ? (
                    availableCategories.map((cat) => (
                      <Bar
                        key={cat}
                        dataKey={`${cat}_qty`}
                        name={`${cat}`}
                        fill={categoryColors[cat] || '#8884d8'}
                        radius={[4, 4, 0, 0]}
                      />
                    ))
                  ) : (
                    <Bar
                      dataKey={`${selectedCategory}_qty`}
                      name={`${selectedCategory} Quantity`}
                      fill={categoryColors[selectedCategory] || '#0284c7'}
                      radius={[4, 4, 0, 0]}
                    />
                  )}
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Explicit Category Output Breakdown Chips */}
          {data.employee_productivity?.length > 0 && (
            <div style={{ marginTop: '0.75rem', overflowX: 'auto' }}>
              <table className={styles.productivityTable} data-testid="productivity-summary-table">
                <thead>
                  <tr>
                    <th>Top Employee</th>
                    <th>Approved Hours</th>
                    <th>Category Breakdown & Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {data.employee_productivity.slice(0, 5).map((emp) => (
                    <tr key={emp.employee_id}>
                      <td style={{ fontWeight: 600 }}>{emp.employee_name}</td>
                      <td>{Number(emp.total_approved_hours).toFixed(1)} hrs</td>
                      <td>
                        {emp.by_category.length === 0 ? (
                          <span style={{ color: '#94a3b8' }}>No recorded work items</span>
                        ) : (
                          emp.by_category.map((cat) => (
                            <span key={cat.category} className={styles.categoryBadge}>
                              <strong>{cat.category}:</strong> {cat.total_quantity} {cat.uom} ({cat.ratio_label})
                            </span>
                          ))
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Chart 3: Approval Status Overview */}
        <div className={styles.chartCard} data-testid="approval-status-chart" style={{ gridColumn: '1 / -1' }}>
          <div className={styles.chartHeader}>
            <div>
              <h4 className={styles.chartTitle}>Approval Status Overview</h4>
              <p className={styles.chartSubtitle}>
                Verification breakdown across Attendance, Work Entries, and Materials
              </p>
            </div>
          </div>
          <div className={styles.chartBody}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={approvalStatusData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="domain" stroke="#64748b" tick={{ fontSize: 12 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="Approved" fill="#10b981" />
                <Bar dataKey="Submitted" fill="#3b82f6" />
                <Bar dataKey="Draft" fill="#94a3b8" />
                <Bar dataKey="Rejected" fill="#ef4444" />
                <Bar dataKey="Correction Req" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
