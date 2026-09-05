"""Agent runtime execution loop."""

import time

from packages.llm.base import LLMResponse, ToolCall
from packages.runtime.checkpoint import CheckpointStore
from packages.runtime.harness import AgentHarness
from packages.runtime.state import AgentState, RunStatus

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
    ):
        self.harness = harness
        self.checkpoint = checkpoint
        self.max_steps = max_steps
        self.timeout = timeout
        self.max_retries = max_retries
        self._cancel_requests: set[str] = set()

    def cancel(self, run_id: str) -> None:
        self._cancel_requests.add(run_id)

    async def run(self, state: AgentState) -> AgentState:
        state.status = RunStatus.RUNNING
        self.harness.emit("run_started", {"run_id": state.run_id})
        deadline = time.monotonic() + self.timeout

        try:
            while True:
                if state.run_id in self._cancel_requests:
                    state.status = RunStatus.CANCELLED
                    break
                if state.step >= self.max_steps:
                    state.status = RunStatus.BUDGET_EXCEEDED
                    state.error = f"max_steps ({self.max_steps}) reached"
                    break
                if time.monotonic() > deadline:
                    state.status = RunStatus.FAILED
                    state.error = "timeout"
                    break

                context = await self.harness.build_context(state)
                tools = await self.harness.resolve_tools(state)
                response = await self.harness.llm.chat(context, tools)
                state.step += 1
                self._accumulate_usage(state, response)
                self.harness.emit(
                    "llm_response",
                    {
                        "run_id": state.run_id,
                        "step": state.step,
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
                    if decision != "allow":
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
        state.error = (
            f"tool {call.name} failed after {self.max_retries + 1} attempts: {last_error}"
        )
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

    async def _finish(self, state: AgentState) -> AgentState:
        self._cancel_requests.discard(state.run_id)
        await self._save_checkpoint(state)
        await self.harness.finalize(state)
        return state
