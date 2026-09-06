"""Run budget control: steps / tokens / cost / latency."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Budget:
    max_steps: int | None = 16
    max_tokens: int | None = None
    max_cost: float | None = None
    max_latency_s: float | None = None

    def exceeded(self, *, step: int, tokens: int, cost: float, elapsed_s: float) -> str | None:
        """Return a human-readable reason if any budget dimension is exceeded."""
        if self.max_steps is not None and step >= self.max_steps:
            return f"step budget exceeded ({step}/{self.max_steps})"
        if self.max_tokens is not None and tokens >= self.max_tokens:
            return f"token budget exceeded ({tokens}/{self.max_tokens})"
        if self.max_cost is not None and cost >= self.max_cost:
            return f"cost budget exceeded (${cost:.4f}/${self.max_cost:.4f})"
        if self.max_latency_s is not None and elapsed_s >= self.max_latency_s:
            return f"latency budget exceeded ({elapsed_s:.1f}s/{self.max_latency_s}s)"
        return None
