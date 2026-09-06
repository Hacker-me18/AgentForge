"""Minimal MCP-style JSON-RPC 2.0 server over stdio (no official SDK).

Line-delimited JSON-RPC: one request per line on stdin, one response per
line on stdout. Supported methods: ``initialize``, ``tools/list``,
``tools/call`` (plus the ``notifications/initialized`` notification).
"""

import asyncio
import inspect
import json
import sys
from collections.abc import Callable
from typing import Any

PROTOCOL_VERSION = "2024-11-05"

_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603


class MCPServer:
    def __init__(self, name: str = "mcp-server", version: str = "0.1.0"):
        self.name = name
        self.version = version
        self._tools: dict[str, dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        handler: Callable[[dict], Any],
        description: str = "",
        input_schema: dict | None = None,
    ) -> None:
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema or {"type": "object", "properties": {}},
            "handler": handler,
        }

    async def dispatch(self, request: dict) -> dict | None:
        """Handle one JSON-RPC request; returns None for notifications."""
        method = request.get("method", "")
        request_id = request.get("id")
        if request_id is None:  # notification, e.g. notifications/initialized
            return None

        # JSON-RPC results are shape-variant across methods; keep the value Any.
        result: dict[str, Any]
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.name, "version": self.version},
                }
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": spec["name"],
                            "description": spec["description"],
                            "inputSchema": spec["inputSchema"],
                        }
                        for spec in self._tools.values()
                    ]
                }
            elif method == "tools/call":
                result = await self._call_tool(request.get("params") or {})
            else:
                return self._error(request_id, _METHOD_NOT_FOUND, f"unknown method: {method}")
        except Exception as exc:  # noqa: BLE001 - serialize any failure as JSON-RPC error
            return self._error(request_id, _INTERNAL_ERROR, str(exc))
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    async def _call_tool(self, params: dict) -> dict:
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        spec = self._tools.get(name)
        if spec is None:
            raise ValueError(f"unknown tool: {name}")
        output = spec["handler"](arguments)
        if inspect.isawaitable(output):
            output = await output
        return {
            "content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False)}],
            "isError": False,
        }

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    async def serve(self, stdin=None, stdout=None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, stdin.readline)
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            response: dict[str, Any] | None
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                response = self._error(None, _INVALID_PARAMS, f"invalid JSON: {exc}")
            else:
                response = await self.dispatch(request)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                stdout.flush()

    def run(self) -> None:
        asyncio.run(self.serve())


def main(server: MCPServer | None = None) -> None:
    (server or MCPServer()).run()


if __name__ == "__main__":
    main()
