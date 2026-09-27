"""Motores de decisión de rebelión intercambiables para los agentes ciudadanos."""

from .base import DecisionEngine
from .factory import build_engine
from .types import CitizenDecisionState, DecisionResult, RebellionDecision

__all__ = [
    "DecisionEngine",
    "build_engine",
    "CitizenDecisionState",
    "DecisionResult",
    "RebellionDecision",
]
