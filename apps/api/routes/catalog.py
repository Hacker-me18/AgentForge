"""Catalog endpoints: the tool registry and the demo agent catalog."""

from fastapi import APIRouter, Request

from agents.catalog import all_agents

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/tools")
async def list_tools(request: Request) -> list[dict]:
    """Every registered tool with its metadata and effective policy action."""
    registry = request.app.state.tool_registry
    policy = request.app.state.policy_engine
    items = []
    for tool in registry.all():
        meta = tool.metadata
        items.append(
            {
                "name": meta.name,
                "description": meta.description,
                "input_schema": meta.input_schema,
                "risk_level": meta.risk_level.value,
                "timeout": meta.timeout,
                "cost": meta.cost,
                "permission": list(meta.permission),
                "source": meta.source,
                "policy": policy.check(meta.name).value,
            }
        )
    return items


@router.get("/agents")
async def list_agents() -> list[dict]:
    """The built-in demo agent catalog."""
    return [agent.to_dict() for agent in all_agents()]
