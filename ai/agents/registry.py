"""
Agent Registry

Each agent registers itself here with:
  - name:        short identifier used by the orchestrator to route
  - description: one sentence explaining what requests this agent handles
  - run:         async callable (llm, user_input) -> str

To add a new agent, just append an entry to AGENTS — the orchestrator
will discover it automatically.
"""
from dataclasses import dataclass
from typing import Callable, Awaitable


@dataclass
class AgentEntry:
    name: str
    description: str
    run: Callable[..., Awaitable[str]]


# ── Registry ──────────────────────────────────────────────────────────────────
# Populated at the bottom of this file. Order does not matter.

AGENTS: list[AgentEntry] = []


def register(name: str, description: str):
    """Decorator that registers an async function as an agent."""
    def decorator(fn: Callable[..., Awaitable[str]]):
        AGENTS.append(AgentEntry(name=name, description=description, run=fn))
        return fn
    return decorator
