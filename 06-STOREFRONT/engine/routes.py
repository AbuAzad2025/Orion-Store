"""Storefront HTML pages — wave 5 #55-57."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, g

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from engine.theme_engine import ThemeEngine

_STOREFRONT_ROOT = Path(__file__).resolve().parents[1]

storefront_ui_bp = Blueprint(
    "storefront_ui",
    __name__,
    template_folder=str(_STOREFRONT_ROOT / "themes" / "default" / "templates"),
)
_engine = ThemeEngine()
_products = ProductService()
_categories = CategoryService()


def _tenant_or_404():
    if not g.tenant:
        return None
    return g.tenant


@storefront_ui_bp.get("/")
def store_index():
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    products = _products.list_published(tenant.id)
    return _engine.render(
        "index.html",
        tenant=tenant,
        products=products,
        page_title=tenant.name,
    )


@storefront_ui_bp.get("/product/<slug>")
def store_product(slug: str):
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    product = _products.get_by_slug(tenant.id, slug)
    return _engine.render(
        "product.html",
        tenant=tenant,
        product=product,
        page_title=product.name,
    )


@storefront_ui_bp.get("/category/<slug>")
def store_category(slug: str):
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    category = _categories.get_by_slug(tenant.id, slug)
    products = [
        p for p in _products.list_published(tenant.id) if p.category_id == category.id
    ]
    return _engine.render(
        "category.html",
        tenant=tenant,
        category=category,
        products=products,
        page_title=category.name,
    )


@storefront_ui_bp.get("/account")
def store_account():
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    return _engine.render("account.html", tenant=tenant, page_title="حسابي")


@storefront_ui_bp.get("/cart")
def store_cart():
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    return _engine.render("cart.html", tenant=tenant, page_title="السلة")


@storefront_ui_bp.get("/checkout")
def store_checkout():
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    return _engine.render("checkout.html", tenant=tenant, page_title="الدفع")
