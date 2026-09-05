"""Minimal MCP (JSON-RPC over stdio) support."""

from packages.tools.mcp.adapter import MCPToolAdapter
from packages.tools.mcp.client import MCPClient, MCPError
from packages.tools.mcp.server import MCPServer

__all__ = ["MCPClient", "MCPError", "MCPServer", "MCPToolAdapter"]
