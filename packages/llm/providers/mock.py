"""Deterministic mock LLM provider for tests and demos."""

from packages.llm.base import LLMProvider, LLMResponse, ToolCall


def _estimate(text: str) -> int:
    return max(1, len(text) // 4)


class MockLLMProvider(LLMProvider):
    """Scriptable, deterministic provider.

    If ``scripted`` responses are provided they are returned in order. Otherwise:
    - when the latest message is a tool result (role == "tool"), return a final
      summary text with finish_reason="stop";
    - otherwise return a single tool call to ``mock.echo`` echoing the user task.
    """

    def __init__(self, scripted: list[LLMResponse] | None = None, model: str = "mock-model"):
        self._scripted = list(scripted or [])
        self._model = model

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        if self._scripted:
            return self._scripted.pop(0)

        model_name = model or self._model
        input_tokens = _estimate(str(messages))
        last = messages[-1] if messages else {}

        if last.get("role") == "tool":
            snippet = str(last.get("content", ""))[:200]
            content = f"Task summary: tool result received, task completed. Result: {snippet}"
            return LLMResponse(
                content=content,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=_estimate(content),
                finish_reason="stop",
            )

        task = ""
        for message in messages:
            if message.get("role") == "user":
                task = str(message.get("content", ""))
        call = ToolCall(id="mock-call-1", name="mock.echo", arguments={"text": task})
        return LLMResponse(
            content="",
            tool_calls=[call],
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=8,
            finish_reason="tool_calls",
        )
