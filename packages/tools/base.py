"""Tool abstraction: metadata, risk levels and the Tool base class."""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolMetadata(BaseModel):
    name: str
    description: str = ""
    schema: dict = Field(default_factory=lambda: {"type": "object", "properties": {}})
    risk_level: RiskLevel = RiskLevel.LOW
    timeout: int = 30  # seconds
    cost: float = 0.0  # estimated cost per call
    permission: list[str] = Field(default_factory=list)
    source: Literal["local", "mcp"] = "local"


class Tool(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Static metadata describing this tool."""
        ...

    @abstractmethod
    async def execute(self, arguments: dict, *, state: Any = None) -> dict:
        """Run the tool with the given arguments and return a result dict."""
        ...
