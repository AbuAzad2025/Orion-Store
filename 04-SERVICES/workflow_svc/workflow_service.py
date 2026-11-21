from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from workflow.workflow import WorkflowDefinition, WorkflowRun

from core.exceptions import NotFoundError
from order.order import Order, OrderEvent
from orion.extensions import db

# Keys (in priority order) used to derive a stable, tenant-scoped idempotency
# key from an event payload. The first integer value found wins.
_EVENT_ID_KEYS = ("event_id", "refund_id", "payment_id", "order_id", "id")


class WorkflowService:
    def create_definition(
        self,
        *,
        tenant_id: int,
        name: str,
        trigger_event: str,
        actions: list,
        conditions: dict | None = None,
    ) -> WorkflowDefinition:
        wf = WorkflowDefinition(
            tenant_id=tenant_id,
            name=name,
            trigger_event=trigger_event,
            conditions=conditions,
            actions=actions,
        )
        db.session.add(wf)
        db.session.commit()
        return wf

    def list_definitions(self, tenant_id: int) -> list[WorkflowDefinition]:
        return WorkflowDefinition.query.filter_by(tenant_id=tenant_id).all()

    def trigger(
        self,
        event_type: str | None = None,
        tenant_id: int | None = None,
        payload: dict | None = None,
        *,
        event: str | None = None,
        event_id: int | None = None,
    ) -> list[WorkflowRun]:
        """Execute every active workflow matching an event for a tenant.

        Both call shapes are supported::

            trigger("order.paid", tenant_id, {"order_id": 7})
            trigger(tenant_id=..., event="order.paid", event_id=7)  # legacy

        A run is created once per (tenant, definition, event key). Replaying the
        same event is a no-op, which gives the engine event-level idempotency.
        """
        event_type = event_type or event
        payload = dict(payload or {})
        if event_id is not None and "event_id" not in payload:
            payload["event_id"] = event_id
        if tenant_id is None:
            tenant_id = payload.get("tenant_id")
        if not event_type or not tenant_id:
            return []

        event_key = self._event_key(event_type, payload)
        definitions = WorkflowDefinition.query.filter_by(
            tenant_id=tenant_id, trigger_event=event_type, is_active=True
        ).all()

        runs: list[WorkflowRun] = []
        for definition in definitions:
            if not self._conditions_match(definition.conditions, payload):
                continue
            if self._find_run(tenant_id, definition.id, event_key) is not None:
                continue
            runs.append(self._execute(definition, tenant_id, payload, event_key))
        return runs

    def run_definition(
        self,
        definition: WorkflowDefinition,
        tenant_id: int,
        payload: dict | None = None,
        *,
        force: bool = False,
    ) -> WorkflowRun:
        """Run a single definition (used by the manual API endpoint).

        With ``force=False`` the normal event-level idempotency applies; a
        manual run defaults to ``force=True`` so an operator can re-run a
        workflow on demand.
        """
        payload = dict(payload or {})
        payload["tenant_id"] = tenant_id
        event_key = self._event_key(definition.trigger_event, payload)
        if not force:
            existing = self._find_run(tenant_id, definition.id, event_key)
            if existing is not None:
                return existing
        return self._execute(definition, tenant_id, payload, event_key)

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _find_run(
        tenant_id: int, definition_id: int, event_key: int
    ) -> WorkflowRun | None:
        return WorkflowRun.query.filter_by(
            tenant_id=tenant_id,
            definition_id=definition_id,
            trigger_event_id=event_key,
        ).first()

    @staticmethod
    def _event_key(event_type: str, payload: dict) -> int:
        """Derive a deterministic INTEGER idempotency key for an event."""
        for key in _EVENT_ID_KEYS:
            value = payload.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        canonical = json.dumps(
            {
                "event": event_type,
                **{
                    str(k): str(v)
                    for k, v in sorted(payload.items(), key=lambda i: str(i[0]))
                },
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).digest()
        # INTEGER is 32-bit signed in PostgreSQL — keep the hash positive.
        return int.from_bytes(digest[:4], "big") & 0x7FFF_FFFF

    @staticmethod
    def _conditions_match(conditions: dict | None, payload: dict) -> bool:
        """Tolerant equality conditions; unknown keys never block a run."""
        if not conditions or not isinstance(conditions, dict):
            return True
        for key, expected in conditions.items():
            if key not in payload:
                continue
            actual = payload[key]
            if isinstance(expected, (list, tuple, set, frozenset)):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    def _execute(
        self,
        definition: WorkflowDefinition,
        tenant_id: int,
        payload: dict,
        event_key: int,
    ) -> WorkflowRun:
        run = WorkflowRun(
            tenant_id=tenant_id,
            definition_id=definition.id,
            trigger_event_id=event_key,
            status="pending",
        )
        db.session.add(run)
        db.session.flush()
        try:
            for action in definition.actions or []:
                self._execute_action(action, definition, tenant_id, payload)
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
        except Exception as exc:  # a bad action must not abort the domain event
            run.status = "failed"
            run.error_message = str(exc)[:1000]
        db.session.commit()
        return run

    def _execute_action(
        self,
        action: object,
        definition: WorkflowDefinition,
        tenant_id: int,
        payload: dict,
    ) -> None:
        if not isinstance(action, dict):
            return
        action_type = str(action.get("type") or "").lower()
        if action_type == "send_email":
            self._send_email_action(action, tenant_id, payload)
        elif action_type == "tag_order":
            self._tag_order_action(action, definition, tenant_id, payload)
        # Unknown action types are ignored (forward compatible).

    @staticmethod
    def _send_email_action(action: dict, tenant_id: int, payload: dict) -> None:
        recipient = (
            action.get("recipient")
            or payload.get("recipient")
            or payload.get("customer_email")
        )
        order_id = payload.get("order_id")
        if (
            not recipient
            and isinstance(order_id, int)
            and not isinstance(order_id, bool)
        ):
            order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
            if order:
                recipient = order.customer_email
        if not recipient:
            return
        context = dict(payload)
        context.update(action.get("context") or {})
        from notification_svc.notification_service import NotificationService

        NotificationService().send_action_email(
            tenant_id=tenant_id,
            recipient=recipient,
            template=str(action.get("template") or "workflow_action"),
            context=context,
        )

    @staticmethod
    def _tag_order_action(
        action: dict, definition: WorkflowDefinition, tenant_id: int, payload: dict
    ) -> None:
        tag = action.get("tag") or action.get("value")
        order_id = payload.get("order_id")
        if not tag or not isinstance(order_id, int) or isinstance(order_id, bool):
            return
        order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
        if not order:
            return
        db.session.add(
            OrderEvent(
                tenant_id=tenant_id,
                order_id=order.id,
                event_type="workflow_tag",
                message=str(tag),
                metadata_json={
                    "tag": str(tag),
                    "workflow_definition_id": definition.id,
                },
            )
        )
