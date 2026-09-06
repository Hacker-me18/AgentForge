"""Run cost accounting derived from llm events."""

from packages.runtime.execution import MODEL_PRICING
from packages.tracing.events import Event

DEFAULT_PRICING = (0.0, 0.0)


class CostTracker:
    """Aggregates token usage, cost and call counts from run events."""

    def summarize(self, events: list[Event]) -> dict:
        input_tokens = 0
        output_tokens = 0
        cost = 0.0
        llm_calls = 0
        tool_calls = 0
        sandbox_runs = 0
        for event in events:
            if event.type == "llm.response":
                llm_calls += 1
                in_tok = int(event.payload.get("input_tokens", 0))
                out_tok = int(event.payload.get("output_tokens", 0))
                input_tokens += in_tok
                output_tokens += out_tok
                price_in, price_out = MODEL_PRICING.get(
                    str(event.payload.get("model", "")), DEFAULT_PRICING
                )
                cost += (in_tok * price_in + out_tok * price_out) / 1_000_000
            elif event.type == "tool.request":
                tool_calls += 1
            elif event.type == "sandbox.started":
                sandbox_runs += 1
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": round(cost, 6),
            "llm_calls": llm_calls,
            "tool_calls": tool_calls,
            "sandbox_runs": sandbox_runs,
        }
