"""Shared SQLAlchemy enum types."""

from __future__ import annotations

import enum


class TenantStatus(str, enum.Enum):
    PENDING = "pending"
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class PlanType(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"
