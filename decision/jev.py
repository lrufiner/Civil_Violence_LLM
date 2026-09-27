"""Motor de decisión basado en Jev (TypeSafe AI, modelo "System One") vía LangChain.

Jev no genera texto: responde preguntas tipadas (Noul/Choice/Score) sobre un estado
y devuelve probabilidades calibradas. Acá se usa una pregunta `Noul` (sí/no) para
la decisión de rebelión, evitando el parsing de texto libre que usan los LLM de chat.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import replace
from typing import Any, List, NamedTuple, Optional, Sequence

from .base import DecisionEngine, map_concurrently
from .types import CitizenDecisionState, DecisionResult

logger = logging.getLogger(__name__)

_VALID_MODES = ("sample", "threshold")

# Jev no genera texto: como explicación se le hace, en la misma consulta, una pregunta
# categórica sobre qué factor pesa más, y se muestra la opción elegida con su probabilidad.
_FACTOR_CRITERIA = {
    "descontento": "Su descontento con el gobierno lo empuja a rebelarse.",
    "miedo a la policía": "El riesgo de que lo arreste la policía que tiene cerca lo frena.",
    "contagio de activos": "Ver a muchos otros rebeldes cerca lo anima a sumarse y reduce su propio riesgo.",
    "legitimidad": "Considera legítimo al gobierno, así que no tiene motivos para rebelarse.",
}

# Textos de la explicación que se muestra en la UI; la pregunta a Jev siempre va en español
_EXPLANATION_TEXTS = {
    "es": {"probability": "p(rebelión)", "factor": "factor"},
    "en": {"probability": "p(rebellion)", "factor": "factor"},
}
_FACTOR_LABELS = {
    "es": {label: label for label in _FACTOR_CRITERIA},
    "en": {
        "descontento": "grievance",
        "miedo a la policía": "fear of the police",
        "contagio de activos": "contagion from active citizens",
        "legitimidad": "legitimacy",
    },
}


class _JevReply(NamedTuple):
    """Respuesta cruda de una consulta; `error` no es None si la consulta falló."""

    probability: float
    response: Any
    latency_ms: float
    error: Optional[Exception]


class JevDecisionEngine(DecisionEngine):
    """Usa `langchain_typesafe.TypeSafeClassifier` para pedir una probabilidad de rebelión.

    La latencia está dominada por la red (~240 ms de ida y vuelta a api.typesafe.ai), así que
    `decide_many` hace las consultas en paralelo (`max_concurrency`) y después sortea en orden,
    para que la corrida siga siendo reproducible con la semilla.
    """

    stochastic = True

    def __init__(
        self,
        model: str = "jev-latest",
        mode: str = "sample",
        rng: Optional[random.Random] = None,
        max_concurrency: int = 16,
        explain: bool = True,
        language: str = "es",
    ):
        if mode not in _VALID_MODES:
            raise ValueError(f"mode debe ser uno de {_VALID_MODES}, recibido: {mode!r}")
        if language not in _EXPLANATION_TEXTS:
            raise ValueError(f"language debe ser uno de {tuple(_EXPLANATION_TEXTS)}, recibido: {language!r}")
        self.model = model
        self.mode = mode
        self.rng = rng or random.Random()
        self.max_concurrency = max_concurrency
        self.explain = explain
        self.language = language
        self.name = f"jev:{model}"

        try:
            from langchain_typesafe import Choice, Noul, TypeSafeClassifier
        except ImportError as exc:
            raise ImportError(
                "Falta instalar 'langchain-typesafe' para usar el motor Jev. "
                "Revisá requirements.txt e instalá las dependencias faltantes."
            ) from exc

        try:
            self._classifier = TypeSafeClassifier(model=model)
        except TypeError:
            # Algunas versiones del SDK no aceptan `model` en el constructor.
            self._classifier = TypeSafeClassifier()
        except Exception as exc:  # noqa: BLE001 - normalmente un ValidationError por falta de API key
            raise ValueError(
                "No se pudo inicializar TypeSafeClassifier (Jev). Verificá que TYPESAFE_API_KEY "
                "esté seteada en tu .env. Detalle original: " + str(exc)
            ) from exc

        self._noul_question = Noul(
            instructions="¿El ciudadano se rebela (pasa a protestar activamente contra el gobierno) en este turno?"
        )
        self._questions = {"rebellion": self._noul_question}
        if explain:
            self._questions["factor"] = Choice(
                instructions="¿Qué factor pesa más en la decisión de este ciudadano de rebelarse o quedarse quieto?",
                criteria=_FACTOR_CRITERIA,
            )

    @staticmethod
    def _build_state(state: CitizenDecisionState) -> str:
        """Describe el estado con escala y contexto, sin revelar la fórmula ni el umbral de Epstein.

        Con cifras sueltas ("Policías visibles: 8") Jev no sabía si eran muchos o pocos, ni que
        muchos rebeldes diluyen el riesgo de cada uno, y elegía casi siempre "miedo a la policía"
        aun con 5 rebeldes por policía a la vista.
        """
        cops, actives = state.cops_visible, state.actives_visible
        area = f"en su radio de visión (unas {state.vision_cells} celdas a su alrededor)" if state.vision_cells \
            else "a su alrededor"
        # Sin esta lectura cualitativa, el texto sobre el riesgo opacaba al descontento y Jev
        # dejaba de elegir "descontento" incluso con descontentos de ~60%
        if state.grievance >= 0.45:
            motive = "Está muy enojado con el gobierno: un descontento así empuja a rebelarse aunque haya cierto riesgo."
        elif state.grievance >= 0.2:
            motive = "Su enojo con el gobierno es real, pero moderado."
        else:
            motive = "Tiene pocos motivos de queja contra el gobierno."
        if cops == 0:
            balance = "No hay ningún policía a la vista, así que casi no corre riesgo de ser arrestado."
        elif actives == 0:
            balance = f"Si se rebela sería el único rebelde frente a {cops} policías."
        else:
            balance = f"Contándolo a él, habría {(actives + 1) / cops:.1f} rebeldes por cada policía."
        return (
            "Un ciudadano de una simulación de disturbios civiles decide si se rebela contra el gobierno. "
            f"Su descontento con el gobierno es {state.grievance:.0%} (0% = ninguno, 100% = máximo); "
            f"ya tiene en cuenta que percibe al gobierno con una legitimidad de {state.legitimacy:.0%}. {motive} "
            f"Su aversión al riesgo es {state.risk_aversion:.0%}. "
            f"{area[0].upper() + area[1:]} ve {cops} policías y {actives} ciudadanos ya rebelados. {balance} "
            "Cada policía puede arrestar a un solo rebelde por turno, así que cuantos más rebeldes hay por "
            "policía, menor es el riesgo de que lo arresten a él; si lo arrestan, puede pasar mucho tiempo preso. "
            "Rebelarse o no depende de si su descontento pesa más que el riesgo de ser arrestado, "
            "según cuánto le importa arriesgarse."
        )

    def _query(self, state: CitizenDecisionState) -> _JevReply:
        """Consulta a Jev sin sortear ni tocar `rng` (seguro para llamar desde varios hilos)."""
        start = time.perf_counter()
        try:
            response = self._classifier.invoke(
                {
                    "state": self._build_state(state),
                    "questions": self._questions,
                }
            )
            probability = response.nouls["rebellion"].noul
            return _JevReply(probability, response, (time.perf_counter() - start) * 1000, None)
        except Exception as exc:  # noqa: BLE001 - cualquier falla del proveedor no debe tumbar la simulación
            logger.warning("Error consultando Jev: %s", exc)
            return _JevReply(0.0, None, (time.perf_counter() - start) * 1000, exc)

    def _activate(self, probability: float) -> bool:
        return self.rng.random() < probability if self.mode == "sample" else probability >= 0.5

    def _to_result(self, reply: _JevReply) -> DecisionResult:
        if reply.error is not None:
            return DecisionResult.failure(self.name, reply.latency_ms, reply.error)
        active = self._activate(reply.probability)
        return DecisionResult(
            active=active,
            probability=reply.probability,
            source=self.name,
            latency_ms=reply.latency_ms,
            confidence=reply.probability if active else 1 - reply.probability,
            raw=reply.response,
            explanation=self._explanation(reply),
        )

    def _explanation(self, reply: _JevReply) -> str:
        texts = _EXPLANATION_TEXTS[self.language]
        text = f"{texts['probability']}={reply.probability:.2f}"
        factor = getattr(reply.response, "choices", {}).get("factor")
        if factor is not None:
            label = _FACTOR_LABELS[self.language].get(factor.choice, factor.choice)
            probability = factor.probabilities.get(factor.choice, factor.confidence)
            text += f" · {texts['factor']}: {label} ({probability:.0%})"
        return text

    def decide(self, state: CitizenDecisionState) -> DecisionResult:
        return self._to_result(self._query(state))

    def decide_many(self, states: Sequence[CitizenDecisionState]) -> List[DecisionResult]:
        replies = map_concurrently(self._query, states, self.max_concurrency)
        return [self._to_result(reply) for reply in replies]

    def resample(self, result: DecisionResult) -> DecisionResult:
        active = self._activate(result.probability)
        return replace(result, active=active, confidence=result.probability if active else 1 - result.probability)
