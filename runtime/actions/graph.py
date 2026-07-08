"""Action graph models."""

from __future__ import annotations

from dataclasses import dataclass, field

from runtime.actions.models import Action


@dataclass(frozen=True, slots=True)
class ActionGraph:
    actions: tuple[Action, ...]
    edges: MappingEdges = field(default_factory=tuple)

    def ordered(self) -> list[Action]:
        """Return actions in execution order.

        The first implementation supports linear graphs. Edges are modeled now so DAG execution can
        be added without changing the public type.
        """

        return list(self.actions)


MappingEdges = tuple[tuple[str, str], ...]
