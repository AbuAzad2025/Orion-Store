"""Invoice and document templates (wave 4 #45-46)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from orion.extensions import db


class TenantDocumentTemplate(db.Model):
    __tablename__ = "tenant_document_templates"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    locale: Mapped[str] = mapped_column(String(5), default="ar")
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Invoice(db.Model):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    financial_event_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType,
        ForeignKey("financial_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    payment_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    platform_footer_applied: Mapped[bool] = mapped_column(Boolean, default=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "public_id": str(self.public_id),
            "invoice_number": self.invoice_number,
            "total_amount": str(self.total_amount),
            "commission_amount": str(self.commission_amount),
            "platform_footer_applied": self.platform_footer_applied,
        }
