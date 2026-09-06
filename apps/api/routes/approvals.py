"""Human approval API."""

from fastapi import APIRouter, HTTPException, Request

from packages.policy.models import ApprovalStatus

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("")
async def list_approvals(request: Request, status: str | None = None) -> list[dict]:
    store = request.app.state.approval_store
    parsed = ApprovalStatus(status) if status else None
    approvals = await store.list(parsed)
    return [a.model_dump() for a in approvals]


@router.post("/{approval_id}/approve")
async def approve(approval_id: str, request: Request) -> dict:
    manager = request.app.state.approval_manager
    approval = await manager.decide(approval_id, approve=True)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval not found or already decided")
    return approval.model_dump()


@router.post("/{approval_id}/reject")
async def reject(approval_id: str, request: Request) -> dict:
    manager = request.app.state.approval_manager
    approval = await manager.decide(approval_id, approve=False)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval not found or already decided")
    return approval.model_dump()
