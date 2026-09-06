"""Facade combining the Docker executor with optional sandbox event emission.

Events emitted (via an optional ``event_recorder`` callback):
    - ``sandbox.started``   : before the container starts.
    - ``sandbox.completed`` : run finished with status ``success``.
    - ``sandbox.failed``    : run finished with a non-success status or the
                              executor raised an error.
"""

from collections.abc import Callable

from packages.sandbox.executor import (
    STATUS_SUCCESS,
    DockerExecutor,
    SandboxResult,
)
from packages.sandbox.limits import ResourceLimits

EventRecorder = Callable[[str, dict], None]


class SandboxRunner:
    """High-level entry point used by the tools layer."""

    def __init__(
        self,
        executor: DockerExecutor | None = None,
        event_recorder: EventRecorder | None = None,
    ):
        self.executor = executor or DockerExecutor()
        self.event_recorder = event_recorder

    def _emit(self, event: str, payload: dict) -> None:
        if self.event_recorder is not None:
            self.event_recorder(event, payload)

    async def run(
        self,
        code: str,
        *,
        limits: ResourceLimits | None = None,
        artifacts_dir: str | None = None,
    ) -> SandboxResult:
        limits = limits or ResourceLimits()
        image = self.executor.image
        self._emit(
            "sandbox.started",
            {
                "image": image,
                "timeout_s": limits.timeout_s,
                "memory": limits.memory,
                "cpu": limits.cpu,
                "network": limits.network,
            },
        )
        try:
            result = await self.executor.execute(code, limits=limits, artifacts_dir=artifacts_dir)
        except Exception as exc:
            self._emit("sandbox.failed", {"image": image, "error": str(exc)})
            raise
        event = "sandbox.completed" if result.status == STATUS_SUCCESS else "sandbox.failed"
        self._emit(
            event,
            {
                "image": image,
                "status": result.status,
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "artifacts": list(result.artifacts),
            },
        )
        return result
