"""Agent harness: orchestrates context, tools, policy and observation.

The harness contains no business logic; it only wires the LLM provider,
tool gateway, context engine and event recorder together.
"""

import json
import uuid
from collections.abc import Callable
from typing import Any, Protocol

from packages.llm.base import LLMProvider, ToolCall
from packages.policy.engine import PolicyEngine
from packages.runtime.state import AgentState, RunStatus

EventRecorder = Callable[[str, dict], None]


class ToolGateway(Protocol):
    def schemas(self) -> list[dict]: ...

    async def call(self, name: str, arguments: dict) -> Any: ...


class AgentHarness:
    def __init__(
        self,
        llm: LLMProvider,
        tool_gateway: ToolGateway | None = None,
        context_engine: Any | None = None,
        event_recorder: EventRecorder | None = None,
        policy_engine: PolicyEngine | None = None,
    ):
        self.llm = llm
        self.tool_gateway = tool_gateway
        self.context_engine = context_engine
        self.event_recorder = event_recorder
        self.policy_engine = policy_engine

    def emit(self, event: str, payload: dict) -> None:
        if self.event_recorder is not None:
            self.event_recorder(event, payload)

    async def prepare(self, task: str, agent_config: dict | None = None) -> AgentState:
        config = dict(agent_config or {})
        system_prompt = config.get("system_prompt")
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": task})
        state = AgentState(
            run_id=config.get("run_id") or uuid.uuid4().hex,
            agent_id=config.get("agent_id", "default-agent"),
            task=task,
            messages=messages,
            context={"system_prompt": system_prompt, "agent_config": config},
            status=RunStatus.PENDING,
        )
        self.emit("run.prepared", {"run_id": state.run_id, "agent_id": state.agent_id})
        return state

    async def build_context(self, state: AgentState) -> list[dict]:
        if self.context_engine is not None:
            tools = await self.resolve_tools(state)
            messages = await self.context_engine.build(
                state, state.context.get("system_prompt"), tools
            )
        else:
            messages = list(state.messages)
        self.emit(
            "context.created",
            {"run_id": state.run_id, "step": state.step, "message_count": len(messages)},
        )
        return messages

    async def resolve_tools(self, state: AgentState) -> list[dict]:
        if self.tool_gateway is None:
            return []
        return self.tool_gateway.schemas()

    async def check_policy(self, action: dict) -> str:
        if self.policy_engine is not None:
            return self.policy_engine.check(action["tool"]).value
        return "allow"

    async def execute(self, state: AgentState, tool_call: ToolCall) -> dict:
        if self.tool_gateway is None:
            raise RuntimeError("No tool gateway configured")
        result = await self.tool_gateway.call(tool_call.name, tool_call.arguments)
        return {"tool": tool_call.name, "result": result}

    async def observe(self, state: AgentState, result: dict) -> None:
        observation = {"step": state.step, **result}
        state.observations.append(observation)
        if "result" in result:
            state.tool_results.append({"tool": result.get("tool"), "result": result["result"]})
            content = json.dumps(result["result"], ensure_ascii=False, default=str)
        else:
            content = str(result.get("error", ""))
        state.messages.append(
            {
                "role": "tool",
                "tool_call_id": result.get("tool_call_id", ""),
                "name": result.get("tool", ""),
                "content": content,
            }
        )
        self.emit("observation", observation)

    async def finalize(self, state: AgentState) -> dict:
        summary = {
            "run_id": state.run_id,
            "agent_id": state.agent_id,
            "status": state.status.value,
            "answer": state.context.get("final_answer"),
            "steps": state.step,
            "token_usage": dict(state.token_usage),
            "cost": state.cost,
            "error": state.error,
        }
        self.emit("run_finalized", summary)
        return summary
