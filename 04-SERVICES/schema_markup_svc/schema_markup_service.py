from __future__ import annotations

from core.exceptions import NotFoundError
from orion.extensions import db
from schema_markup.schema_markup import ProductSchemaMarkup


class SchemaMarkupService:
    def set_markup(
        self,
        *,
        tenant_id: int,
        product_id: int,
        schema_type: str = "Product",
        json_ld: dict | None = None,
    ) -> ProductSchemaMarkup:
        existing = ProductSchemaMarkup.query.filter_by(
            tenant_id=tenant_id, product_id=product_id
        ).first()
        if existing:
            existing.schema_type = schema_type
            existing.json_ld = json_ld or {}
        else:
            existing = ProductSchemaMarkup(
                tenant_id=tenant_id,
                product_id=product_id,
                schema_type=schema_type,
                json_ld=json_ld or {},
            )
            db.session.add(existing)
        db.session.commit()
        return existing

    def get_markup(
        self, *, tenant_id: int, product_id: int
    ) -> ProductSchemaMarkup | None:
        return ProductSchemaMarkup.query.filter_by(
            tenant_id=tenant_id, product_id=product_id
        ).first()
