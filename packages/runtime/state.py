"""Agent run state."""

from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXCEEDED = "budget_exceeded"


class AgentState(BaseModel):
    run_id: str
    agent_id: str = ""
    task: str = ""
    messages: list[dict] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    tool_results: list[dict] = Field(default_factory=list)
    observations: list[dict] = Field(default_factory=list)
    memory: dict = Field(default_factory=dict)
    step: int = 0
    token_usage: dict = Field(default_factory=lambda: {"input": 0, "output": 0})
    cost: float = 0.0
    status: RunStatus = RunStatus.PENDING
    error: str | None = None
