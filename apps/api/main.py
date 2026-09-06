"""AgentOS Studio API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.db import init_db
from apps.api.logging_config import configure_logging
from apps.api.routes import approvals, catalog, policies, runs, sandbox, stats
from apps.api.routes import eval as eval_routes
from apps.api.run_service import RunService
from packages.llm.factory import LLMFactory
from packages.policy.approval import ApprovalManager, ApprovalStore
from packages.policy.engine import PolicyEngine
from packages.tools.registry.builtin import create_default_registry
from packages.tracing.bus import EventBus
from packages.tracing.store import EventStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    await init_db()
    db_path = settings.database_url.split("///")[-1]
    app.state.policy_engine = PolicyEngine()
    app.state.approval_store = ApprovalStore(db_path)
    app.state.approval_manager = ApprovalManager(app.state.approval_store)
    app.state.event_store = EventStore(db_path)
    app.state.event_bus = EventBus(app.state.event_store)
    app.state.tool_registry = create_default_registry()
    app.state.run_service = RunService(
        db_path=db_path,
        llm=LLMFactory.create(settings),
        policy_engine=app.state.policy_engine,
        approval_manager=app.state.approval_manager,
        event_bus=app.state.event_bus,
    )
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(policies.router)
app.include_router(approvals.router)
app.include_router(runs.router)
app.include_router(catalog.router)
app.include_router(stats.router)
app.include_router(sandbox.router)
app.include_router(eval_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
