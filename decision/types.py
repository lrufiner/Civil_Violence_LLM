"""Tipos compartidos por todos los motores de decisión de agentes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, Field


@dataclass
class CitizenDecisionState:
    """Estado observado por un ciudadano al momento de decidir si rebelarse."""

    agent_id: int
    hardship: float
    risk_aversion: float
    legitimacy: float
    grievance: float
    cops_visible: int
    actives_visible: int
    #: Celdas dentro del radio de visión (da escala a los conteos); None si no se conoce
    vision_cells: Optional[int] = None


@dataclass
class DecisionResult:
    """Resultado normalizado devuelto por cualquier `DecisionEngine`."""

    active: bool
    probability: float
    source: str
    latency_ms: float
    confidence: Optional[float] = None
    raw: Any = None
    error: Optional[str] = None
    from_cache: bool = False
    #: Texto breve para la UI: justificación del LLM o factor principal según Jev
    explanation: Optional[str] = None

    @classmethod
    def failure(cls, source: str, latency_ms: float, error: Exception) -> "DecisionResult":
        """Resultado inactivo que registra la falla de un proveedor externo sin tumbar la simulación."""
        return cls(active=False, probability=0.0, source=source, latency_ms=latency_ms, error=str(error))


class RebellionDecision(BaseModel):
    """Salida estructurada exigida a un LLM de chat (evita parsear texto libre)."""

    active: bool = Field(description="True si el ciudadano decide rebelarse, False si se queda quieto")
    confidence: float = Field(ge=0.0, le=1.0, description="Confianza del modelo en su propia decisión, de 0 a 1")
    reason: str = Field(
        default="",
        description="Justificación breve de la decisión, en primera persona y en el idioma del prompt (máximo 15 palabras)",
    )
