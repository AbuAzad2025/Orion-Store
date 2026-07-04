from __future__ import annotations

from workflow.workflow import WorkflowDefinition, WorkflowRun

from core.exceptions import NotFoundError
from orion.extensions import db


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
        self, *, tenant_id: int, event: str, event_id: int
    ) -> list[WorkflowRun]:
        definitions = WorkflowDefinition.query.filter_by(
            tenant_id=tenant_id, trigger_event=event, is_active=True
        ).all()
        runs = []
        for wf in definitions:
            run = WorkflowRun(
                tenant_id=tenant_id, definition_id=wf.id, trigger_event_id=event_id
            )
            db.session.add(run)
            runs.append(run)
        db.session.commit()
        return runs
