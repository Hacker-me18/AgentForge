"""Tests for tracing: event store, trace building, cost summary and runs API."""

import asyncio

from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from packages.tracing.bus import EventBus
from packages.tracing.events import Event
from packages.tracing.store import EventStore
from packages.tracing.trace import TraceBuilder


async def test_event_store_append_and_list(tmp_path) -> None:
    store = EventStore(str(tmp_path / "events.db"))
    await store.append(Event(run_id="r1", type="run.started", payload={"task": "t"}))
    await store.append(Event(run_id="r1", type="llm.request", payload={}))
    await store.append(Event(run_id="r2", type="run.started", payload={}))

    events = await store.for_run("r1")
    assert [e.type for e in events] == ["run.started", "llm.request"]
    assert [e.sequence for e in events] == [1, 2]
    assert events[0].payload["task"] == "t"
    assert len(await store.for_run("r2")) == 1


async def test_event_bus_recorder(tmp_path) -> None:
    bus = EventBus(EventStore(str(tmp_path / "events.db")))
    seen: list[Event] = []
    bus.subscribe(seen.append)
    recorder = bus.recorder("r1")
    recorder("tool.request", {"tool": "web.search"})
    recorder("tool.completed", {"tool": "web.search", "duration_ms": 5})
    await bus.flush()
    assert [e.type for e in seen] == ["tool.request", "tool.completed"]
    assert len(await bus.store.for_run("r1")) == 2


def _run_events() -> list[Event]:
    """Synthetic event stream: Run → Context → LLM → Tool → LLM → Final."""

    def ev(seq: int, type_: str, ts: float, **payload) -> Event:
        return Event(run_id="r1", type=type_, timestamp=ts, sequence=seq, payload=payload)

    return [
        ev(1, "run.started", 0.0, task="compare"),
        ev(2, "context.created", 0.1, step=0),
        ev(3, "llm.request", 0.2, step=1),
        ev(
            4,
            "llm.response",
            0.8,
            step=1,
            model="deepseek-chat",
            input_tokens=1000,
            output_tokens=200,
            tool_calls=1,
        ),
        ev(5, "tool.request", 0.9, tool="web.search"),
        ev(6, "policy.checked", 0.91, tool="web.search", decision="allow"),
        ev(7, "tool.started", 0.92, tool="web.search"),
        ev(8, "tool.completed", 1.4, tool="web.search", duration_ms=480),
        ev(9, "llm.request", 1.5, step=2),
        ev(
            10,
            "llm.response",
            2.0,
            step=2,
            model="deepseek-chat",
            input_tokens=1500,
            output_tokens=400,
            tool_calls=0,
        ),
        ev(11, "run.completed", 2.1, steps=2, cost=0.00071),
    ]


def test_trace_builder_tree_and_cost() -> None:
    trace = TraceBuilder().build(_run_events())
    root = trace["root"]
    assert root["kind"] == "run"
    assert root["status"] == "ok"
    assert root["duration_ms"] == 2100

    kinds = [child["kind"] for child in root["children"]]
    assert "context" in kinds
    assert kinds.count("llm") == 2

    llm_span = [c for c in root["children"] if c["kind"] == "llm"][0]
    assert llm_span["duration_ms"] == 600
    # The tool call happens after the first llm span is closed; it may attach to
    # the root. Either way exactly one tool span exists and it is closed.
    all_tool_spans = [
        s for parent in [root, *root["children"]] for s in parent["children"] if s["kind"] == "tool"
    ]
    assert len(all_tool_spans) == 1
    assert all_tool_spans[0]["status"] == "ok"
    assert all_tool_spans[0]["duration_ms"] == 500

    summary = trace["summary"]
    assert summary["llm_calls"] == 2
    assert summary["tool_calls"] == 1
    assert summary["total_tokens"] == 3100
    # (1000*0.27 + 200*1.10 + 1500*0.27 + 400*1.10) / 1e6
    assert summary["cost"] == 0.001335


async def test_runs_api_end_to_end() -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/runs", json={"task": "echo test", "max_steps": 5})
            assert resp.status_code == 201
            run_id = resp.json()["run_id"]

            # Poll until the background run finishes.
            record = {}
            for _ in range(100):
                await asyncio.sleep(0.05)
                record = (await client.get(f"/api/runs/{run_id}")).json()
                if record["status"] not in ("pending", "running"):
                    break
            assert record["status"] == "completed"
            assert record["answer"]
            assert record["steps"] >= 1

            # Events cover the full lifecycle.
            events = (await client.get(f"/api/runs/{run_id}/events")).json()
            types = {e["type"] for e in events}
            expected = {
                "run.started",
                "context.created",
                "llm.request",
                "llm.response",
                "tool.request",
                "tool.started",
                "tool.completed",
                "run.completed",
            }
            assert expected <= types
            assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))

            # Trace tree + summary.
            trace = (await client.get(f"/api/runs/{run_id}/trace")).json()
            assert trace["root"]["kind"] == "run"
            assert trace["root"]["status"] == "ok"
            assert trace["summary"]["llm_calls"] >= 1
            assert trace["summary"]["tool_calls"] >= 1

            # Listing shows the run.
            runs = (await client.get("/api/runs")).json()
            assert any(r["run_id"] == run_id for r in runs)
