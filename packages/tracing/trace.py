"""Build a span tree (trace) from the flat event stream of a run."""

from packages.tracing.cost import CostTracker
from packages.tracing.events import Event

_OPENERS = {
    "context": "context.created",
    "llm": "llm.request",
    "tool": "tool.request",
    "sandbox": "sandbox.started",
    "approval": "approval.requested",
}
_CLOSERS = {
    "context": {"context.created"},
    "llm": {"llm.response"},
    "tool": {"tool.completed", "tool.failed"},
    "sandbox": {"sandbox.completed", "sandbox.failed"},
    "approval": {"approval.decided"},
}
_STATUS_BY_CLOSER = {
    "tool.failed": "failed",
    "sandbox.failed": "failed",
    "llm.response": "ok",
    "context.created": "ok",
    "sandbox.completed": "ok",
    "tool.completed": "ok",
    "approval.decided": "ok",
}


def _span(kind: str, name: str, start: float, attrs: dict) -> dict:
    return {
        "kind": kind,
        "name": name,
        "start": start,
        "end": None,
        "duration_ms": None,
        "status": "running",
        "attrs": attrs,
        "children": [],
    }


def _close(span: dict, end: float, status: str) -> None:
    span["end"] = end
    span["duration_ms"] = round((end - span["start"]) * 1000, 2)
    span["status"] = status


class TraceBuilder:
    """Reconstructs Run → Context/LLM/Tool/Sandbox/Approval → Final spans."""

    def build(self, events: list[Event]) -> dict:
        events = sorted(events, key=lambda e: e.sequence)
        root: dict | None = None
        open_spans: list[dict] = []

        for event in events:
            etype = event.type
            if etype == "run.started":
                root = _span("run", "run", event.timestamp, dict(event.payload))
                continue
            if root is None:
                continue

            if etype in ("run.completed", "run.failed"):
                while open_spans:
                    _close(open_spans.pop(), event.timestamp, "interrupted")
                status = "ok" if etype == "run.completed" else "failed"
                root["attrs"].update(event.payload)
                _close(root, event.timestamp, status)
                continue

            kind = self._opener_kind(etype)
            if kind is not None:
                name = str(event.payload.get("tool") or kind)
                span = _span(kind, name, event.timestamp, dict(event.payload))
                parent = open_spans[-1] if open_spans else root
                parent["children"].append(span)
                if kind != "context":  # context.created is instantaneous
                    open_spans.append(span)
                else:
                    _close(span, event.timestamp, "ok")
                continue

            closer_kind = self._closer_kind(etype)
            if closer_kind is not None:
                matched = self._pop_matching(open_spans, closer_kind)
                if matched is not None:
                    matched["attrs"].update(event.payload)
                    _close(matched, event.timestamp, _STATUS_BY_CLOSER.get(etype, "ok"))
                continue

            # Point events (policy.checked, checkpoint.created, observation...).
            point = _span("event", etype, event.timestamp, dict(event.payload))
            _close(point, event.timestamp, "ok")
            parent = open_spans[-1] if open_spans else root
            parent["children"].append(point)

        if root is None:
            root = _span("run", "run", 0.0, {})
            root["status"] = "unknown"
        elif root["end"] is None:
            _close(root, events[-1].timestamp if events else 0.0, "running")

        return {
            "root": root,
            "summary": CostTracker().summarize(events),
        }

    @staticmethod
    def _opener_kind(event_type: str) -> str | None:
        for kind, opener in _OPENERS.items():
            if event_type == opener:
                return kind
        return None

    @staticmethod
    def _closer_kind(event_type: str) -> str | None:
        for kind, closers in _CLOSERS.items():
            if event_type in closers and kind != "context":
                return kind
        return None

    @staticmethod
    def _pop_matching(open_spans: list[dict], kind: str) -> dict | None:
        for i in range(len(open_spans) - 1, -1, -1):
            if open_spans[i]["kind"] == kind:
                return open_spans.pop(i)
        return None
