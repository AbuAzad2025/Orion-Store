from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from subscription.subscription import (
    CustomerSubscription,
    DigitalAsset,
    DigitalDownload,
    LicenseKey,
    SubscriptionEvent,
    SubscriptionInvoice,
    SubscriptionPlan,
)

from core.exceptions import NotFoundError, ValidationError
from core.utils import utc_now
from orion.extensions import db


class SubscriptionService:
    def create_plan(
        self,
        *,
        tenant_id: int,
        name: str,
        code: str,
        billing_period_days: int,
        price: str | Decimal,
        trial_period_days: int = 0,
        currency: str = "ILS",
        max_orders_per_cycle: int | None = None,
        max_products: int | None = None,
    ) -> SubscriptionPlan:
        plan = SubscriptionPlan(
            tenant_id=tenant_id,
            name=name,
            code=code.strip().lower(),
            billing_period_days=billing_period_days,
            price=Decimal(str(price)),
            trial_period_days=trial_period_days,
            currency=currency,
            max_orders_per_cycle=max_orders_per_cycle,
            max_products=max_products,
        )
        db.session.add(plan)
        db.session.commit()
        return plan

    def list_plans(self, tenant_id: int) -> list[SubscriptionPlan]:
        return SubscriptionPlan.query.filter_by(
            tenant_id=tenant_id, is_active=True
        ).all()

    def subscribe(
        self,
        *,
        tenant_id: int,
        plan_id: int,
        customer_email: str,
        user_id: int | None = None,
    ) -> CustomerSubscription:
        plan = SubscriptionPlan.query.filter_by(id=plan_id, tenant_id=tenant_id).first()
        if not plan:
            raise NotFoundError("Subscription plan not found.")
        now = utc_now()
        period_end = now + timedelta(days=plan.billing_period_days)
        sub = CustomerSubscription(
            tenant_id=tenant_id,
            plan_id=plan_id,
            customer_email=customer_email.strip().lower(),
            user_id=user_id,
            status="active" if plan.trial_period_days == 0 else "trialing",
            current_period_start=now,
            current_period_end=period_end,
        )
        if plan.trial_period_days > 0:
            sub.trial_end = now + timedelta(days=plan.trial_period_days)
        db.session.add(sub)
        db.session.flush()
        db.session.add(
            SubscriptionEvent(
                subscription_id=sub.id,
                tenant_id=tenant_id,
                event_type="subscription.created",
                message=f"Subscribed to plan {plan.name}",
            )
        )
        db.session.commit()
        return sub

    def cancel(self, *, tenant_id: int, subscription_id: int) -> CustomerSubscription:
        sub = CustomerSubscription.query.filter_by(
            id=subscription_id, tenant_id=tenant_id
        ).first()
        if not sub:
            raise NotFoundError("Subscription not found.")
        sub.status = "cancelled"
        sub.cancelled_at = utc_now()
        db.session.add(
            SubscriptionEvent(
                subscription_id=sub.id,
                tenant_id=tenant_id,
                event_type="subscription.cancelled",
            )
        )
        db.session.commit()
        return sub

    def list_subscriptions(self, tenant_id: int) -> list[CustomerSubscription]:
        return CustomerSubscription.query.filter_by(tenant_id=tenant_id).all()

    def create_digital_asset(
        self,
        *,
        tenant_id: int,
        product_id: int,
        file_url: str,
        file_name: str,
        mime_type: str = "application/octet-stream",
        max_downloads: int = 5,
    ) -> DigitalAsset:
        asset = DigitalAsset(
            tenant_id=tenant_id,
            product_id=product_id,
            file_url=file_url,
            file_name=file_name,
            mime_type=mime_type,
            max_downloads=max_downloads,
        )
        db.session.add(asset)
        db.session.commit()
        return asset

    def create_download(
        self, *, tenant_id: int, asset_id: int, order_id: int
    ) -> DigitalDownload:
        asset = DigitalAsset.query.filter_by(id=asset_id, tenant_id=tenant_id).first()
        if not asset:
            raise NotFoundError("Digital asset not found.")
        download = DigitalDownload(
            tenant_id=tenant_id,
            asset_id=asset_id,
            order_id=order_id,
            download_token=uuid.uuid4().hex,
            expires_at=utc_now() + timedelta(days=30),
        )
        db.session.add(download)
        db.session.commit()
        return download

    def generate_license(
        self, *, tenant_id: int, order_item_id: int, product_id: int
    ) -> LicenseKey:
        key = f"LIC-{uuid.uuid4().hex[:16].upper()}"
        lic = LicenseKey(
            tenant_id=tenant_id,
            order_item_id=order_item_id,
            product_id=product_id,
            key=key,
        )
        db.session.add(lic)
        db.session.commit()
        return lic
