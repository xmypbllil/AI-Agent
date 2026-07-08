"""Minimal dependency injection container."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar, cast

T = TypeVar("T")


@dataclass(slots=True)
class ServiceContainer:
    """Small explicit service container for runtime composition."""

    _instances: dict[str, object] = field(default_factory=dict)
    _factories: dict[str, Callable[["ServiceContainer"], object]] = field(default_factory=dict)

    def register_instance(self, key: str, instance: object) -> None:
        self._instances[key] = instance

    def register_factory(self, key: str, factory: Callable[["ServiceContainer"], object]) -> None:
        self._factories[key] = factory

    def resolve(self, key: str, expected_type: type[T] | None = None) -> T:
        if key not in self._instances:
            factory = self._factories.get(key)
            if factory is None:
                raise KeyError(f"Service is not registered: {key}")
            self._instances[key] = factory(self)

        instance = self._instances[key]
        if expected_type is not None and not isinstance(instance, expected_type):
            raise TypeError(f"Service {key!r} is not {expected_type.__name__}")
        return cast(T, instance)

    def namespace(self) -> dict[str, Any]:
        return dict(self._instances)
