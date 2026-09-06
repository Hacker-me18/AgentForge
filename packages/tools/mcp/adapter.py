"""Adapter that exposes MCP tools as local Tool instances in the registry."""

from typing import Any

from packages.tools.base import RiskLevel, Tool, ToolMetadata
from packages.tools.mcp.client import MCPClient


class MCPToolAdapter(Tool):
    """Wrap a single MCP tool so the gateway stays MCP-agnostic."""

    def __init__(
        self,
        client: MCPClient,
        tool_info: dict,
        risk_level: RiskLevel = RiskLevel.LOW,
    ):
        self._client = client
        self._metadata = ToolMetadata(
            name=tool_info["name"],
            description=tool_info.get("description", ""),
            input_schema=tool_info.get("inputSchema") or {"type": "object", "properties": {}},
            risk_level=risk_level,
            source="mcp",
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: dict, *, state: Any = None) -> dict:
        result = await self._client.call_tool(self._metadata.name, arguments)
        if isinstance(result, dict):
            return result
        return {"result": result}
