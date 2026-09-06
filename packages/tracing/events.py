"""Unified event model."""

import time
import uuid

from pydantic import BaseModel, Field


class Event(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    run_id: str
    type: str
    timestamp: float = Field(default_factory=time.time)
    sequence: int = 0
    payload: dict = Field(default_factory=dict)
