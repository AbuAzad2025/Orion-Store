from __future__ import annotations

from core.exceptions import NotFoundError
from metafield.metafield import Metafield, MetafieldDefinition
from orion.extensions import db


class MetafieldService:
    def define(
        self,
        *,
        tenant_id: int,
        owner_type: str,
        key: str,
        label: str,
        field_type: str = "string",
        is_required: bool = False,
    ) -> MetafieldDefinition:
        mf = MetafieldDefinition(
            tenant_id=tenant_id,
            owner_type=owner_type,
            key=key,
            label=label,
            field_type=field_type,
            is_required=is_required,
        )
        db.session.add(mf)
        db.session.commit()
        return mf

    def set_value(
        self,
        *,
        tenant_id: int,
        definition_id: int,
        owner_id: int,
        value: str | None = None,
        json_value: dict | None = None,
    ) -> Metafield:
        definition = MetafieldDefinition.query.filter_by(
            id=definition_id, tenant_id=tenant_id
        ).first()
        if not definition:
            raise NotFoundError("Metafield definition not found.")
        existing = Metafield.query.filter_by(
            definition_id=definition_id, owner_id=owner_id
        ).first()
        if existing:
            existing.value = value
            existing.json_value = json_value
        else:
            existing = Metafield(
                tenant_id=tenant_id,
                definition_id=definition_id,
                owner_id=owner_id,
                value=value,
                json_value=json_value,
            )
            db.session.add(existing)
        db.session.commit()
        return existing

    def get_for_owner(
        self, *, tenant_id: int, owner_type: str, owner_id: int
    ) -> list[dict]:
        definitions = MetafieldDefinition.query.filter_by(
            tenant_id=tenant_id, owner_type=owner_type
        ).all()
        result = []
        for defn in definitions:
            mf = Metafield.query.filter_by(
                definition_id=defn.id, owner_id=owner_id
            ).first()
            result.append(
                {
                    **defn.to_dict(),
                    "value": mf.value if mf else defn.default_value,
                    "json_value": mf.json_value if mf else None,
                }
            )
        return result
