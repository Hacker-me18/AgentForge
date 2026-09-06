"""Demo MCP server exposing four simulated tools over stdio."""

import sys
from pathlib import Path

# Allow running this file directly as a script (no package context needed).
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from packages.tools.mcp.server import MCPServer  # noqa: E402

_SEARCH_INDEX = [
    {
        "title": "PostgreSQL vs MySQL",
        "url": "https://mcp.example.com/pg-vs-mysql",
        "snippet": "PostgreSQL: advanced SQL & JSONB; MySQL: simple read-heavy speed.",
    },
    {
        "title": "MCP protocol basics",
        "url": "https://mcp.example.com/mcp-basics",
        "snippet": "JSON-RPC 2.0 over stdio or HTTP; tools/list and tools/call.",
    },
]

_FAKE_FS = {
    "/notes/readme.txt": "AgentOS Studio demo file served over MCP.",
    "/notes/todo.txt": "1. wire gateway 2. plug policy engine",
}

_FAKE_DB = {
    "select count(*) from users": [{"count": 3}],
    "select name from users": [{"name": "ada"}, {"name": "grace"}, {"name": "linus"}],
}


def _calculator(arguments: dict) -> dict:
    expression = str(arguments.get("expression", ""))
    if not all(ch in "0123456789+-*/%(). " for ch in expression):
        raise ValueError("only basic arithmetic is allowed")
    return {"expression": expression, "result": eval(expression, {"__builtins__": {}}, {})}


def build_server() -> MCPServer:
    server = MCPServer(name="demo-mcp-server")

    server.register_tool(
        "mcp.search",
        lambda arguments: {
            "query": arguments.get("query", ""),
            "results": [
                entry
                for entry in _SEARCH_INDEX
                if str(arguments.get("query", "")).lower()
                in f"{entry['title']} {entry['snippet']}".lower()
            ]
            or _SEARCH_INDEX,
        },
        description="Simulated web search over a tiny static index.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )
    server.register_tool(
        "mcp.filesystem.read",
        lambda arguments: {
            "path": arguments.get("path", ""),
            "content": _FAKE_FS.get(arguments.get("path", ""), ""),
        },
        description="Read a file from the simulated filesystem.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )
    server.register_tool(
        "mcp.database.query",
        lambda arguments: {
            "rows": _FAKE_DB.get(str(arguments.get("query", "")).strip().lower(), [])
        },
        description="Query the simulated database.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )
    server.register_tool(
        "mcp.calculator",
        _calculator,
        description="Evaluate a basic arithmetic expression.",
        input_schema={
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    )
    return server


if __name__ == "__main__":
    build_server().run()
