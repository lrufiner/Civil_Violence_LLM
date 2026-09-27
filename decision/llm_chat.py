"""Motor de decisión basado en un LLM de chat (OpenAI/Anthropic/Ollama) vía LangChain."""

from __future__ import annotations

import logging
import time
from typing import Any, List, Optional, Sequence

from llm.providers import get_chat_model

from .base import DecisionEngine, map_concurrently
from .types import CitizenDecisionState, DecisionResult, RebellionDecision

logger = logging.getLogger(__name__)

# El idioma del prompt define también el idioma de la justificación (`reason`) que muestra la UI
PROMPT_TEMPLATES = {
    "es": (
        "Sos un ciudadano en una simulación de disturbios civiles (modelo de Epstein).\n"
        "Descontento (grievance): {grievance_pct}%.\n"
        "Aversión al riesgo: {risk_aversion_pct}%.\n"
        "Policías visibles: {cops_visible}. Ciudadanos activos visibles: {actives_visible}.\n"
        "Decidí si te rebelás (active=true) o te quedás quieto (active=false), "
        "indicá tu confianza en esa decisión (0 a 1) "
        "y justificala en una frase breve en primera persona, en español (reason, máximo 15 palabras)."
    ),
    "en": (
        "You are a citizen in a civil violence simulation (Epstein's model).\n"
        "Grievance: {grievance_pct}%.\n"
        "Risk aversion: {risk_aversion_pct}%.\n"
        "Visible cops: {cops_visible}. Visible active citizens: {actives_visible}.\n"
        "Decide whether you rebel (active=true) or stay quiet (active=false), "
        "state your confidence in that decision (0 to 1) "
        "and justify it in one short first-person sentence, in English (reason, at most 15 words)."
    ),
}
DEFAULT_PROMPT_TEMPLATE = PROMPT_TEMPLATES["es"]


class LLMChatEngine(DecisionEngine):
    """Consulta un LLM de chat con salida estructurada (sin parsing de texto libre)."""

    def __init__(
        self,
        provider: str,
        model: str,
        prompt_template: Optional[str] = None,
        temperature: float = 0.0,
        timeout: float = 10.0,
        max_retries: int = 2,
        max_concurrency: int = 4,
        language: str = "es",
        **extra_kwargs: Any,
    ):
        self.provider = provider
        self.model_name = model
        self.name = f"llm:{provider}:{model}"
        if language not in PROMPT_TEMPLATES:
            raise ValueError(f"language debe ser uno de {tuple(PROMPT_TEMPLATES)}, recibido: {language!r}")
        self.prompt_template = prompt_template or PROMPT_TEMPLATES[language]
        self.max_concurrency = max_concurrency
        try:
            chat_model = get_chat_model(
                provider, model, temperature=temperature, timeout=timeout, max_retries=max_retries, **extra_kwargs
            )
        except ImportError:
            raise  # mensaje de instalación ya armado en get_chat_model
        except Exception as exc:  # noqa: BLE001 - normalmente falta la API key del proveedor
            raise ValueError(
                f"No se pudo inicializar el proveedor '{provider}'. Verificá que la API key "
                f"correspondiente esté seteada en tu .env. Detalle original: {exc}"
            ) from exc
        self._structured_model = chat_model.with_structured_output(RebellionDecision)

    def decide(self, state: CitizenDecisionState) -> DecisionResult:
        prompt = self.prompt_template.format(
            grievance_pct=int(state.grievance * 100),
            risk_aversion_pct=int(state.risk_aversion * 100),
            cops_visible=state.cops_visible,
            actives_visible=state.actives_visible,
        )
        start = time.perf_counter()
        try:
            decision: RebellionDecision = self._structured_model.invoke(prompt)
            latency_ms = (time.perf_counter() - start) * 1000
            probability = decision.confidence if decision.active else 1 - decision.confidence
            return DecisionResult(
                active=decision.active,
                probability=probability,
                source=self.name,
                latency_ms=latency_ms,
                confidence=decision.confidence,
                raw=decision,
                explanation=decision.reason.strip() or None,
            )
        except Exception as exc:  # noqa: BLE001 - cualquier falla del proveedor no debe tumbar la simulación
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning("Error consultando %s: %s", self.name, exc)
            return DecisionResult.failure(self.name, latency_ms, exc)

    def decide_many(self, states: Sequence[CitizenDecisionState]) -> List[DecisionResult]:
        # Sin estado aleatorio propio: se puede paralelizar `decide` directamente
        return map_concurrently(self.decide, states, self.max_concurrency)
