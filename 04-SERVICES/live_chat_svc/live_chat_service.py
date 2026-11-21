from __future__ import annotations

import uuid

from live_chat.live_chat import LiveChatMessage, LiveChatSession

from core.exceptions import NotFoundError
from orion.extensions import db


class LiveChatService:
    def create_session(
        self, *, tenant_id: int, customer_email: str | None = None
    ) -> LiveChatSession:
        session = LiveChatSession(
            tenant_id=tenant_id,
            customer_email=customer_email,
            session_token=uuid.uuid4().hex,
        )
        db.session.add(session)
        db.session.commit()
        return session

    def send_message(
        self, *, tenant_id: int, session_id: int, sender_type: str, message: str
    ) -> LiveChatMessage:
        session = LiveChatSession.query.filter_by(
            id=session_id, tenant_id=tenant_id
        ).first()
        if not session:
            raise NotFoundError("Chat session not found.")
        msg = LiveChatMessage(
            tenant_id=tenant_id,
            session_id=session_id,
            sender_type=sender_type,
            message=message,
        )
        db.session.add(msg)
        if session.status == "pending":
            session.status = "active"
        db.session.commit()
        return msg

    def get_messages(self, *, tenant_id: int, session_id: int) -> list[LiveChatMessage]:
        session = LiveChatSession.query.filter_by(
            id=session_id, tenant_id=tenant_id
        ).first()
        if not session:
            raise NotFoundError("Chat session not found.")
        return (
            LiveChatMessage.query.filter_by(session_id=session_id)
            .order_by(LiveChatMessage.created_at.asc())
            .all()
        )
