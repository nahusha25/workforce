# Phase 5 — Frontend Plan

## Pages
- **5.1 Dashboard Overview**: Metric cards (manpower, hours, cable, devices, productivity, material cost, approval status), filter bar, summary charts
- **5.2 Report View**: Tabular data with filters, sortable columns, export buttons
- **5.3 Invoice Generation**: Period selector, site/employee selector, generate button, preview, finalise

## Components
| Component | Purpose |
|-----------|---------|
| MetricCard | Dashboard KPI card with value, label, trend indicator |
| FilterBar | Date range, client, site, employee, supervisor dropdowns |
| BarChart | Manpower by date, hours by date |
| LineChart | Trends over time |
| PieChart | Approval status breakdown |
| ReportTable | Sortable, filterable data table with pagination |
| ExportButton | Excel/PDF export trigger |
| InvoiceForm | Period + scope selection for invoice generation |
| InvoicePreview | Generated invoice with line items |
| InvoiceList | List of generated invoices |

## Charts
- Use a lightweight chart library (e.g., Chart.js or Recharts)
- Responsive: stack charts vertically on mobile, grid on desktop
- Colour-code status: approved (green), pending (blue), rejected (red)

## Desktop-First (for this phase)
Dashboard is primarily a desktop experience for directors. But must still be functional on tablet/mobile:
- **Desktop**: Multi-column grid of metric cards, side-by-side charts, full data tables
- **Tablet**: 2-column card grid, scrollable tables
- **Mobile**: Single-column cards, stacked charts, horizontal-scroll tables or card-based data

## Export UX
- Export buttons in report header
- Loading indicator during file generation
- Browser download of generated file
- Toast notification on success
