"""AgentOS Studio API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.db import init_db
from apps.api.logging_config import configure_logging
from apps.api.routes import approvals, policies
from packages.policy.approval import ApprovalManager, ApprovalStore
from packages.policy.engine import PolicyEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    await init_db()
    app.state.policy_engine = PolicyEngine()
    db_path = settings.database_url.split("///")[-1]
    app.state.approval_store = ApprovalStore(db_path)
    app.state.approval_manager = ApprovalManager(app.state.approval_store)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(policies.router)
app.include_router(approvals.router)

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
