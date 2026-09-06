"""Aggregated platform statistics for the overview page."""

from fastapi import APIRouter, Request

from agents.catalog import all_agents

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats(request: Request) -> dict:
    state = request.app.state
    runs = await state.run_service.store.aggregate()
    event_types = await state.event_store.type_counts()
    tool_counts = await state.event_store.tool_counts()
    approvals = await state.approval_store.counts()
    rules = state.policy_engine.list_rules()

    completed = int(runs["by_status"].get("completed", 0))
    total = int(runs["total"])
    denominator = total or 1

    def _count(*names: str) -> int:
        return sum(int(event_types.get(name, 0)) for name in names)

    return {
        "runs": {
            "total": total,
            "completed": completed,
            "success_rate": round(completed / denominator * 100, 1),
            "by_status": runs["by_status"],
            "timeline": runs["timeline"],
        },
        "usage": {
            "steps": int(runs["steps"]),
            "cost": float(runs["cost"]),
            "input_tokens": int(runs["input_tokens"]),
            "output_tokens": int(runs["output_tokens"]),
            "total_tokens": int(runs["total_tokens"]),
        },
        "activity": {
            "llm_requests": _count("llm.request"),
            "llm_responses": _count("llm.response"),
            "tool_calls": _count("tool.request"),
            "policy_checks": _count("policy.checked"),
            "approval_requests": _count("approval.requested"),
            "sandbox_starts": _count("sandbox.started"),
            "checkpoints": _count("checkpoint.created"),
        },
        "tools": tool_counts,
        "approvals": approvals,
        "policies": {
            "count": len(rules),
            "allow": sum(1 for rule in rules if rule.action.value == "allow"),
            "deny": sum(1 for rule in rules if rule.action.value == "deny"),
            "require_approval": sum(1 for rule in rules if rule.action.value == "require_approval"),
        },
        "agents": len(all_agents()),
    }
