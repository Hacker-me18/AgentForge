"""Policy rules API."""

from fastapi import APIRouter, Request

from packages.policy.models import PolicyRule

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("")
async def list_policies(request: Request) -> list[dict]:
    engine = request.app.state.policy_engine
    return [rule.model_dump() for rule in engine.list_rules()]


@router.put("")
async def upsert_policy(rule: PolicyRule, request: Request) -> dict:
    engine = request.app.state.policy_engine
    engine.set_rule(rule)
    return rule.model_dump()
