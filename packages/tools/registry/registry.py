"""Tool registry: registration, lookup and schema export."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from packages.tools.base import Tool, ToolMetadata


class FunctionTool(Tool):
    """A Tool backed by a plain (sync or async) handler function."""

    def __init__(self, metadata: ToolMetadata, handler: Callable[..., Any]):
        self._metadata = metadata
        self._handler = handler

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: dict, *, state: Any = None) -> dict:
        result = self._handler(arguments, state)
        if inspect.isawaitable(result):
            result = await result
        return result


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        name = tool.metadata.name
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = tool
        return tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    # Named `all`: a method called `list` shadows the builtin and breaks the
    # later `schemas() -> list[dict]` annotation under mypy.
    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict]:
        """OpenAI function-calling style schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "parameters": tool.metadata.input_schema,
                },
            }
            for tool in self._tools.values()
        ]
