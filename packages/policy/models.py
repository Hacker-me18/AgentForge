"""Policy domain models."""

import time
import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class PolicyAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyRule(BaseModel):
    """A rule mapping a tool (exact name or ``prefix.*``) to an action."""

    tool: str
    action: PolicyAction
    reason: str = ""


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Approval(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    run_id: str
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    risk_level: str = "high"
    reason: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = Field(default_factory=time.time)
    decided_at: float | None = None


# Default governance table (matches docs §36).
DEFAULT_RULES: list[PolicyRule] = [
    PolicyRule(tool="web.search", action=PolicyAction.ALLOW),
    PolicyRule(tool="document.read", action=PolicyAction.ALLOW),
    PolicyRule(tool="python.execute", action=PolicyAction.ALLOW),
    PolicyRule(tool="calculator", action=PolicyAction.ALLOW),
    PolicyRule(tool="mock.echo", action=PolicyAction.ALLOW),
    PolicyRule(tool="database.read", action=PolicyAction.ALLOW),
    PolicyRule(
        tool="database.write",
        action=PolicyAction.REQUIRE_APPROVAL,
        reason="Update records",
    ),
    PolicyRule(
        tool="shell.execute",
        action=PolicyAction.DENY,
        reason="Arbitrary shell execution is forbidden",
    ),
]
