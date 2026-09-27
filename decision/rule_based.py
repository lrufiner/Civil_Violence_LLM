"""Regla matemática original de Epstein, con probabilidad de arresto real."""

from __future__ import annotations

import math
import time

from .base import DecisionEngine
from .types import CitizenDecisionState, DecisionResult


class RuleBasedEngine(DecisionEngine):
    """active = (grievance - risk_aversion * arrest_probability) > threshold.

    arrest_probability = 1 - exp(-risk_constant * round(cops_visible / (actives_visible + 1))),
    como en la implementación de referencia de Mesa del Modelo 1 de Epstein (2002); el +1
    cuenta al propio ciudadano como activo.

    El `round` no figura en el artículo, pero sin él no se reproducen sus dinámicas: con
    menos policías que activos a la vista, el cociente redondea a 0 y el riesgo percibido
    desaparece, lo que permite las "explosiones" de rebelión. Con `round_ratio=False` se usa
    el cociente continuo.
    """

    name = "rule"

    def __init__(self, threshold: float, risk_constant: float, round_ratio: bool = True):
        self.threshold = threshold
        self.risk_constant = risk_constant
        self.round_ratio = round_ratio

    def _arrest_probability(self, cops_visible: int, actives_visible: int) -> float:
        ratio = cops_visible / (actives_visible + 1)
        if self.round_ratio:
            ratio = round(ratio)
        return 1 - math.exp(-self.risk_constant * ratio)

    def decide(self, state: CitizenDecisionState) -> DecisionResult:
        start = time.perf_counter()
        arrest_probability = self._arrest_probability(state.cops_visible, state.actives_visible)
        net_risk = state.risk_aversion * arrest_probability
        active = (state.grievance - net_risk) > self.threshold
        latency_ms = (time.perf_counter() - start) * 1000
        return DecisionResult(
            active=active,
            probability=1.0 if active else 0.0,
            source=self.name,
            latency_ms=latency_ms,
            confidence=1.0,
            raw={"arrest_probability": arrest_probability, "net_risk": net_risk},
        )
