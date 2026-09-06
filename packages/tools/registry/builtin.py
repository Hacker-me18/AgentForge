"""Built-in local tools shipped with the platform.

All tools are registered via :func:`create_default_registry`. Shell execution
is CRITICAL risk and effectively disabled by default policy (Phase E will
enforce it); ``python.execute`` runs inside the Phase D Docker sandbox
(``agentos-sandbox`` image) with network disabled and resource limits.
"""

import ast
import sqlite3
from pathlib import Path
from typing import Any

from packages.sandbox import (
    DockerUnavailableError,
    ResourceLimits,
    SandboxRunner,
)
from packages.tools.base import RiskLevel, ToolMetadata
from packages.tools.registry.registry import FunctionTool, ToolRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DOCS_DIR = REPO_ROOT / "datasets" / "docs"

# ---------------------------------------------------------------------------
# calculator: safe arithmetic evaluation via an AST whitelist
# ---------------------------------------------------------------------------

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)
_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    *_ALLOWED_BINOPS,
    *_ALLOWED_UNARYOPS,
)


def _safe_eval(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"disallowed expression node: {type(node).__name__}")
        if isinstance(node, ast.BinOp) and not isinstance(node.op, _ALLOWED_BINOPS):
            raise ValueError(f"disallowed operator: {type(node.op).__name__}")
        if isinstance(node, ast.UnaryOp) and not isinstance(node.op, _ALLOWED_UNARYOPS):
            raise ValueError(f"disallowed unary operator: {type(node.op).__name__}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("only numeric constants are allowed")
    return eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}}, {})


def _calculator(arguments: dict, state: Any = None) -> dict:
    expression = str(arguments.get("expression", ""))
    result = _safe_eval(expression)
    return {"expression": expression, "result": result}


# ---------------------------------------------------------------------------
# web.search: static knowledge base (MVP, no network)
# ---------------------------------------------------------------------------

_KNOWLEDGE_BASE: list[dict] = [
    {
        "title": "PostgreSQL vs MySQL: Key Differences",
        "url": "https://example.com/postgresql-vs-mysql",
        "snippet": (
            "PostgreSQL offers advanced SQL compliance, JSONB support and "
            "extensibility, while MySQL is often faster for simple read-heavy "
            "workloads and has a larger hosting ecosystem."
        ),
    },
    {
        "title": "Why PostgreSQL is preferred for complex queries",
        "url": "https://example.com/postgresql-complex-queries",
        "snippet": (
            "PostgreSQL supports CTEs, window functions, partial indexes and "
            "a powerful query planner, making it well suited for analytics and "
            "complex relational models."
        ),
    },
    {
        "title": "MySQL replication and scaling primer",
        "url": "https://example.com/mysql-replication",
        "snippet": (
            "MySQL provides mature binlog-based replication and read replicas; "
            "PostgreSQL streaming replication is comparable, but MySQL's "
            "ecosystem (e.g. Vitess) is often cited for horizontal sharding."
        ),
    },
    {
        "title": "ACID and transactions: PostgreSQL vs MySQL InnoDB",
        "url": "https://example.com/acid-postgresql-mysql",
        "snippet": (
            "Both PostgreSQL and MySQL (InnoDB) are ACID compliant; PostgreSQL "
            "implements MVCC without a separate undo log, while InnoDB relies "
            "on undo segments and doublewrite buffering."
        ),
    },
    {
        "title": "Redis vs Memcached for caching",
        "url": "https://example.com/redis-vs-memcached",
        "snippet": (
            "Redis supports rich data structures (hashes, sorted sets), "
            "persistence and Lua scripting, while Memcached is a simpler "
            "multi-threaded LRU cache with lower per-key overhead."
        ),
    },
    {
        "title": "Kafka vs RabbitMQ: message systems compared",
        "url": "https://example.com/kafka-vs-rabbitmq",
        "snippet": (
            "Kafka is a distributed append-only log optimized for high-throughput "
            "event streaming and replay, while RabbitMQ is a broker-centric "
            "queue with flexible routing (exchanges) and per-message ACKs."
        ),
    },
    {
        "title": "React vs Vue: frontend framework trade-offs",
        "url": "https://example.com/react-vs-vue",
        "snippet": (
            "React uses JSX and a unidirectional data flow with a large "
            "ecosystem, while Vue offers single-file components, built-in "
            "reactivity and a gentler learning curve."
        ),
    },
    {
        "title": "REST vs GraphQL API design",
        "url": "https://example.com/rest-vs-graphql",
        "snippet": (
            "REST exposes fixed resources over HTTP verbs and caching, while "
            "GraphQL lets clients declare exactly which fields they need via a "
            "typed schema, avoiding over-fetching but complicating cache."
        ),
    },
    {
        "title": "Docker vs Kubernetes: containers vs orchestration",
        "url": "https://example.com/docker-vs-kubernetes",
        "snippet": (
            "Docker packages and runs individual containers, while Kubernetes "
            "orchestrates fleets of containers with scheduling, self-healing, "
            "service discovery and horizontal autoscaling."
        ),
    },
    {
        "title": "MongoDB vs relational databases",
        "url": "https://example.com/mongodb-vs-relational",
        "snippet": (
            "MongoDB stores flexible BSON documents and scales horizontally via "
            "sharding, while relational databases enforce schemas and joins "
            "with strong transactional guarantees."
        ),
    },
    {
        "title": "gRPC vs REST for service communication",
        "url": "https://example.com/grpc-vs-rest",
        "snippet": (
            "gRPC uses HTTP/2 with protobuf binary encoding and code-generated "
            "stubs for low-latency RPC, while REST relies on textual JSON and "
            "is easier to debug and browse."
        ),
    },
    {
        "title": "TCP vs UDP transport protocols",
        "url": "https://example.com/tcp-vs-udp",
        "snippet": (
            "TCP provides ordered, reliable, congestion-controlled byte streams "
            "via handshakes and retransmission, while UDP is connectionless "
            "with minimal latency, suiting DNS and real-time media."
        ),
    },
    {
        "title": "Microservices vs monolith architecture",
        "url": "https://example.com/microservices-vs-monolith",
        "snippet": (
            "Microservices split a system into independently deployable "
            "services with separate data stores, while a monolith keeps one "
            "deployable unit, simplifying transactions and local development."
        ),
    },
    {
        "title": "Python vs JavaScript for data science",
        "url": "https://example.com/python-vs-javascript-ds",
        "snippet": (
            "Python dominates data science with NumPy, pandas and scikit-learn, "
            "while JavaScript is stronger for interactive browser "
            "visualizations with D3.js and full-stack sharing."
        ),
    },
    {
        "title": "JWT vs session-based authentication",
        "url": "https://example.com/jwt-vs-session",
        "snippet": (
            "JWTs are stateless signed tokens verified without a server-side "
            "store, while session auth keeps state server-side, making "
            "revocation trivial but requiring sticky sessions or shared stores."
        ),
    },
    {
        "title": "B-tree vs LSM-tree storage engines",
        "url": "https://example.com/btree-vs-lsm",
        "snippet": (
            "B-trees update pages in place and excel at reads, while LSM-trees "
            "buffer writes in memtables and flush sorted runs (SSTables), "
            "favoring write-heavy workloads like time-series data."
        ),
    },
]


def _web_search(arguments: dict, state: Any = None) -> dict:
    query = str(arguments.get("query", "")).lower()
    terms = [t for t in query.replace("/", " ").split() if len(t) >= 2]
    results = []
    for entry in _KNOWLEDGE_BASE:
        haystack = f"{entry['title']} {entry['snippet']}".lower()
        if not terms or any(term in haystack for term in terms):
            results.append(dict(entry))
    return {"query": arguments.get("query", ""), "results": results}


# ---------------------------------------------------------------------------
# document.read: whitelist-directory text file reading (path-traversal safe)
# ---------------------------------------------------------------------------


def _document_read(arguments: dict, state: Any = None) -> dict:
    base = Path(arguments.get("base_dir") or DEFAULT_DOCS_DIR).resolve()
    rel = str(arguments.get("path", ""))
    target = (base / rel).resolve()
    if base != target and base not in target.parents:
        raise ValueError(f"path escapes allowed directory: {rel}")
    if not target.is_file():
        raise FileNotFoundError(f"file not found: {rel}")
    content = target.read_text(encoding="utf-8")
    return {"path": str(target), "content": content}


# ---------------------------------------------------------------------------
# database.read / database.write: local SQLite
# ---------------------------------------------------------------------------

_WRITE_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
}


def _db_path(arguments: dict) -> str:
    db_path = str(arguments.get("db_path") or REPO_ROOT / "data" / "agentos.db")
    return db_path


def _database_read(arguments: dict, state: Any = None) -> dict:
    query = str(arguments.get("query", "")).strip()
    lowered = query.lower()
    if not lowered.startswith("select"):
        raise ValueError("database.read only allows SELECT statements")
    tokens = {t.strip("();,") for t in lowered.split()}
    if tokens & _WRITE_KEYWORDS:
        raise ValueError("write keywords are not allowed in database.read")
    conn = sqlite3.connect(f"file:{_db_path(arguments)}?mode=ro", uri=True)
    try:
        cursor = conn.execute(query)
        columns = [desc[0] for desc in cursor.description or []]
        rows = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
    finally:
        conn.close()
    return {"columns": columns, "rows": rows, "row_count": len(rows)}


def _database_write(arguments: dict, state: Any = None) -> dict:
    query = str(arguments.get("query", "")).strip()
    # timeout: wait for the event bus's fire-and-forget writers instead of
    # surfacing SQLITE_BUSY when they briefly hold the write lock.
    conn = sqlite3.connect(_db_path(arguments), timeout=15)
    try:
        cursor = conn.execute(query)
        conn.commit()
        affected = cursor.rowcount
    finally:
        conn.close()
    return {"affected_rows": affected, "query": query}


# ---------------------------------------------------------------------------
# shell.execute: CRITICAL, denied by default policy (Phase E)
# ---------------------------------------------------------------------------


def _shell_execute(arguments: dict, state: Any = None) -> dict:
    return {
        "status": "denied",
        "message": (
            "shell.execute is CRITICAL risk and is DENIED by the default "
            "policy; Phase E approval flow is required to enable it."
        ),
        "command": arguments.get("command", ""),
    }


# ---------------------------------------------------------------------------
# python.execute: Docker sandbox execution (Phase D)
# ---------------------------------------------------------------------------


def _make_python_execute(runner: SandboxRunner):
    async def _python_execute(arguments: dict, state: Any = None) -> dict:
        code = str(arguments.get("code", ""))
        timeout = float(arguments.get("timeout", 30))
        limits = ResourceLimits(timeout_s=timeout)
        try:
            result = await runner.run(code, limits=limits)
        except DockerUnavailableError as exc:
            return {
                "status": "error",
                "stdout": "",
                "stderr": f"docker unavailable: {exc}",
                "artifacts": [],
                "summary": "docker unavailable",
            }
        summary = (
            f"status={result.status} exit_code={result.exit_code} "
            f"duration_ms={result.duration_ms:.0f} artifacts={len(result.artifacts)}"
        )
        return {
            "status": result.status,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "artifacts": list(result.artifacts),
            "summary": summary,
        }

    return _python_execute


# ---------------------------------------------------------------------------
# registry factory
# ---------------------------------------------------------------------------

_OBJECT_SCHEMA = {"type": "object", "properties": {}}


def create_default_registry(sandbox_runner: SandboxRunner | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        FunctionTool(
            ToolMetadata(
                name="mock.echo",
                description="Echo back the given arguments (testing utility).",
                input_schema=_OBJECT_SCHEMA,
                risk_level=RiskLevel.LOW,
            ),
            lambda arguments, state=None: {"echo": arguments},
        )
    )
    registry.register(
        FunctionTool(
            ToolMetadata(
                name="calculator",
                description="Evaluate a basic arithmetic expression safely.",
                input_schema={
                    "type": "object",
                    "properties": {"expression": {"type": "string", "description": "e.g. '1+2*3'"}},
                    "required": ["expression"],
                },
                risk_level=RiskLevel.LOW,
            ),
            _calculator,
        )
    )
    registry.register(
        FunctionTool(
            ToolMetadata(
                name="web.search",
                description="Search the web (MVP: built-in static knowledge base).",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                risk_level=RiskLevel.LOW,
                cost=0.001,
            ),
            _web_search,
        )
    )
    registry.register(
        FunctionTool(
            ToolMetadata(
                name="document.read",
                description="Read a text file inside the whitelisted docs directory.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "relative file path"},
                        "base_dir": {"type": "string", "description": "optional override"},
                    },
                    "required": ["path"],
                },
                risk_level=RiskLevel.LOW,
            ),
            _document_read,
        )
    )
    registry.register(
        FunctionTool(
            ToolMetadata(
                name="database.read",
                description="Run a read-only SELECT query against a local SQLite database.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "db_path": {"type": "string"},
                    },
                    "required": ["query"],
                },
                risk_level=RiskLevel.MEDIUM,
            ),
            _database_read,
        )
    )
    registry.register(
        FunctionTool(
            ToolMetadata(
                name="database.write",
                description="Execute a write SQL statement against a local SQLite database.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "db_path": {"type": "string"},
                    },
                    "required": ["query"],
                },
                risk_level=RiskLevel.HIGH,
            ),
            _database_write,
        )
    )
    registry.register(
        FunctionTool(
            ToolMetadata(
                name="shell.execute",
                description="Execute a shell command (CRITICAL; denied by default policy).",
                input_schema={
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
                risk_level=RiskLevel.CRITICAL,
                permission=["shell"],
            ),
            _shell_execute,
        )
    )
    registry.register(
        FunctionTool(
            ToolMetadata(
                name="python.execute",
                description=(
                    "Execute Python code inside an isolated Docker sandbox "
                    "(agentos-sandbox image; network disabled, memory/CPU limited)."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "timeout": {"type": "number"},
                    },
                    "required": ["code"],
                },
                risk_level=RiskLevel.MEDIUM,
                timeout=35,
            ),
            _make_python_execute(sandbox_runner or SandboxRunner()),
        )
    )
    return registry
