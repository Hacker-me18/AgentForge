"""Interactive sandbox endpoint for the Studio UI.

Runs arbitrary Python inside the locked-down Docker container
(``agentos-sandbox``, ``--network none`` + memory/CPU limits). This mirrors
what the ``python.execute`` tool does under the hood and is intended for the
local Studio demo — add authentication/queueing before exposing publicly.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.sandbox.executor import DockerUnavailableError, SandboxResult
from packages.sandbox.limits import ResourceLimits
from packages.sandbox.runner import SandboxRunner

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


class SandboxRunRequest(BaseModel):
    code: str
    timeout_s: float = 15


@router.post("/run")
async def run_code(body: SandboxRunRequest) -> dict:
    if not body.code.strip():
        raise HTTPException(status_code=400, detail="code must not be empty")
    timeout = min(max(body.timeout_s, 1), 30)
    try:
        result: SandboxResult = await SandboxRunner().run(
            body.code, limits=ResourceLimits(timeout_s=timeout)
        )
    except DockerUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"sandbox unavailable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - surface container failures as JSON
        raise HTTPException(status_code=500, detail=f"sandbox run failed: {exc}") from exc
    return {
        "status": result.status,
        "exit_code": result.exit_code,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-2000:],
        "duration_ms": round(result.duration_ms, 1),
        "artifacts": result.artifacts,
    }
