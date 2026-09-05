"""LLM provider abstraction."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict = Field(default_factory=dict)


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Send chat messages and return a normalized response."""
        ...
