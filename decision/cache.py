"""Cachea decisiones para estados equivalentes, pensado para motores costosos (LLM/Jev)."""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional, Sequence, Tuple

from .base import DecisionEngine
from .types import CitizenDecisionState, DecisionResult

CacheKey = Tuple[float, float, float, int, int]


def _cache_key(state: CitizenDecisionState, precision: int, count_cap: Optional[int] = None) -> CacheKey:
    cops, actives = state.cops_visible, state.actives_visible
    if count_cap is not None:
        cops, actives = min(cops, count_cap), min(actives, count_cap)
    return (
        round(state.grievance, precision),
        round(state.risk_aversion, precision),
        round(state.legitimacy, precision),
        cops,
        actives,
    )


class CachedDecisionEngine(DecisionEngine):
    """Envuelve otro motor y reutiliza la respuesta para estados redondeados equivalentes.

    Reduce llamadas repetidas a proveedores de pago (LLM chat / Jev) en corridas largas,
    donde muchos ciudadanos comparten grievance/risk_aversion/legitimacy similares.
    `count_cap` agrupa los conteos de policías/activos visibles por encima de ese valor.

    Si el motor interno es estocástico (Jev en modo "sample") se cachea la probabilidad
    y cada hit vuelve a sortear `active`, para no fijar un único resultado por estado.
    """

    def __init__(
        self,
        inner: DecisionEngine,
        precision: int = 2,
        max_size: int = 10_000,
        count_cap: Optional[int] = None,
    ):
        self.inner = inner
        self.precision = precision
        self.count_cap = count_cap
        self.max_size = max_size
        self.name = f"cached({inner.name})"
        self._cache: Dict[CacheKey, DecisionResult] = {}
        self.hits = 0
        self.misses = 0

    def _key(self, state: CitizenDecisionState) -> CacheKey:
        return _cache_key(state, self.precision, self.count_cap)

    def _hit(self, cached: DecisionResult) -> DecisionResult:
        self.hits += 1
        result = replace(cached, from_cache=True, latency_ms=0.0)
        return self.inner.resample(result) if self.inner.stochastic is True else result

    def _store(self, key: CacheKey, result: DecisionResult) -> None:
        if result.error is not None:
            return
        if len(self._cache) >= self.max_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = result

    def decide(self, state: CitizenDecisionState) -> DecisionResult:
        key = self._key(state)
        cached = self._cache.get(key)
        if cached is not None:
            return self._hit(cached)

        self.misses += 1
        result = self.inner.decide(state)
        self._store(key, result)
        return result

    def decide_many(self, states: Sequence[CitizenDecisionState]) -> List[DecisionResult]:
        """Resuelve hits del cache y consulta una sola vez por clave faltante (en lote)."""
        results: List[Optional[DecisionResult]] = [None] * len(states)
        pending: Dict[CacheKey, List[int]] = {}
        for i, state in enumerate(states):
            key = self._key(state)
            cached = self._cache.get(key)
            if cached is not None:
                results[i] = self._hit(cached)
            else:
                pending.setdefault(key, []).append(i)

        if pending:
            self.misses += len(pending)
            fresh = self.inner.decide_many([states[indices[0]] for indices in pending.values()])
            for (key, indices), result in zip(pending.items(), fresh):
                self._store(key, result)
                results[indices[0]] = result
                for i in indices[1:]:
                    results[i] = self._hit(result) if result.error is None else result
        return results  # type: ignore[return-value]
