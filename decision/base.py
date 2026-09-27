"""Interfaz común que deben implementar todos los motores de decisión."""

from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List, Sequence, TypeVar

from .types import CitizenDecisionState, DecisionResult

T = TypeVar("T")
R = TypeVar("R")


def map_concurrently(fn: Callable[[T], R], items: Sequence[T], max_workers: int) -> List[R]:
    """`map` con un pool de hilos, preservando el orden; pensado para llamadas de red (I/O bound)."""
    if len(items) <= 1 or max_workers <= 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        return list(pool.map(fn, items))


class DecisionEngine(ABC):
    """Decide si un ciudadano se rebela a partir de su `CitizenDecisionState`."""

    name: str = "base"
    #: True si `decide` sortea `active` a partir de `probability`; el cache re-sortea en cada hit.
    stochastic: bool = False

    @abstractmethod
    def decide(self, state: CitizenDecisionState) -> DecisionResult:
        raise NotImplementedError

    def decide_many(self, states: Sequence[CitizenDecisionState]) -> List[DecisionResult]:
        """Decide varios estados en orden; los motores de red lo redefinen para consultar en paralelo."""
        return [self.decide(state) for state in states]

    def resample(self, result: DecisionResult) -> DecisionResult:
        """Vuelve a sortear `active` desde `result.probability` (no-op para motores deterministas)."""
        return result

    def prepare_step(self, candidates: Sequence[Any], state_of: Callable[[Any], CitizenDecisionState]) -> None:
        """Hook al inicio de cada paso del modelo con los ciudadanos que pueden decidir (no-op por defecto)."""

    def end_step(self) -> None:
        """Hook al final de cada paso del modelo (no-op por defecto)."""
