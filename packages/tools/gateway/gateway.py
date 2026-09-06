"""Tool gateway: policy-checked, observable, timeout-bounded tool execution.

Implements the ``ToolGateway`` protocol expected by
``packages.runtime.harness.AgentHarness``. Execution errors are re-raised as
``ToolExecutionError`` so the runtime's retry logic can catch and retry them.
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any

from packages.tools.base import ToolMetadata
from packages.tools.gateway.errors import (
    PolicyDeniedError,
    ToolExecutionError,
    ToolNotFoundError,
)
from packages.tools.registry.registry import ToolRegistry

EventRecorder = Callable[[str, dict], None]
PolicyChecker = Callable[[str, ToolMetadata, dict], str]


class ToolGateway:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_checker: PolicyChecker | None = None,
        event_recorder: EventRecorder | None = None,
    ):
        self.registry = registry
        self.policy_checker = policy_checker
        self.event_recorder = event_recorder

    def emit(self, event: str, payload: dict) -> None:
        if self.event_recorder is not None:
            self.event_recorder(event, payload)

    def schemas(self) -> list[dict]:
        return self.registry.schemas()

    def check_policy(self, name: str, metadata: ToolMetadata, arguments: dict) -> str:
        # Phase E plugs in the real policy engine; default is allow.
        if self.policy_checker is None:
            return "allow"
        return self.policy_checker(name, metadata, arguments)

    async def call(self, name: str, arguments: dict, *, state: Any = None) -> dict:
        arguments = dict(arguments or {})
        self.emit("tool.request", {"tool": name, "arguments": arguments})

        tool = self.registry.get(name)
        if tool is None:
            self.emit("tool.failed", {"tool": name, "error": f"tool not found: {name}"})
            raise ToolNotFoundError(f"tool not found: {name}")

        metadata = tool.metadata
        decision = self.check_policy(name, metadata, arguments)
        self.emit(
            "policy.checked",
            {"tool": name, "decision": decision, "risk_level": metadata.risk_level.value},
        )
        if decision != "allow":
            self.emit("tool.failed", {"tool": name, "error": f"policy decision: {decision}"})
            raise PolicyDeniedError(f"tool '{name}' denied by policy: {decision}")

        self.emit("tool.started", {"tool": name})
        started = time.perf_counter()
        try:
            output = await asyncio.wait_for(
                tool.execute(arguments, state=state), timeout=metadata.timeout
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            if isinstance(exc, TimeoutError):
                reason = f"tool '{name}' timed out after {metadata.timeout}s"
            else:
                reason = f"tool '{name}' failed: {exc}"
            self.emit("tool.failed", {"tool": name, "error": reason, "duration_ms": duration_ms})
            raise ToolExecutionError(reason) from exc

        duration_ms = (time.perf_counter() - started) * 1000
        self.emit("tool.completed", {"tool": name, "duration_ms": duration_ms})
        return {"status": "success", "output": output, "duration_ms": duration_ms}
