"""
Phase 5 — Report Export Service (Excel & PDF) (BE-030, BE-031).
Generates in-memory streaming responses using openpyxl and ReportLab.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional, Tuple

import openpyxl
from fastapi import HTTPException, status
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.schemas import DashboardFilters
from app.modules.dashboard.service import DashboardService

ALLOWED_REPORT_TYPES = {
    "attendance",
    "work",
    "materials",
    "productivity",
    "payment-summary",
    "invoice-summary",
}

REPORT_TYPE_ALIASES = {
    "payment": "payment-summary",
    "payment_summary": "payment-summary",
    "invoice": "invoice-summary",
    "invoice_summary": "invoice-summary",
}


def normalize_report_type(raw_type: str) -> str:
    cleaned = raw_type.strip().lower()
    cleaned = REPORT_TYPE_ALIASES.get(cleaned, cleaned)
    if cleaned not in ALLOWED_REPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported report_type '{raw_type}'. Allowed types: "
                "attendance, work, materials, productivity, payment-summary, invoice-summary"
            ),
        )
    return cleaned


def normalize_export_format(raw_format: str) -> str:
    fmt = raw_format.strip().lower()
    if fmt not in {"xlsx", "pdf"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid format. Allowed formats: 'xlsx', 'pdf'",
        )
    return fmt


def format_currency(val: Any) -> str:
    """Format currency values matching project precision standard: exactly 2 decimal places (e.g. 150.00)."""
    if val is None:
        return "0.00"
    try:
        dec = Decimal(str(val))
        return f"{dec:.2f}"
    except Exception:
        return "0.00"



# ---------------------------------------------------------------------------
# Data preparation per report type
# ---------------------------------------------------------------------------

async def fetch_report_export_data(
    session: AsyncSession,
    report_type: str,
    filters: DashboardFilters,
    **extra_kwargs: Any,
) -> Tuple[str, List[str], List[List[Any]]]:
    """
    Fetches unpaginated data (page_size=10000) and formats it into (title, headers, rows).
    """
    norm_type = normalize_report_type(report_type)

    if norm_type == "attendance":
        title = "Attendance History Report"
        status_filter = extra_kwargs.get("status", "approved")
        resp = await DashboardService.get_attendance_report(
            session=session,
            f=filters,
            page=1,
            page_size=10000,
            status_filter=status_filter,
        )
        headers = [
            "Date",
            "Employee Name",
            "Site Name",
            "Check-In",
            "Check-Out",
            "Working Hours",
            "Overtime Hours",
            "Status",
            "In Geofence",
        ]
        rows = [
            [
                str(r.date),
                r.employee_name,
                r.site_name,
                r.check_in_time.strftime("%H:%M") if r.check_in_time else "-",
                r.check_out_time.strftime("%H:%M") if r.check_out_time else "-",
                str(r.working_hours if r.working_hours is not None else 0),
                str(r.overtime_hours if r.overtime_hours is not None else 0),
                r.status,
                "Yes" if r.is_within_geofence else "No",
            ]
            for r in resp.data
        ]
        return title, headers, rows

    elif norm_type == "work":
        title = "Daily Work Progress Report"
        resp = await DashboardService.get_work_report(
            session=session,
            f=filters,
            page=1,
            page_size=10000,
            activity_id=extra_kwargs.get("activity_id"),
            work_order_id=extra_kwargs.get("work_order_id"),
        )
        headers = [
            "Work Date",
            "Employee Name",
            "Site Name",
            "Activity Name",
            "Category",
            "Quantity",
            "UOM",
            "Status",
        ]
        rows = [
            [
                str(r.work_date),
                r.employee_name,
                r.site_name,
                r.activity_name,
                r.category,
                str(r.quantity),
                r.uom,
                r.status,
            ]
            for r in resp.data
        ]
        return title, headers, rows

    elif norm_type == "materials":
        title = "Material Transactions Report"
        resp = await DashboardService.get_materials_report(
            session=session,
            f=filters,
            page=1,
            page_size=10000,
            transaction_type=extra_kwargs.get("transaction_type"),
            is_high_value=extra_kwargs.get("is_high_value"),
            status=extra_kwargs.get("status"),
        )
        headers = [
            "Date",
            "Item Name",
            "Employee Name",
            "Site Name",
            "Transaction Type",
            "Quantity",
            "Amount (INR)",
            "High Value",
            "Status",
        ]
        rows = [
            [
                r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "-",
                r.item_name,
                r.employee_name,
                r.site_name,
                r.transaction_type,
                str(r.quantity),
                format_currency(r.amount),
                "Yes" if r.is_high_value else "No",
                r.status,
            ]
            for r in resp.data
        ]
        return title, headers, rows

    elif norm_type == "productivity":
        title = "Employee Productivity Report"
        resp = await DashboardService.get_productivity_report(
            session=session,
            f=filters,
            page=1,
            page_size=10000,
            sort_category=extra_kwargs.get("sort_category"),
        )
        headers = [
            "Employee Name",
            "Total Approved Hours",
            "Activity Category",
            "Output Quantity",
            "UOM",
            "Output Rate",
            "Productivity Metric",
        ]
        rows = []
        for r in resp.data:
            if r.by_category:
                for cat in r.by_category:
                    rows.append([
                        r.employee_name,
                        str(r.total_approved_hours),
                        cat.category,
                        str(cat.total_quantity),
                        cat.uom,
                        str(cat.ratio) if cat.ratio is not None else "-",
                        cat.ratio_label,
                    ])
            else:
                rows.append([
                    r.employee_name,
                    str(r.total_approved_hours),
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                ])
        return title, headers, rows

    elif norm_type == "payment-summary":
        title = "Weekly Payment Summary (Estimated Preview)"
        resp = await DashboardService.get_payment_summary_report(
            session=session,
            f=filters,
            page=1,
            page_size=10000,
        )
        headers = [
            "Employee Name",
            "Rate Type",
            "Effective From",
            "Effective To",
            "Approved Days",
            "Approved Quantity",
            "Effective Rate (INR)",
            "Estimated Gross (INR)",
        ]
        rows = [
            [
                r.employee_name,
                r.rate_type,
                str(r.rate_effective_from),
                str(r.rate_effective_to or "Ongoing"),
                str(r.approved_days),
                str(r.approved_quantity),
                format_currency(r.effective_rate),
                format_currency(r.estimated_gross),
            ]
            for r in resp.data
        ]
        return title, headers, rows

    elif norm_type == "invoice-summary":
        title = "Client & Site Invoice Summary"
        resp = await DashboardService.get_invoice_summary_report(
            session=session,
            f=filters,
            page=1,
            page_size=10000,
        )
        headers = [
            "Site Name",
            "Client Name",
            "Total Labour Days",
            "Total Work Quantity",
            "Total Material Cost (INR)",
        ]
        rows = [
            [
                r.site_name,
                r.client_name,
                str(r.total_labour_days),
                str(r.total_work_quantity),
                format_currency(r.total_material_cost),
            ]
            for r in resp.data
        ]
        return title, headers, rows

    raise HTTPException(status_code=422, detail="Invalid report type")


# ---------------------------------------------------------------------------
# Excel Generator
# ---------------------------------------------------------------------------

def generate_excel(title: str, headers: List[str], rows: List[List[Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]

    # Title Banner
    ws.append([f"Workforce Management — {title}"])
    ws.row_dimensions[1].height = 24
    ws.cell(row=1, column=1).font = Font(name="Calibri", size=13, bold=True, color="1F2937")

    # Timestamp subtitle
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ws.append([f"Generated on {now_str}"])
    ws.cell(row=2, column=1).font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    ws.append([])  # blank spacer

    # Header Row
    ws.append(headers)
    header_row_idx = 4
    ws.row_dimensions[header_row_idx].height = 20
    header_fill = PatternFill(start_color="374151", end_color="374151", fill_type="solid")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="E5E7EB"),
        right=Side(style="thin", color="E5E7EB"),
        top=Side(style="thin", color="E5E7EB"),
        bottom=Side(style="thin", color="E5E7EB"),
    )

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # Data Rows
    row_font = Font(name="Calibri", size=9, color="111827")
    zebra_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    start_data_idx = 5
    for r_offset, row_data in enumerate(rows):
        current_r = start_data_idx + r_offset
        ws.append(row_data)
        ws.row_dimensions[current_r].height = 18
        is_even = (r_offset % 2 == 1)

        for c_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=current_r, column=c_idx)
            cell.font = row_font
            cell.border = thin_border
            if is_even:
                cell.fill = zebra_fill
            val = cell.value
            if isinstance(val, (int, float, Decimal)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Auto column width
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.row < header_row_idx:
                continue
            val_str = str(cell.value or "")
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# PDF Generator
# ---------------------------------------------------------------------------

def generate_pdf(title: str, headers: List[str], rows: List[List[Any]]) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=25,
        rightMargin=25,
        topMargin=25,
        bottomMargin=25,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=10,
    )

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    elements = [
        Paragraph(f"Workforce Management — {title}", title_style),
        Paragraph(f"Generated on {now_str} • Confirmed & Approved Data Only", sub_style),
        Spacer(1, 6),
    ]

    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#111827"),
    )
    header_style = ParagraphStyle(
        "HeaderCellText",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    table_data = [[Paragraph(h, header_style) for h in headers]]

    for row in rows:
        row_cells = []
        for val in row:
            txt = str(val) if val is not None else "-"
            row_cells.append(Paragraph(txt, cell_style))
        table_data.append(row_cells)

    if len(table_data) == 1:
        empty_style = ParagraphStyle("EmptyText", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Oblique")
        table_data.append([Paragraph("No records found", empty_style)] + [Paragraph("", cell_style)] * (len(headers) - 1))

    table = Table(table_data, repeatRows=1)
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for r in range(1, len(table_data)):
        if r % 2 == 0:
            t_style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F9FAFB")))

    table.setStyle(TableStyle(t_style))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# High-level dispatcher
# ---------------------------------------------------------------------------

async def export_report(
    session: AsyncSession,
    report_type: str,
    export_format: str,
    filters: DashboardFilters,
    **extra_kwargs: Any,
) -> Tuple[io.BytesIO, str, str]:
    """
    Validates params, fetches data, builds Excel or PDF, and returns:
    (buffer, media_type, filename).
    """
    norm_type = normalize_report_type(report_type)
    norm_format = normalize_export_format(export_format)

    title, headers, rows = await fetch_report_export_data(
        session=session,
        report_type=norm_type,
        filters=filters,
        **extra_kwargs,
    )

    filename = f"{norm_type}_{filters.date_from}_{filters.date_to}.{norm_format}"

    if norm_format == "xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        buf = generate_excel(title, headers, rows)
    else:
        media_type = "application/pdf"
        buf = generate_pdf(title, headers, rows)

    return buf, media_type, filename
