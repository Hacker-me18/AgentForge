"""Deterministic mock LLM provider for tests and demos."""

import json
import re

from packages.llm.base import LLMProvider, LLMResponse, ToolCall


def _estimate(text: str) -> int:
    return max(1, len(text) // 4)


def _rank_by_query(query: str, results: list[dict]) -> list[dict]:
    """Order search results by keyword overlap with the query (best first)."""
    tokens = {token for token in re.split(r"\W+", query.lower()) if len(token) >= 3}

    def score(item: dict) -> int:
        haystack = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
        return sum(1 for token in tokens if token in haystack)

    return sorted(results, key=score, reverse=True)


def _tool_summary(snippet: str) -> str:
    """Render the last real tool result as a readable closing statement."""
    try:
        data = json.loads(snippet)
    except (ValueError, TypeError):
        return snippet[:280]
    if not isinstance(data, dict):
        return snippet[:280]
    # The gateway wraps every tool output in {"status", "output", "duration_ms"}.
    if isinstance(data.get("output"), dict):
        data = data["output"]
    results = data.get("results")
    if isinstance(results, list):
        if not results:
            return "no matching results found"
        ranked = _rank_by_query(str(data.get("query", "")), results)
        lines = [
            f"- {item.get('title', '')}: {item.get('snippet', '')[:110]}" for item in ranked[:2]
        ]
        if len(ranked) > 2:
            lines.append(f"+ {len(ranked) - 2} more")
        return "search results:\n" + "\n".join(lines)
    if "expression" in data and "result" in data:
        return f"{data['expression']} = {data['result']}"
    if "affected_rows" in data:
        return f"database write affected {data['affected_rows']} row(s)"
    if isinstance(data.get("content"), str):
        return data["content"][:280]
    return snippet[:280]


_ARITHMETIC_RE = re.compile(r"\d+(?:\.\d+)?(?:\s*[-+*/]\s*\d+(?:\.\d+)?)+")


class MockLLMProvider(LLMProvider):
    """Scriptable, deterministic provider.

    If ``scripted`` responses are provided they are returned in order. Otherwise:
    - when the latest non-system message is a tool result (role == "tool"),
      return a final summary text with finish_reason="stop";
    - otherwise pick a tool according to ``strategy``:
      - ``"echo"`` (default): call ``mock.echo`` echoing the user task;
      - ``"route"``: keyword router — tasks containing an arithmetic
        expression go to ``calculator``, everything else to ``web.search``.
    """

    def __init__(
        self,
        scripted: list[LLMResponse] | None = None,
        model: str = "mock-model",
        strategy: str = "echo",
    ):
        self._scripted = list(scripted or [])
        self._model = model
        self._strategy = strategy

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
        # The context engine may append system "extras" after the conversation,
        # so inspect the last non-system message instead of messages[-1].
        last = next((m for m in reversed(messages) if m.get("role") != "system"), {})

        if last.get("role") == "tool":
            snippet = str(last.get("content", ""))
            content = f"Done. {_tool_summary(snippet)}"
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
        call = self._route(task) if self._strategy == "route" else self._echo(task)
        return LLMResponse(
            content="",
            tool_calls=[call],
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=8,
            finish_reason="tool_calls",
        )

    @staticmethod
    def _echo(task: str) -> ToolCall:
        return ToolCall(id="mock-call-1", name="mock.echo", arguments={"text": task})

    @staticmethod
    def _route(task: str) -> ToolCall:
        expression = _ARITHMETIC_RE.search(task)
        if expression is not None:
            return ToolCall(
                id="mock-call-1",
                name="calculator",
                arguments={"expression": expression.group(0)},
            )
        return ToolCall(id="mock-call-1", name="web.search", arguments={"query": task})
