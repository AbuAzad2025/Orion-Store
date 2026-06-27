"""Shipping calculation and admin CRUD (wave 6 #58)."""

from __future__ import annotations

from decimal import Decimal

from shipping.shipping_method import ShippingMethod
from shipping.shipping_rate import ShippingRate
from shipping.shipping_zone import ShippingZone

from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


class ShippingService:
    def query_methods(self, tenant_id: int):
        return ShippingMethod.query.filter_by(
            tenant_id=tenant_id, is_active=True
        ).order_by(ShippingMethod.sort_order, ShippingMethod.id)

    def list_methods(self, tenant_id: int) -> list[ShippingMethod]:
        return self.query_methods(tenant_id).all()

    def get_by_code(self, tenant_id: int, code: str) -> ShippingMethod:
        method = ShippingMethod.query.filter_by(
            tenant_id=tenant_id, code=code, is_active=True
        ).first()
        if not method:
            raise NotFoundError(f"Shipping method '{code}' not found.")
        return method

    def create_method(
        self,
        *,
        tenant_id: int,
        name: str,
        code: str,
        base_cost: str | Decimal = "0",
        free_shipping_threshold: str | Decimal | None = None,
        is_default: bool = False,
        estimated_days_min: int | None = None,
        estimated_days_max: int | None = None,
    ) -> ShippingMethod:
        if is_default:
            ShippingMethod.query.filter_by(tenant_id=tenant_id, is_default=True).update(
                {"is_default": False}
            )
        method = ShippingMethod(
            tenant_id=tenant_id,
            name=name.strip(),
            code=code.strip().lower(),
            base_cost=Decimal(str(base_cost)),
            free_shipping_threshold=(
                Decimal(str(free_shipping_threshold))
                if free_shipping_threshold is not None
                else None
            ),
            is_default=is_default,
            estimated_days_min=estimated_days_min,
            estimated_days_max=estimated_days_max,
        )
        db.session.add(method)
        db.session.commit()
        return method

    def ensure_default_zone(self, tenant_id: int) -> ShippingZone:
        zone = ShippingZone.query.filter_by(
            tenant_id=tenant_id, is_default=True, is_active=True
        ).first()
        if zone:
            return zone
        zone = ShippingZone(
            tenant_id=tenant_id,
            name="Default",
            is_default=True,
            countries=[],
            regions=[],
        )
        db.session.add(zone)
        db.session.commit()
        return zone

    def resolve_zone(self, tenant_id: int, shipping_address: dict) -> ShippingZone:
        country = (shipping_address.get("country") or "").strip().upper()
        city = (shipping_address.get("city") or "").strip().lower()
        zones = ShippingZone.query.filter_by(tenant_id=tenant_id, is_active=True).all()
        for zone in zones:
            countries = [c.upper() for c in (zone.countries or [])]
            regions = [r.lower() for r in (zone.regions or [])]
            if country and country in countries:
                return zone
            if city and city in regions:
                return zone
        default = next((z for z in zones if z.is_default), None)
        if default:
            return default
        return self.ensure_default_zone(tenant_id)

    def calculate_cost(
        self,
        *,
        tenant_id: int,
        method_code: str,
        subtotal: Decimal,
        shipping_address: dict | None = None,
        free_shipping: bool = False,
    ) -> Decimal:
        if free_shipping:
            return Decimal("0")
        method = self.get_by_code(tenant_id, method_code)
        if method.min_order_value and subtotal < method.min_order_value:
            raise ValidationError("Order subtotal below shipping method minimum.")
        if method.max_order_value and subtotal > method.max_order_value:
            raise ValidationError("Order subtotal exceeds shipping method maximum.")
        if (
            method.free_shipping_threshold is not None
            and subtotal >= method.free_shipping_threshold
        ):
            return Decimal("0")

        zone = self.resolve_zone(tenant_id, shipping_address or {})
        rate = ShippingRate.query.filter_by(
            tenant_id=tenant_id,
            shipping_method_id=method.id,
            shipping_zone_id=zone.id,
        ).first()
        return rate.price if rate else method.base_cost

    def seed_flat_rate(
        self, tenant_id: int, *, code: str = "standard", cost: str = "10.00"
    ) -> ShippingMethod:
        existing = ShippingMethod.query.filter_by(
            tenant_id=tenant_id, code=code
        ).first()
        if existing:
            return existing
        method = self.create_method(
            tenant_id=tenant_id,
            name="Standard Shipping",
            code=code,
            base_cost=cost,
            free_shipping_threshold="100.00",
            is_default=True,
            estimated_days_min=2,
            estimated_days_max=5,
        )
        zone = self.ensure_default_zone(tenant_id)
        db.session.add(
            ShippingRate(
                tenant_id=tenant_id,
                shipping_method_id=method.id,
                shipping_zone_id=zone.id,
                price=Decimal(cost),
            )
        )
        db.session.commit()
        return method
