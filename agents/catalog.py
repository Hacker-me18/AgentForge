"""Agent catalog: the built-in agents shown in the Studio UI and used for demo runs.

Each agent is a first-class definition (id + persona + allowed capabilities +
one-click demo tasks). Under the deterministic mock LLM, ``strategy`` decides
how free-form tasks are turned into tool calls:

- ``"route"`` (default): arithmetic tasks go to ``calculator``, everything else
  to ``web.search`` (matches the offline evaluation arms);
- ``"echo"``: always calls ``mock.echo`` (legacy default behaviour).

``plan`` (a tuple of tool names) is used for agents that must always drive a
specific sequence regardless of wording — e.g. ``data-writer``, which calls the
``database.write`` tool and therefore exercises the human-approval path.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentInfo:
    agent_id: str
    name: str
    category: str
    description: str
    capabilities: tuple[str, ...] = ()
    suggested_tasks: tuple[str, ...] = ()
    strategy: str = "route"
    plan: tuple[str, ...] = ()
    badge: str = ""
    system_prompt: str = (
        "You are a helpful agent. Complete the user's task using the tools "
        "available to you, then summarise what you found."
    )

    @property
    def is_governed(self) -> bool:
        """True when the agent can trigger policy/approval on a normal run."""
        return bool(self.plan)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "suggested_tasks": list(self.suggested_tasks),
            "strategy": self.strategy,
            "plan": list(self.plan),
            "badge": self.badge,
            "governed": self.is_governed,
        }


# ---------------------------------------------------------------------------
# catalog entries
# ---------------------------------------------------------------------------

_RESEARCH_PROMPT = (
    "You are the AgentOS research agent. Given a question, search your "
    "knowledge base for authoritative material, weigh the sources you find, "
    "and answer with a short, evidence-backed comparison. Prefer tools over "
    "guessing; cite the titles you used."
)

_DATA_PROMPT = (
    "You are the AgentOS data analyst. Break user requests into computable "
    "steps, run arithmetic with the calculator, and query structured data "
    "where relevant. Always state the numbers you computed and the sources "
    "you drew on."
)

_WRITER_PROMPT = (
    "You are the AgentOS data writer. You persist notes into the local demo "
    "ledger (database.write). Because this tool mutates state it is gated by "
    "the governance layer and waits for a human decision before it runs."
)

AGENTS: tuple[AgentInfo, ...] = (
    AgentInfo(
        agent_id="research-agent",
        name="Research Agent",
        category="Research",
        description=(
            "Searches the knowledge base and answers evidence-backed "
            "comparisons (web.search / calculator)."
        ),
        capabilities=("web.search", "calculator", "document.read"),
        suggested_tasks=(
            "Compare PostgreSQL vs MySQL for a 2026 OLTP workload",
            "Redis vs Memcached: which is better for a cache tier?",
            "Kafka vs RabbitMQ for high-throughput event streaming",
            "Is GraphQL or REST a better fit for a public API in 2026?",
            "Docker vs Kubernetes — do I need both?",
            "Compute 12% of 34800 for a quarterly budget line",
        ),
        strategy="route",
        system_prompt=_RESEARCH_PROMPT,
    ),
    AgentInfo(
        agent_id="data-analyst",
        name="Data Analyst",
        category="Analytics",
        description=(
            "Runs calculations and cross-checks figures against the knowledge "
            "base before reporting numbers."
        ),
        capabilities=("calculator", "web.search", "database.read"),
        suggested_tasks=(
            "Project 5 years of growth: 1420 * 1.08^5",
            "If a cluster runs 48 pods and each costs $3.20/hr, what is the "
            "daily cost? (48 * 3.2 * 24)",
            "Cross-check B-tree vs LSM-tree trade-offs for a write-heavy time-series workload",
            "What is 245000 * 1.12 and does the knowledge base mention horizontal scaling?",
        ),
        strategy="route",
        system_prompt=_DATA_PROMPT,
    ),
    AgentInfo(
        agent_id="data-writer",
        name="Data Writer",
        category="Governance demo",
        description=(
            "Attempts a database.write and waits for a human decision — "
            "exercise the approval loop live."
        ),
        capabilities=("database.write",),
        suggested_tasks=(
            "Persist the following note to the ledger: 'approved analyst summary 2026-09'",
        ),
        plan=("database.write",),
        badge="requires human approval",
        system_prompt=_WRITER_PROMPT,
    ),
    AgentInfo(
        agent_id="default-agent",
        name="Default Agent",
        category="General",
        description=(
            "The fallback agent with the stock echo behaviour; useful for "
            "sanity checks of the run loop."
        ),
        capabilities=("mock.echo",),
        suggested_tasks=("echo back this task",),
        strategy="echo",
        system_prompt="You are AgentOS's default agent.",
    ),
)

_BY_ID: dict[str, AgentInfo] = {agent.agent_id: agent for agent in AGENTS}


def get_agent(agent_id: str) -> AgentInfo | None:
    """Return the catalog entry for ``agent_id`` (or ``None``)."""
    return _BY_ID.get(agent_id)


def all_agents() -> list[AgentInfo]:
    """Every catalog agent, in declaration order."""
    return list(AGENTS)
