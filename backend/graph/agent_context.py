from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContext:
    user_id: int