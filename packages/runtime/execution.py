"""Agent runtime execution loop."""

import time
from collections.abc import Awaitable, Callable

from packages.llm.base import LLMResponse, ToolCall
from packages.policy.budget import Budget
from packages.runtime.checkpoint import CheckpointStore
from packages.runtime.harness import AgentHarness
from packages.runtime.state import AgentState, RunStatus

# Asks a human (or test stub) whether a tool call may proceed.
ApprovalHandler = Callable[[str, str, dict], Awaitable[bool]]

# USD per 1M tokens: (input, output)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "mock-model": (0.0, 0.0),
    "deepseek-chat": (0.27, 1.10),
}
DEFAULT_PRICING = (0.0, 0.0)


class AgentRuntime:
    def __init__(
        self,
        harness: AgentHarness,
        checkpoint: CheckpointStore | None = None,
        max_steps: int = 16,
        timeout: float = 120.0,
        max_retries: int = 2,
        approval_handler: ApprovalHandler | None = None,
        budget: Budget | None = None,
    ):
        self.harness = harness
        self.checkpoint = checkpoint
        self.max_steps = max_steps
        self.timeout = timeout
        self.max_retries = max_retries
        self.approval_handler = approval_handler
        self.budget = budget
        self._cancel_requests: set[str] = set()

    def cancel(self, run_id: str) -> None:
        self._cancel_requests.add(run_id)

    async def run(self, state: AgentState) -> AgentState:
        state.status = RunStatus.RUNNING
        self.harness.emit("run.started", {"run_id": state.run_id, "task": state.task})
        started_at = time.monotonic()
        deadline = started_at + self.timeout
        max_steps = (
            self.budget.max_steps
            if self.budget is not None and self.budget.max_steps is not None
            else self.max_steps
        )

        try:
            while True:
                if state.run_id in self._cancel_requests:
                    state.status = RunStatus.CANCELLED
                    break
                if state.step >= max_steps:
                    state.status = RunStatus.BUDGET_EXCEEDED
                    state.error = f"step budget exceeded ({state.step}/{max_steps})"
                    break
                if time.monotonic() > deadline:
                    state.status = RunStatus.FAILED
                    state.error = "timeout"
                    break
                budget_reason = self._check_budget(state, started_at)
                if budget_reason is not None:
                    state.status = RunStatus.BUDGET_EXCEEDED
                    state.error = budget_reason
                    break

                context = await self.harness.build_context(state)
                tools = await self.harness.resolve_tools(state)
                self.harness.emit(
                    "llm.request",
                    {"run_id": state.run_id, "step": state.step + 1, "messages": len(context)},
                )
                response = await self.harness.llm.chat(context, tools)
                state.step += 1
                self._accumulate_usage(state, response)
                self.harness.emit(
                    "llm.response",
                    {
                        "run_id": state.run_id,
                        "step": state.step,
                        "model": response.model,
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "finish_reason": response.finish_reason,
                        "tool_calls": len(response.tool_calls),
                    },
                )

                if not response.tool_calls:
                    state.status = RunStatus.COMPLETED
                    state.context["final_answer"] = response.content
                    break

                state.messages.append(
                    {
                        "role": "assistant",
                        "content": response.content,
                        "tool_calls": [tc.model_dump() for tc in response.tool_calls],
                    }
                )
                for call in response.tool_calls:
                    decision = await self.harness.check_policy(
                        {"tool": call.name, "arguments": call.arguments}
                    )
                    if decision == "require_approval":
                        approved = await self._request_approval(state, call)
                        if not approved:
                            await self.harness.observe(
                                state,
                                {
                                    "tool_call_id": call.id,
                                    "tool": call.name,
                                    "status": "blocked",
                                    "error": "approval rejected",
                                },
                            )
                            continue
                    elif decision != "allow":
                        await self.harness.observe(
                            state,
                            {
                                "tool_call_id": call.id,
                                "tool": call.name,
                                "status": "blocked",
                                "error": f"policy decision: {decision}",
                            },
                        )
                        continue
                    succeeded = await self._execute_with_retry(state, call)
                    if not succeeded:
                        return await self._finish(state)
                    await self._save_checkpoint(state)
        except Exception as exc:
            state.status = RunStatus.FAILED
            state.error = str(exc)

        return await self._finish(state)

    def _check_budget(self, state: AgentState, started_at: float) -> str | None:
        if self.budget is None:
            return None
        tokens = state.token_usage.get("input", 0) + state.token_usage.get("output", 0)
        return self.budget.exceeded(
            step=state.step,
            tokens=tokens,
            cost=state.cost,
            elapsed_s=time.monotonic() - started_at,
        )

    async def _request_approval(self, state: AgentState, call: ToolCall) -> bool:
        """Pause the run and wait for a human approval decision."""
        state.status = RunStatus.WAITING_APPROVAL
        self.harness.emit(
            "approval.requested",
            {"run_id": state.run_id, "tool": call.name, "arguments": call.arguments},
        )
        try:
            if self.approval_handler is None:
                self.harness.emit(
                    "approval.decided",
                    {"run_id": state.run_id, "tool": call.name, "approved": False},
                )
                return False
            approved = await self.approval_handler(call.id, call.name, call.arguments)
            self.harness.emit(
                "approval.decided",
                {"run_id": state.run_id, "tool": call.name, "approved": approved},
            )
            return approved
        finally:
            if state.status == RunStatus.WAITING_APPROVAL:
                state.status = RunStatus.RUNNING

    async def _execute_with_retry(self, state: AgentState, call: ToolCall) -> bool:
        last_error = ""
        for attempt in range(1, self.max_retries + 2):
            try:
                result = await self.harness.execute(state, call)
            except Exception as exc:
                last_error = str(exc)
                await self.harness.observe(
                    state,
                    {
                        "tool_call_id": call.id,
                        "tool": call.name,
                        "status": "failed",
                        "error": last_error,
                        "attempt": attempt,
                    },
                )
                continue
            await self.harness.observe(
                state,
                {
                    "tool_call_id": call.id,
                    "tool": call.name,
                    "status": "success",
                    "result": result.get("result"),
                    "attempt": attempt,
                },
            )
            return True
        state.status = RunStatus.FAILED
        state.error = f"tool {call.name} failed after {self.max_retries + 1} attempts: {last_error}"
        return False

    def _accumulate_usage(self, state: AgentState, response: LLMResponse) -> None:
        state.token_usage["input"] = state.token_usage.get("input", 0) + response.input_tokens
        state.token_usage["output"] = state.token_usage.get("output", 0) + response.output_tokens
        price_in, price_out = MODEL_PRICING.get(response.model, DEFAULT_PRICING)
        state.cost += (
            response.input_tokens * price_in + response.output_tokens * price_out
        ) / 1_000_000

    async def _save_checkpoint(self, state: AgentState) -> None:
        if self.checkpoint is not None:
            await self.checkpoint.save(state)
            self.harness.emit("checkpoint.created", {"run_id": state.run_id, "step": state.step})

    async def _finish(self, state: AgentState) -> AgentState:
        self._cancel_requests.discard(state.run_id)
        await self._save_checkpoint(state)
        summary = await self.harness.finalize(state)
        event = "run.completed" if state.status == RunStatus.COMPLETED else "run.failed"
        self.harness.emit(event, summary)
        return state
