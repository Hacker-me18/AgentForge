"""Minimal context engine: Collect -> Rank -> Compress -> Budget -> Assemble."""

import json
from typing import Any


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class ContextEngine:
    def __init__(self, token_budget: int = 16000, keep_recent: int = 6,
                 compress_threshold: int = 200):
        self.token_budget = token_budget
        self.keep_recent = keep_recent
        self.compress_threshold = compress_threshold

    async def build(
        self,
        state: Any,
        system_prompt: str | None = None,
        tool_schemas: list[dict] | None = None,
    ) -> list[dict]:
        collected = self._collect(state, system_prompt, tool_schemas)
        if self._total_tokens(collected) <= self.token_budget:
            return collected
        compressed = self._compress(collected)
        if self._total_tokens(compressed) <= self.token_budget:
            return compressed
        return self._truncate(compressed)

    def estimate(self, messages: list[dict]) -> int:
        return self._total_tokens(messages)

    def _collect(
        self, state: Any, system_prompt: str | None, tool_schemas: list[dict] | None
    ) -> list[dict]:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(state.messages)

        extras: list[dict] = []
        if tool_schemas:
            summary = "; ".join(
                f"{t.get('name', '?')}: {t.get('description', '')}" for t in tool_schemas
            )
            extras.append({"role": "system", "content": f"Available tools: {summary}"})
        if state.memory:
            extras.append(
                {
                    "role": "system",
                    "content": f"Memory: {json.dumps(state.memory, ensure_ascii=False, default=str)}",
                }
            )
        recent_observations = state.observations[-5:]
        if recent_observations:
            extras.append(
                {
                    "role": "system",
                    "content": "Recent observations: "
                    + json.dumps(recent_observations, ensure_ascii=False, default=str)[:2000],
                }
            )
        return messages + extras

    def _compress(self, messages: list[dict]) -> list[dict]:
        result = []
        total = len(messages)
        for index, message in enumerate(messages):
            content = message.get("content", "")
            keep = message.get("role") == "system" or index >= total - self.keep_recent
            if not keep and isinstance(content, str) and len(content) > self.compress_threshold:
                message = {**message, "content": f"[compressed] {content[: self.compress_threshold]}"}
            result.append(message)
        return result

    def _truncate(self, messages: list[dict]) -> list[dict]:
        # Drop oldest non-system messages until within budget; always keep system.
        result = list(messages)
        while len(result) > 1 and self._total_tokens(result) > self.token_budget:
            for index, message in enumerate(result):
                if message.get("role") != "system":
                    del result[index]
                    break
            else:
                break
        return result

    @staticmethod
    def _total_tokens(messages: list[dict]) -> int:
        return sum(estimate_tokens(str(m.get("content", ""))) + 4 for m in messages)
