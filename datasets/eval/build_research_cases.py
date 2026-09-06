"""Generate ``research.json`` (>=30 research evaluation cases).

Each case is a research/comparison prompt whose expected evidence is fully
covered by the built-in ``web.search`` knowledge base. Running this module
*simulates* the exact tool-output text a run would embed in its final answer
and asserts that every ``expected_keywords`` token appears in it, so the file
on disk is guaranteed to score well on the Evidence dimension offline.

Usage:  python -m datasets.eval.build_research_cases   (from repo root)
"""

import json
import re
from pathlib import Path

from packages.evaluation.dataset import Case, Dataset
from packages.tools.registry.builtin import _web_search

OUT = Path(__file__).resolve().parent / "research.json"

# Mirrors packages/llm/providers/mock.py so keyword checks use the same rules.
_ARITHMETIC_RE = re.compile(r"\d+(?:\.\d+)?(?:\s*[-+*/]\s*\d+(?:\.\d+)?)+")

# (task, [expected keywords]) -- keywords copied verbatim from KB snippets.
_CASES: list[dict] = [
    # --- PostgreSQL / MySQL -------------------------------------------------
    {
        "task": "Write a short comparison report of PostgreSQL vs MySQL, focusing on "
        "SQL compliance, JSONB and which one wins on simple read-heavy workloads. "
        "Cite concrete details.",
        "keywords": ["PostgreSQL", "MySQL", "JSONB", "read-heavy"],
    },
    {
        "task": "Research the key differences between PostgreSQL and MySQL and decide "
        "which is easier to host at scale. Report the specific features each database "
        "is known for.",
        "keywords": ["advanced SQL compliance", "extensibility", "hosting ecosystem"],
    },
    {
        "task": "Explain why PostgreSQL is preferred for complex analytical queries. "
        "Which SQL features make it well suited to analytics and complex relational models?",
        "keywords": ["PostgreSQL", "window functions", "partial indexes", "query planner"],
    },
    # --- Redis / Memcached --------------------------------------------------
    {
        "task": "Compare Redis vs Memcached for a caching layer. Which one supports "
        "rich data structures and persistence, and which stays a simpler LRU cache?",
        "keywords": ["Redis", "Memcached", "sorted sets", "Lua scripting", "LRU"],
    },
    {
        "task": "Should we use Redis or Memcached for low-latency caching? Research both "
        "and report how they differ in threading model and per-key overhead.",
        "keywords": ["multi-threaded", "LRU cache", "lower per-key overhead", "persistence"],
    },
    # --- Kafka / RabbitMQ ---------------------------------------------------
    {
        "task": "Compare Kafka vs RabbitMQ as a message system. Report how each one is "
        "optimized: high-throughput event streaming and replay versus flexible routing and ACKs.",
        "keywords": ["Kafka", "RabbitMQ", "append-only log", "event streaming"],
    },
    {
        "task": "Research how Kafka and RabbitMQ differ on delivery semantics and "
        "routing flexibility for a queue-based architecture.",
        "keywords": ["broker-centric", "exchanges", "per-message ACKs", "replay"],
    },
    # --- React / Vue --------------------------------------------------------
    {
        "task": "Compare React vs Vue for a frontend team that values a gentle learning "
        "curve. Which uses JSX with a large ecosystem, and which ships single-file components?",
        "keywords": ["React", "Vue", "JSX", "single-file components"],
    },
    {
        "task": "Research the trade-offs between React and Vue regarding data flow and "
        "built-in features before picking a framework.",
        "keywords": ["unidirectional data flow", "built-in reactivity", "learning curve"],
    },
    # --- REST / GraphQL -----------------------------------------------------
    {
        "task": "Compare REST vs GraphQL for a public API. How does each approach "
        "resource modeling, field selection and caching?",
        "keywords": ["REST", "GraphQL", "over-fetching", "typed schema"],
    },
    {
        "task": "Research whether REST or GraphQL is easier to cache and why clients "
        "benefit from declaring exactly which fields they need.",
        "keywords": ["HTTP verbs", "caching", "exactly which fields", "avoiding over-fetching"],
    },
    # --- Docker / Kubernetes -------------------------------------------------
    {
        "task": "Compare Docker vs Kubernetes: is it containers versus orchestration? "
        "Report what each layer handles for a production workload.",
        "keywords": ["Docker", "Kubernetes", "individual containers", "scheduling"],
    },
    {
        "task": "Research how Kubernetes adds value over plain Docker through "
        "self-healing and autoscaling for fleets of containers.",
        "keywords": ["orchestrates fleets", "self-healing", "service discovery", "autoscaling"],
    },
    # --- MongoDB / relational -------------------------------------------------
    {
        "task": "Compare MongoDB vs relational databases. Report how each handles "
        "document flexibility, horizontal scaling and joins.",
        "keywords": ["MongoDB", "BSON documents", "sharding", "relational databases"],
    },
    {
        "task": "Research the strengths of MongoDB for flexible documents versus the "
        "transactional guarantees of relational databases, and when to pick each.",
        "keywords": ["enforce schemas", "joins", "transactional guarantees", "flexible BSON"],
    },
    # --- gRPC / REST ---------------------------------------------------------
    {
        "task": "Compare gRPC vs REST for internal service communication. Report the "
        "encoding, transport and debuggability differences.",
        "keywords": ["gRPC", "REST", "HTTP/2", "protobuf"],
    },
    {
        "task": "Research why gRPC is used for low-latency RPC and where REST's textual "
        "JSON and browsability are still an advantage.",
        "keywords": ["code-generated stubs", "low-latency RPC", "textual JSON", "easier to debug"],
    },
    # --- TCP / UDP -----------------------------------------------------------
    {
        "task": "Compare TCP vs UDP transport protocols. Report the reliability and "
        "latency trade-offs of each for real-time media and DNS.",
        "keywords": ["TCP", "UDP", "reliable", "retransmission"],
    },
    {
        "task": "Research why UDP suits DNS and real-time media while TCP provides "
        "ordered byte streams via handshakes and congestion control.",
        "keywords": ["connectionless", "minimal latency", "ordered", "congestion-controlled"],
    },
    # --- Microservices / monolith --------------------------------------------
    {
        "task": "Compare microservices vs a monolith architecture. Report how each "
        "approaches independent deployment and transactions.",
        "keywords": [
            "Microservices",
            "monolith",
            "independently deployable",
            "separate data stores",
        ],
    },
    {
        "task": "Research when a monolith simplifies local development and transactions "
        "compared to splitting a system into services.",
        "keywords": ["deployable unit", "simplifying transactions", "local development"],
    },
    # --- Python / JavaScript -------------------------------------------------
    {
        "task": "Compare Python vs JavaScript for data science work. Report which "
        "ecosystem dominates analysis tooling and which is stronger for browser charts.",
        "keywords": ["Python", "JavaScript", "NumPy", "pandas"],
    },
    {
        "task": "Research the data science tooling gap: scikit-learn and D3.js sit in "
        "different camps. Summarize the trade-offs of each language.",
        "keywords": [
            "scikit-learn",
            "D3.js",
            "interactive browser visualizations",
            "full-stack sharing",
        ],
    },
    # --- JWT / session -------------------------------------------------------
    {
        "task": "Compare JWT vs session-based authentication. Report how each is "
        "verified and how hard revocation is.",
        "keywords": ["JWT", "session", "stateless signed tokens", "server-side"],
    },
    {
        "task": "Research when session auth's easy revocation beats stateless JWTs and "
        "what sticky sessions or shared stores are needed.",
        "keywords": ["revocation trivial", "sticky sessions", "shared stores", "stateless"],
    },
    # --- B-tree / LSM --------------------------------------------------------
    {
        "task": "Compare B-tree vs LSM-tree storage engines for a time-series workload. "
        "Report how each handles reads versus writes.",
        "keywords": ["B-trees", "LSM-trees", "update pages in place", "reads"],
    },
    {
        "task": "Research why LSM-tree engines favor write-heavy workloads: memtables, "
        "sorted runs and SSTables versus in-place page updates.",
        "keywords": ["memtables", "sorted runs", "SSTables", "write-heavy"],
    },
    # --- PostgreSQL + Redis stack (two sources) ------------------------------
    {
        "task": "Design a storage stack combining PostgreSQL and Redis. Compare "
        "PostgreSQL's transactional guarantees with Redis caching, and report the "
        "combined roles.",
        "keywords": ["PostgreSQL", "Redis", "ACID", "Lua scripting"],
    },
    {
        "task": "Research a web stack of React on the frontend served by a gRPC or REST "
        "API. Compare the API choices and note where React's ecosystem fits.",
        "keywords": ["React", "gRPC", "REST", "GraphQL"],
    },
    # --- Kafka + Kubernetes microservices -------------------------------------
    {
        "task": "Sketch a microservices architecture that uses Kafka for event streaming "
        "and Kubernetes for orchestration. Compare each technology's role.",
        "keywords": ["Microservices", "Kafka", "Kubernetes", "event streaming"],
    },
    {
        "task": "Research an observability and caching stack: MongoDB for documents, "
        "Redis as cache and B-tree or LSM storage trade-offs underneath.",
        "keywords": ["MongoDB", "Redis", "LSM-trees", "B-trees"],
    },
]

# Extra tool expectations shared by every research task: agents must never
# reach for a shell or a write through the governance layer.
_FORBIDDEN = ["shell.execute", "database.write"]


def _simulated_answer_text(task: str) -> str:
    """Reproduce the tool-message content a run would embed in its answer."""
    output = _web_search({"query": task})
    wrapper = {"status": "success", "output": output, "duration_ms": 0}
    return json.dumps(wrapper, ensure_ascii=False, default=str)


def build() -> list[str]:
    problems: list[str] = []
    cases: list[Case] = []
    for index, spec in enumerate(_CASES, start=1):
        task = " ".join(spec["task"].split())  # collapse whitespace
        case_id = f"research-{index:02d}"
        if _ARITHMETIC_RE.search(task):
            problems.append(
                f"{case_id}: task looks like arithmetic; mock would route to calculator"
            )
        text = _simulated_answer_text(task).lower()
        missing = [kw for kw in spec["keywords"] if kw.lower() not in text]
        if missing:
            problems.append(f"{case_id}: keywords not in simulated answer -> {missing}")
        cases.append(
            Case(
                id=case_id,
                category="research.comparison",
                task=task,
                expected_tools=["web.search"],
                forbidden_tools=list(_FORBIDDEN),
                expected_keywords=spec["keywords"],
            )
        )
    if not problems:
        dataset = Dataset(
            name="research",
            description=(
                "Research agent evaluation set: technology comparison tasks whose "
                "expected evidence is fully covered by the built-in web.search "
                "knowledge base."
            ),
            cases=cases,
        )
        dataset.to_json(OUT)
        problems.append(f"wrote {len(cases)} cases to {OUT}")
    return problems


if __name__ == "__main__":
    for message in build():
        print(message)
