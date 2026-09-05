"""Minimal MCP JSON-RPC 2.0 client over stdio (asyncio subprocess)."""

import asyncio
import json
from typing import Any


class MCPError(Exception):
    """Raised when the server returns a JSON-RPC error or the transport fails."""


class MCPClient:
    def __init__(self, command: list[str], startup_timeout: float = 15.0):
        self.command = command
        self.startup_timeout = startup_timeout
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self.server_info: dict = {}

    async def start(self) -> "MCPClient":
        self._process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        result = await asyncio.wait_for(
            self._request("initialize", {"protocolVersion": "2024-11-05"}),
            timeout=self.startup_timeout,
        )
        self.server_info = result.get("serverInfo", {})
        await self._notify("notifications/initialized", {})
        return self

    async def _send(self, payload: dict) -> None:
        assert self._process is not None and self._process.stdin is not None
        self._process.stdin.write(json.dumps(payload, ensure_ascii=False).encode() + b"\n")
        await self._process.stdin.drain()

    async def _notify(self, method: str, params: dict) -> None:
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})

    async def _request(self, method: str, params: dict) -> Any:
        assert self._process is not None and self._process.stdout is not None
        self._request_id += 1
        await self._send(
            {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        )
        line = await self._process.stdout.readline()
        if not line:
            raise MCPError(f"server closed the stream while calling {method}")
        response = json.loads(line.decode())
        if "error" in response:
            error = response["error"]
            raise MCPError(f"{method} failed [{error.get('code')}]: {error.get('message')}")
        return response.get("result")

    async def list_tools(self) -> list[dict]:
        result = await self._request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        result = await self._request(
            "tools/call", {"name": name, "arguments": dict(arguments or {})}
        )
        if result.get("isError"):
            raise MCPError(f"tool '{name}' reported an error")
        content = result.get("content") or []
        if not content:
            return None
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    async def close(self) -> None:
        if self._process is None:
            return
        process, self._process = self._process, None
        if process.stdin is not None:
            process.stdin.close()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()
                await process.wait()
