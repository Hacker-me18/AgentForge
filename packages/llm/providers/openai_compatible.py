"""OpenAI-compatible chat-completions provider (works for OpenAI and compatible APIs)."""

import json

import httpx

from packages.llm.base import LLMProvider, LLMResponse, ToolCall


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str = "gpt-4o-mini",
        timeout: float = 60.0,
    ):
        if not api_key:
            raise ValueError("OpenAICompatibleProvider requires an API key")
        if not base_url:
            raise ValueError("OpenAICompatibleProvider requires a base_url")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        model_name = model or self._default_model
        payload: dict = {"model": model_name, "messages": messages}
        if tools:
            payload["tools"] = tools
        headers = {"Authorization": f"Bearer {self._api_key}"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        message = choice.get("message") or {}
        tool_calls = []
        for raw_call in message.get("tool_calls") or []:
            function = raw_call.get("function") or {}
            raw_args = function.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_args)
            except json.JSONDecodeError:
                arguments = {"raw": raw_args}
            tool_calls.append(
                ToolCall(
                    id=raw_call.get("id", ""),
                    name=function.get("name", ""),
                    arguments=arguments,
                )
            )

        usage = data.get("usage") or {}
        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            model=data.get("model", model_name),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason") or "stop",
        )
