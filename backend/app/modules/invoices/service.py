from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import User
from app.models.invoices import Invoice, InvoiceLineItem
from app.models.operations import Activity, Client, DailyWorkEntry, Material, MaterialTransaction, Project, Site
from app.models.system import AuditLog
from app.modules.invoices.schemas import (
    CancelInvoiceRequest,
    GenerateInvoiceRequest,
    InvoiceDetailResponse,
    InvoiceLineItemResponse,
    InvoiceLinePreviewItem,
    InvoicePreviewResponse,
    InvoiceResponse,
    IssueInvoiceRequest,
    RateOverrideItem,
    UpdateDraftInvoiceRequest,
)


class InvoiceService:
    @staticmethod
    async def _generate_invoice_number(session: AsyncSession) -> str:
        """
        Generates a forward-only invoice number using the PostgreSQL sequence.
        Format: INV-YYYYMMDD-XXXX (e.g. INV-20261008-0001, expanding naturally to INV-20261008-10000+).
        Never uses COUNT(*) + 1 and never wraps using modulo.
        PostgreSQL sequences guarantee uniqueness and concurrency safety; sequence gaps resulting from
        transaction rollbacks or concurrent failures are acceptable and expected.
        """
        seq_val = (await session.execute(text("SELECT nextval('invoice_number_seq')"))).scalar()
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"INV-{today_str}-{seq_val:04d}"

    @classmethod
    async def _validate_hierarchy(
        cls,
        session: AsyncSession,
        client_id: uuid.UUID,
        project_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> Tuple[Client, Project, Site]:
        """
        Enforces site -> project -> client hierarchical scoping.
        Ensures the selected site belongs to the project, and the project belongs to the client.
        """
        client = await session.get(Client, client_id)
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")

        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if project.client_id != client_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Project '{project.name}' ({project_id}) does not belong to client '{client.name}' ({client_id}).",
            )

        site = await session.get(Site, site_id)
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found.")
        if site.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Site '{site.name}' ({site_id}) does not belong to project '{project.name}' ({project_id}).",
            )

        return client, project, site

    @classmethod
    async def _fetch_unbilled_work_entries(
        cls,
        session: AsyncSession,
        site_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> List[Tuple[DailyWorkEntry, Activity]]:
        """
        Fetch approved daily work entries for the site and period that are not locked by an active invoice line item.
        """
        stmt = (
            select(DailyWorkEntry, Activity)
            .join(Activity, DailyWorkEntry.activity_id == Activity.id)
            .where(
                DailyWorkEntry.site_id == site_id,
                DailyWorkEntry.status == "approved",
                DailyWorkEntry.work_date >= period_start,
                DailyWorkEntry.work_date <= period_end,
                ~DailyWorkEntry.id.in_(
                    select(InvoiceLineItem.source_daily_work_entry_id).where(
                        InvoiceLineItem.is_active.is_(True),
                        InvoiceLineItem.source_daily_work_entry_id.isnot(None),
                    )
                ),
            )
            .order_by(DailyWorkEntry.work_date.asc(), DailyWorkEntry.created_at.asc())
        )
        return (await session.execute(stmt)).all()

    @classmethod
    async def _fetch_unbilled_material_transactions(
        cls,
        session: AsyncSession,
        site_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> List[Tuple[MaterialTransaction, DailyWorkEntry, Optional[Material]]]:
        """
        Fetch approved material transactions for the site whose parent DailyWorkEntry.work_date falls
        within the billing period, excluding records locked by an active invoice line item.
        RULE: Material billing uses DailyWorkEntry.work_date, never MaterialTransaction.created_at.
        """
        stmt = (
            select(MaterialTransaction, DailyWorkEntry, Material)
            .join(DailyWorkEntry, MaterialTransaction.daily_work_entry_id == DailyWorkEntry.id)
            .outerjoin(Material, MaterialTransaction.material_id == Material.id)
            .where(
                MaterialTransaction.site_id == site_id,
                MaterialTransaction.status == "approved",
                DailyWorkEntry.work_date >= period_start,
                DailyWorkEntry.work_date <= period_end,
                ~MaterialTransaction.id.in_(
                    select(InvoiceLineItem.source_material_transaction_id).where(
                        InvoiceLineItem.is_active.is_(True),
                        InvoiceLineItem.source_material_transaction_id.isnot(None),
                    )
                ),
            )
            .order_by(DailyWorkEntry.work_date.asc(), MaterialTransaction.created_at.asc())
        )
        return (await session.execute(stmt)).all()

    @classmethod
    async def preview_invoice(
        cls,
        session: AsyncSession,
        client_id: uuid.UUID,
        project_id: uuid.UUID,
        site_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> InvoicePreviewResponse:
        """
        Generates an uncommitted financial preview of unbilled approved work and material records
        for a single client, project, site, and date range.
        """
        if period_end < period_start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="period_end must be greater than or equal to period_start.",
            )

        client, project, site = await cls._validate_hierarchy(session, client_id, project_id, site_id)
        work_entries = await cls._fetch_unbilled_work_entries(session, site_id, period_start, period_end)
        material_txs = await cls._fetch_unbilled_material_transactions(session, site_id, period_start, period_end)

        items: List[InvoiceLinePreviewItem] = []
        subtotal_work = Decimal("0.00")
        subtotal_material = Decimal("0.00")

        # 1. Preview Work Entries
        for dwe, act in work_entries:
            qty = Decimal(str(dwe.quantity))
            std_rate = Decimal(str(act.approved_rate))
            unit_rate = std_rate
            line_amt = (qty * unit_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subtotal_work += line_amt

            items.append(
                InvoiceLinePreviewItem(
                    source_type="work",
                    source_id=dwe.id,
                    source_date=dwe.work_date,
                    item_description=act.name,
                    quantity=qty,
                    uom=dwe.uom,
                    standard_rate=std_rate,
                    unit_rate=unit_rate,
                    line_amount=line_amt,
                )
            )

        # 2. Preview Material Transactions
        for mt, dwe, mat in material_txs:
            qty = Decimal(str(mt.quantity))
            # Financial rule: preserve actual approved cost exactly
            line_amt = Decimal(str(mt.amount))
            subtotal_material += line_amt
            unit_rate = (line_amt / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if qty > 0 else Decimal("0.00")

            items.append(
                InvoiceLinePreviewItem(
                    source_type="material",
                    source_id=mt.id,
                    source_date=dwe.work_date,
                    item_description=mt.item_name,
                    quantity=qty,
                    uom=mat.unit_of_measure if mat else "nos",
                    standard_rate=unit_rate,
                    unit_rate=unit_rate,
                    line_amount=line_amt,
                )
            )

        subtotal_work = subtotal_work.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal_material = subtotal_material.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        estimated_tax = Decimal("0.00")
        estimated_total = subtotal_work + subtotal_material + estimated_tax

        return InvoicePreviewResponse(
            client_id=client.id,
            client_name=client.name,
            project_id=project.id,
            project_name=project.name,
            site_id=site.id,
            site_name=site.name,
            period_start=period_start,
            period_end=period_end,
            billable_work_count=len(work_entries),
            billable_material_count=len(material_txs),
            subtotal_work=subtotal_work,
            subtotal_material=subtotal_material,
            estimated_tax=estimated_tax,
            estimated_total=estimated_total,
            items=items,
        )

    @classmethod
    async def generate_invoice(
        cls,
        session: AsyncSession,
        request: GenerateInvoiceRequest,
        current_user: User,
    ) -> InvoiceDetailResponse:
        """
        Generates a draft invoice from unbilled approved work and material records.
        Snapshots line details, applies optional Director-only rate overrides,
        calculates financial totals using Decimal, and prevents double billing via DB locks.
        Idempotent via idempotency_key.
        """
        # 1. Idempotency Check
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.idempotency_key == request.idempotency_key)
        )
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            # Validate that idempotency key was not reused with conflicting parameters
            if (
                existing.client_id != request.client_id
                or existing.project_id != request.project_id
                or existing.site_id != request.site_id
                or existing.period_start != request.period_start
                or existing.period_end != request.period_end
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key was previously used with different billing parameters.",
                )
            return await cls._build_invoice_detail(session, existing)

        # 2. Scope & Hierarchy Validation
        client, project, site = await cls._validate_hierarchy(
            session, request.client_id, request.project_id, request.site_id
        )

        # 3. Fetch eligible unbilled records
        work_entries = await cls._fetch_unbilled_work_entries(
            session, request.site_id, request.period_start, request.period_end
        )
        material_txs = await cls._fetch_unbilled_material_transactions(
            session, request.site_id, request.period_start, request.period_end
        )

        if len(work_entries) == 0 and len(material_txs) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No unbilled approved records found for the specified period and site.",
            )

        # 4. Process Rate Overrides
        overrides_map: Dict[uuid.UUID, RateOverrideItem] = {}
        if request.rate_overrides:
            if current_user.role not in ("director", "administrator"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only directors can override invoice billing rates.",
                )
            for ro in request.rate_overrides:
                overrides_map[ro.source_id] = ro

        # 5. Create Invoice Header
        invoice_number = await cls._generate_invoice_number(session)
        inv = Invoice(
            id=uuid.uuid4(),
            invoice_number=invoice_number,
            idempotency_key=request.idempotency_key,
            client_id=request.client_id,
            project_id=request.project_id,
            site_id=request.site_id,
            period_start=request.period_start,
            period_end=request.period_end,
            status="draft",
            client_po_number=request.client_po_number,
            notes=request.notes,
            remarks=request.remarks,
            created_by=current_user.id,
        )

        lines: List[InvoiceLineItem] = []
        subtotal_work = Decimal("0.00")
        subtotal_material = Decimal("0.00")

        # 6. Build Work Lines
        for dwe, act in work_entries:
            qty = Decimal(str(dwe.quantity))
            if qty <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invoice line quantity must be strictly positive for daily work entry {dwe.id}.",
                )
            std_rate = Decimal(str(act.approved_rate))

            ro = overrides_map.get(dwe.id)
            if ro and ro.unit_rate != std_rate:
                if not ro.rate_override_reason or not ro.rate_override_reason.strip():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"rate_override_reason is mandatory for rate override on work entry {dwe.id}.",
                    )
                unit_rate = ro.unit_rate
                override_reason = ro.rate_override_reason.strip()
            else:
                unit_rate = std_rate
                override_reason = ro.rate_override_reason.strip() if ro and ro.rate_override_reason else None

            line_amt = (qty * unit_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subtotal_work += line_amt

            line = InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv.id,
                line_type="work",
                source_daily_work_entry_id=dwe.id,
                source_material_transaction_id=None,
                source_date=dwe.work_date,
                item_description=act.name,
                quantity=qty,
                uom=dwe.uom,
                standard_rate=std_rate,
                unit_rate=unit_rate,
                line_amount=line_amt,
                rate_override_reason=override_reason,
                is_active=True,
            )
            lines.append(line)

        # 7. Build Material Lines
        for mt, dwe, mat in material_txs:
            qty = Decimal(str(mt.quantity))
            if qty <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invoice line quantity must be strictly positive for material transaction {mt.id}.",
                )
            # Financial rule: preserve actual approved cost exactly
            line_amt = Decimal(str(mt.amount))
            subtotal_material += line_amt
            unit_rate = (line_amt / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if qty > 0 else Decimal("0.00")

            line = InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv.id,
                line_type="material",
                source_daily_work_entry_id=None,
                source_material_transaction_id=mt.id,
                source_date=dwe.work_date,  # strict snapshot of DailyWorkEntry.work_date
                item_description=mt.item_name,
                quantity=qty,
                uom=mat.unit_of_measure if mat else "nos",
                standard_rate=unit_rate,
                unit_rate=unit_rate,
                line_amount=line_amt,
                rate_override_reason=None,
                is_active=True,
            )
            lines.append(line)

        # 8. Calculate Financial Totals
        inv.subtotal_work = subtotal_work.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        inv.subtotal_material = subtotal_material.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        inv.tax_amount = Decimal(str(request.tax_amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        inv.total_amount = inv.subtotal_work + inv.subtotal_material + inv.tax_amount
        inv.paid_amount = Decimal("0.00")

        inv.lines = lines
        session.add(inv)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            # Check if idempotency key collided due to concurrent generation
            res = await session.execute(
                select(Invoice).options(selectinload(Invoice.lines)).where(Invoice.idempotency_key == request.idempotency_key)
            )
            existing = res.scalars().first()
            if existing:
                return await cls._build_invoice_detail(session, existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrency conflict: one or more source records have already been locked by another active invoice.",
            )

        return await cls._build_invoice_detail(session, inv)

    @classmethod
    async def get_invoice(cls, session: AsyncSession, invoice_id: uuid.UUID) -> InvoiceDetailResponse:
        """Fetch full invoice details by primary key."""
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id)
            .execution_options(populate_existing=True)
        )
        inv = (await session.execute(stmt)).scalars().first()
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
        return await cls._build_invoice_detail(session, inv)

    @classmethod
    async def list_invoices(
        cls,
        session: AsyncSession,
        client_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        site_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[InvoiceResponse]:
        """List invoices matching query filters."""
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.client),
                selectinload(Invoice.project),
                selectinload(Invoice.site),
            )
            .order_by(Invoice.created_at.desc())
        )
        if client_id:
            stmt = stmt.where(Invoice.client_id == client_id)
        if project_id:
            stmt = stmt.where(Invoice.project_id == project_id)
        if site_id:
            stmt = stmt.where(Invoice.site_id == site_id)
        if status_filter:
            stmt = stmt.where(Invoice.status == status_filter)
        if period_start:
            stmt = stmt.where(Invoice.period_start >= period_start)
        if period_end:
            stmt = stmt.where(Invoice.period_end <= period_end)

        stmt = stmt.offset(offset).limit(limit)
        invoices = (await session.execute(stmt)).scalars().all()

        results: List[InvoiceResponse] = []
        for inv in invoices:
            resp = InvoiceResponse.model_validate(inv)
            resp.client_name = inv.client.name if inv.client else None
            resp.project_name = inv.project.name if inv.project else None
            resp.site_name = inv.site.name if inv.site else None
            results.append(resp)
        return results

    @classmethod
    async def update_draft_invoice(
        cls,
        session: AsyncSession,
        invoice_id: uuid.UUID,
        request: UpdateDraftInvoiceRequest,
        current_user: User,
    ) -> InvoiceDetailResponse:
        """
        Updates metadata, tax, or line rate overrides on a draft invoice.
        Rejects modifications if the invoice is not in 'draft' status.
        Recalculates subtotals and total.
        """
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id)
            .execution_options(populate_existing=True)
        )
        inv = (await session.execute(stmt)).scalars().first()
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

        if inv.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only draft invoices can be modified. Invoice '{inv.invoice_number}' has status '{inv.status}'.",
            )

        # Update metadata
        if request.client_po_number is not None:
            inv.client_po_number = request.client_po_number
        if request.notes is not None:
            inv.notes = request.notes
        if request.remarks is not None:
            inv.remarks = request.remarks
        if request.due_date is not None:
            if inv.issue_date and request.due_date < inv.issue_date:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="due_date must be greater than or equal to issue_date.",
                )
            inv.due_date = request.due_date

        # Update rate overrides if supplied
        if request.rate_overrides is not None:
            if current_user.role not in ("director", "administrator"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only directors can override invoice billing rates.",
                )

            overrides_map = {ro.source_id: ro for ro in request.rate_overrides}
            for line in inv.lines:
                if line.line_type == "work" and line.source_daily_work_entry_id in overrides_map:
                    ro = overrides_map[line.source_daily_work_entry_id]
                    if ro.unit_rate != line.standard_rate:
                        if not ro.rate_override_reason or not ro.rate_override_reason.strip():
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"rate_override_reason is mandatory for rate override on work line {line.id}.",
                            )
                        line.unit_rate = ro.unit_rate
                        line.rate_override_reason = ro.rate_override_reason.strip()
                    else:
                        line.unit_rate = line.standard_rate
                        line.rate_override_reason = ro.rate_override_reason.strip() if ro.rate_override_reason else None

                    line.line_amount = (line.quantity * line.unit_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Update tax amount
        if request.tax_amount is not None:
            inv.tax_amount = Decimal(str(request.tax_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Recalculate totals
        subtotal_work = sum(
            l.line_amount for l in inv.lines if l.line_type == "work"
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal_material = sum(
            l.line_amount for l in inv.lines if l.line_type == "material"
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        inv.subtotal_work = subtotal_work
        inv.subtotal_material = subtotal_material
        inv.total_amount = inv.subtotal_work + inv.subtotal_material + inv.tax_amount

        await session.commit()
        return await cls._build_invoice_detail(session, inv)

    @classmethod
    async def issue_invoice(
        cls,
        session: AsyncSession,
        invoice_id: uuid.UUID,
        current_user_id: uuid.UUID,
        request: Optional[IssueInvoiceRequest] = None,
    ) -> InvoiceDetailResponse:
        """
        Transitions an invoice from 'draft' to 'issued'.
        Freezes financial fields permanently.
        """
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id)
            .execution_options(populate_existing=True)
        )
        inv = (await session.execute(stmt)).scalars().first()
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

        if inv.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot issue invoice with status '{inv.status}'. Only draft invoices can be issued.",
            )

        if not inv.lines or len(inv.lines) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot issue invoice with no line items.",
            )

        req_issue_date = request.issue_date if request else None
        req_due_date = request.due_date if request else None

        issue_d = req_issue_date or date.today()
        due_d = req_due_date or inv.due_date

        if due_d and due_d < issue_d:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="due_date must be greater than or equal to issue_date.",
            )

        inv.status = "issued"
        inv.issue_date = issue_d
        inv.due_date = due_d
        inv.issued_by = current_user_id
        inv.issued_at = datetime.now(timezone.utc)

        await session.commit()
        return await cls._build_invoice_detail(session, inv)

    @classmethod
    async def cancel_invoice(
        cls,
        session: AsyncSession,
        invoice_id: uuid.UUID,
        request: CancelInvoiceRequest,
        current_user_id: uuid.UUID,
    ) -> InvoiceDetailResponse:
        """
        Cancels an invoice according to the locked V1 state machine:
          - 'draft' invoices may be cancelled.
          - 'issued' invoices may be cancelled ONLY if paid_amount == 0.
          - 'paid' or 'partially_paid' invoices (or any invoice with paid_amount > 0) CANNOT be cancelled.
          - Already 'cancelled' invoices cannot be cancelled again.
        In the SAME database transaction:
          - Sets invoice.status = 'cancelled'
          - Sets is_active = FALSE on all associated invoice_line_items,
            releasing PostgreSQL partial unique indexes so source records become billable again.
        """
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id)
            .execution_options(populate_existing=True)
        )
        inv = (await session.execute(stmt)).scalars().first()
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

        if inv.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice is already cancelled.",
            )

        if inv.status in ("paid", "partially_paid") or inv.paid_amount > Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Paid or partially paid invoices cannot be cancelled. Invoice '{inv.invoice_number}' has status '{inv.status}' and paid_amount {inv.paid_amount}.",
            )

        if inv.status not in ("draft", "issued"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel invoice with status '{inv.status}'.",
            )

        # Atomic transition: update header and deactivate lines in SAME transaction
        old_status = inv.status
        inv.status = "cancelled"
        inv.cancelled_by = current_user_id
        inv.cancelled_at = datetime.now(timezone.utc)
        inv.cancellation_reason = request.cancellation_reason.strip()

        await session.execute(
            update(InvoiceLineItem)
            .where(InvoiceLineItem.invoice_id == inv.id)
            .values(is_active=False)
        )

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            entity_type="invoice",
            entity_id=inv.id,
            action="invoice_cancelled",
            changed_by=current_user_id,
            created_at=inv.cancelled_at,
            previous_values={
                "status": old_status,
                "invoice_number": inv.invoice_number,
                "total_amount": str(inv.total_amount),
                "paid_amount": str(inv.paid_amount),
            },
            new_values={
                "status": "cancelled",
                "cancellation_reason": inv.cancellation_reason,
            },
        )
        session.add(audit_entry)

        await session.commit()
        return await cls._build_invoice_detail(session, inv)

    @classmethod
    async def _build_invoice_detail(cls, session: AsyncSession, inv: Invoice) -> InvoiceDetailResponse:
        """Builds an enriched InvoiceDetailResponse with joined client, project, and site names."""
        client = await session.get(Client, inv.client_id)
        project = await session.get(Project, inv.project_id)
        site = await session.get(Site, inv.site_id)

        lines_resp = [InvoiceLineItemResponse.model_validate(line) for line in inv.lines]

        return InvoiceDetailResponse(
            id=inv.id,
            invoice_number=inv.invoice_number,
            idempotency_key=inv.idempotency_key,
            client_id=inv.client_id,
            client_name=client.name if client else None,
            project_id=inv.project_id,
            project_name=project.name if project else None,
            site_id=inv.site_id,
            site_name=site.name if site else None,
            period_start=inv.period_start,
            period_end=inv.period_end,
            status=inv.status,
            subtotal_work=inv.subtotal_work,
            subtotal_material=inv.subtotal_material,
            tax_amount=inv.tax_amount,
            total_amount=inv.total_amount,
            paid_amount=inv.paid_amount,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            client_po_number=inv.client_po_number,
            notes=inv.notes,
            remarks=inv.remarks,
            created_by=inv.created_by,
            issued_by=inv.issued_by,
            issued_at=inv.issued_at,
            cancelled_by=inv.cancelled_by,
            cancelled_at=inv.cancelled_at,
            cancellation_reason=inv.cancellation_reason,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            lines=lines_resp,
        )
