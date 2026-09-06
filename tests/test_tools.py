"""Tests for Phase C: tool registry, tool gateway and MCP integration."""

import sys
from pathlib import Path

import pytest

from packages.tools.base import RiskLevel
from packages.tools.gateway.errors import (
    PolicyDeniedError,
    ToolExecutionError,
    ToolNotFoundError,
)
from packages.tools.gateway.gateway import ToolGateway
from packages.tools.mcp.adapter import MCPToolAdapter
from packages.tools.mcp.client import MCPClient
from packages.tools.registry.builtin import create_default_registry

BUILTIN_TOOLS = {
    "mock.echo": RiskLevel.LOW,
    "calculator": RiskLevel.LOW,
    "web.search": RiskLevel.LOW,
    "document.read": RiskLevel.LOW,
    "database.read": RiskLevel.MEDIUM,
    "database.write": RiskLevel.HIGH,
    "shell.execute": RiskLevel.CRITICAL,
    "python.execute": RiskLevel.MEDIUM,
}

DEMO_SERVER = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "tools"
    / "mcp"
    / "servers"
    / "demo_server.py"
)


# ---------------------------------------------------------------------------
# a) registry
# ---------------------------------------------------------------------------


def test_registry_register_get_list() -> None:
    registry = create_default_registry()
    assert {tool.metadata.name for tool in registry.all()} == set(BUILTIN_TOOLS)
    assert registry.get("calculator") is not None
    assert registry.get("no-such-tool") is None


def test_registry_schemas_openai_format() -> None:
    registry = create_default_registry()
    schemas = registry.schemas()
    assert len(schemas) == len(BUILTIN_TOOLS)
    by_name = {s["function"]["name"]: s for s in schemas}
    for name, risk in BUILTIN_TOOLS.items():
        assert name in by_name
        entry = by_name[name]
        assert entry["type"] == "function"
        function = entry["function"]
        assert function["description"]
        assert function["parameters"]["type"] == "object"

        metadata = registry.get(name).metadata
        assert metadata.risk_level == risk
        assert metadata.timeout > 0
        assert metadata.cost >= 0
        assert isinstance(metadata.permission, list)
        assert metadata.source == "local"


def test_registry_rejects_duplicate_registration() -> None:
    registry = create_default_registry()
    with pytest.raises(ValueError, match="already registered"):
        registry.register(registry.get("calculator"))


# ---------------------------------------------------------------------------
# b) gateway happy path + event sequence
# ---------------------------------------------------------------------------


async def test_gateway_calculator_with_events() -> None:
    events: list[tuple[str, dict]] = []
    gateway = ToolGateway(
        create_default_registry(), event_recorder=lambda e, p: events.append((e, p))
    )

    result = await gateway.call("calculator", {"expression": "1+2*3"})

    assert result["status"] == "success"
    assert result["output"]["result"] == 7
    assert result["duration_ms"] >= 0

    sequence = [name for name, _ in events]
    for expected in ("tool.request", "policy.checked", "tool.started", "tool.completed"):
        assert expected in sequence
    assert sequence.index("tool.request") < sequence.index("policy.checked")
    assert sequence.index("policy.checked") < sequence.index("tool.started")
    assert sequence.index("tool.started") < sequence.index("tool.completed")


async def test_gateway_mock_echo() -> None:
    gateway = ToolGateway(create_default_registry())
    result = await gateway.call("mock.echo", {"text": "hi"})
    assert result["output"] == {"echo": {"text": "hi"}}


# ---------------------------------------------------------------------------
# c) unknown tool + denied policy
# ---------------------------------------------------------------------------


async def test_gateway_unknown_tool_raises_not_found() -> None:
    gateway = ToolGateway(create_default_registry())
    with pytest.raises(ToolNotFoundError):
        await gateway.call("no.such.tool", {})


async def test_gateway_policy_deny_raises() -> None:
    gateway = ToolGateway(create_default_registry(), policy_checker=lambda name, meta, args: "deny")
    with pytest.raises(PolicyDeniedError):
        await gateway.call("calculator", {"expression": "1+1"})


async def test_gateway_execution_error_wraps_tool_failure() -> None:
    gateway = ToolGateway(create_default_registry())
    with pytest.raises(ToolExecutionError, match="calculator"):
        await gateway.call("calculator", {"expression": "1/0"})


# ---------------------------------------------------------------------------
# d) calculator rejects dangerous input
# ---------------------------------------------------------------------------


async def test_calculator_rejects_dangerous_input() -> None:
    gateway = ToolGateway(create_default_registry())
    for payload in ('__import__("os")', "open('/etc/passwd')", "1 if True else 2", "x + 1"):
        with pytest.raises(ToolExecutionError):
            await gateway.call("calculator", {"expression": payload})


# ---------------------------------------------------------------------------
# e) web.search static knowledge base
# ---------------------------------------------------------------------------


async def test_web_search_returns_postgresql_mysql_results() -> None:
    gateway = ToolGateway(create_default_registry())
    result = await gateway.call("web.search", {"query": "PostgreSQL vs MySQL"})
    results = result["output"]["results"]
    assert results
    assert all({"title", "url", "snippet"} <= set(entry) for entry in results)
    haystack = " ".join(f"{e['title']} {e['snippet']}".lower() for e in results)
    assert "postgresql" in haystack
    assert "mysql" in haystack


# ---------------------------------------------------------------------------
# f) MCP end-to-end
# ---------------------------------------------------------------------------


async def test_mcp_end_to_end_via_gateway() -> None:
    client = await MCPClient([sys.executable, str(DEMO_SERVER)]).start()
    try:
        tools = await client.list_tools()
        assert len(tools) == 4
        assert {t["name"] for t in tools} == {
            "mcp.search",
            "mcp.filesystem.read",
            "mcp.database.query",
            "mcp.calculator",
        }

        direct = await client.call_tool("mcp.calculator", {"expression": "2*21"})
        assert direct["result"] == 42

        registry = create_default_registry()
        for tool_info in tools:
            registry.register(MCPToolAdapter(client, tool_info))
        assert registry.get("mcp.calculator").metadata.source == "mcp"

        gateway = ToolGateway(registry)
        result = await gateway.call("mcp.calculator", {"expression": "6*7"})
        assert result["status"] == "success"
        assert result["output"]["result"] == 42
    finally:
        await client.close()
