"""Combina dos motores de decisión, preservando el esquema regla+LLM original."""

from __future__ import annotations

import random
from dataclasses import replace
from typing import Any, Callable, Dict, Optional, Sequence

from .base import DecisionEngine
from .types import CitizenDecisionState, DecisionResult


class HybridEngine(DecisionEngine):
    """Usa `secondary` para una fracción `secondary_rate` de las decisiones, `primary` el resto.

    Con `parallel_secondary=True`, al inicio de cada paso (`prepare_step`) se sortean los
    ciudadanos que usarán el motor secundario y se consultan todos juntos con
    `secondary.decide_many` (en paralelo para LLM/Jev). Esos ciudadanos deciden con su
    estado al inicio del paso; el resto sigue la activación asíncrona con el primario.
    """

    def __init__(
        self,
        primary: DecisionEngine,
        secondary: DecisionEngine,
        secondary_rate: float,
        rng: Optional[random.Random] = None,
        parallel_secondary: bool = False,
    ):
        if not 0.0 <= secondary_rate <= 1.0:
            raise ValueError("secondary_rate debe estar entre 0 y 1")
        self.primary = primary
        self.secondary = secondary
        self.secondary_rate = secondary_rate
        self.rng = rng or random.Random()
        self.parallel_secondary = parallel_secondary
        self.name = f"hybrid[{primary.name}+{secondary.name}@{secondary_rate:.0%}{' ∥' if parallel_secondary else ''}]"
        self._prefetched: Optional[Dict[int, DecisionResult]] = None

    def prepare_step(self, candidates: Sequence[Any], state_of: Callable[[Any], CitizenDecisionState]) -> None:
        if not self.parallel_secondary:
            return
        selected = [state_of(c) for c in candidates if self.rng.random() < self.secondary_rate]
        results = self.secondary.decide_many(selected)
        self._prefetched = {state.agent_id: result for state, result in zip(selected, results)}

    def end_step(self) -> None:
        # Descarta decisiones de ciudadanos arrestados antes de su turno en este paso
        self._prefetched = None

    def decide(self, state: CitizenDecisionState) -> DecisionResult:
        if self._prefetched is not None:
            result = self._prefetched.pop(state.agent_id, None)
            if result is None:
                return self.primary.decide(state)
        elif self.rng.random() < self.secondary_rate:
            result = self.secondary.decide(state)
        else:
            return self.primary.decide(state)

        if result.error is not None:
            # Fallback explícito al motor primario si el secundario falla (nunca default silencioso).
            fallback = self.primary.decide(state)
            return replace(
                fallback,
                raw={"fallback_from": result.source, "original_error": result.error, "primary_raw": fallback.raw},
            )
        return result
