"""Evaluation dataset models.

A :class:`Case` is one unit of evaluation: a task prompt plus the outcome a
well-behaved agent is expected to produce:

- ``expected_tools``    tools the agent is expected to actually execute;
- ``forbidden_tools``   tools that would be a governance slip if executed;
- ``expected_keywords`` evidence fragments (facts, names, numbers) that must
  surface in the agent's answer so the Evidence dimension can be scored.

:class:`Dataset` is an ordered, id-unique collection of cases loaded from or
written to JSON (see ``datasets/eval/research.json``).
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = REPO_ROOT / "datasets" / "eval" / "research.json"


class Case(BaseModel):
    id: str
    task: str
    category: str = "research"
    expected_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)

    def validate_core(self) -> list[str]:
        """Return a list of problems, empty when the case is well formed."""
        problems: list[str] = []
        if not self.id.strip():
            problems.append("case id must not be empty")
        if not self.task.strip():
            problems.append(f"case {self.id}: task must not be empty")
        if not self.expected_tools:
            problems.append(f"case {self.id}: expected_tools is empty")
        if not self.expected_keywords:
            problems.append(f"case {self.id}: expected_keywords is empty")
        return problems


class Dataset(BaseModel):
    name: str
    description: str = ""
    cases: list[Case] = Field(default_factory=list)

    # -- queries ---------------------------------------------------------

    def __len__(self) -> int:
        return len(self.cases)

    def by_id(self, case_id: str) -> Case | None:
        for case in self.cases:
            if case.id == case_id:
                return case
        return None

    # -- validation ------------------------------------------------------

    def validate_dataset(self) -> list[str]:
        problems: list[str] = []
        seen: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                problems.append(f"duplicate case id: {case.id}")
            seen.add(case.id)
            problems.extend(case.validate_core())
        return problems

    # -- serialization ---------------------------------------------------

    @classmethod
    def from_json(cls, path: str | Path) -> "Dataset":
        with Path(path).open(encoding="utf-8") as handle:
            return cls.model_validate(json.load(handle))

    def to_json(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            json.dump(self.model_dump(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    # -- convenience -----------------------------------------------------

    @classmethod
    def load_default(cls) -> "Dataset":
        return cls.from_json(DEFAULT_DATASET_PATH)
