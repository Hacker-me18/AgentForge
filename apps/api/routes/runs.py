"""Runs, events and traces API."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from packages.tracing.trace import TraceBuilder

router = APIRouter(prefix="/api", tags=["runs"])


class StartRunRequest(BaseModel):
    task: str
    agent_id: str = "default-agent"
    system_prompt: str | None = None
    max_steps: int = 16


@router.post("/runs", status_code=201)
async def start_run(body: StartRunRequest, request: Request) -> dict:
    service = request.app.state.run_service
    return await service.start(
        body.task,
        agent_id=body.agent_id,
        system_prompt=body.system_prompt,
        max_steps=body.max_steps,
    )


@router.get("/runs")
async def list_runs(request: Request, limit: int = 50) -> list[dict]:
    return await request.app.state.run_service.store.list(limit)


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request) -> dict:
    record = await request.app.state.run_service.store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    return record


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, request: Request) -> dict:
    if not request.app.state.run_service.cancel(run_id):
        raise HTTPException(status_code=404, detail="run not active")
    return {"run_id": run_id, "cancelled": True}


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request) -> list[dict]:
    events = await request.app.state.event_store.for_run(run_id)
    return [e.model_dump() for e in events]


@router.get("/runs/{run_id}/trace")
async def run_trace(run_id: str, request: Request) -> dict:
    events = await request.app.state.event_store.for_run(run_id)
    if not events:
        raise HTTPException(status_code=404, detail="run not found")
    return TraceBuilder().build(events)


@router.get("/events")
async def recent_events(request: Request, limit: int = 100) -> list[dict]:
    events = await request.app.state.event_store.list_recent(limit)
    return [e.model_dump() for e in events]
