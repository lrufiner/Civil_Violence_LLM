import logging

import mesa
import pandas as pd

from agents import (
    CitizenLLM,
    CitizenState,
    Cop,
)
from config import AGENT_RULES, DATA_COLLECTION, DECISION_ENGINE_CONFIG, MODEL_PARAMS, configure_logging
from decision.factory import build_engine
from decision.hybrid import HybridEngine
from decision.rule_based import RuleBasedEngine
from metrics.collector import PerformanceRecorder

configure_logging()
logger = logging.getLogger(__name__)


# Nombres en español que muestra la UI para los motores; internamente se usan los identificadores en inglés
KIND_ALIASES = {"regla": "rule", "híbrido": "hybrid"}


def _normalize_kind(kind: str) -> str:
    return KIND_ALIASES.get(kind, kind)


class ThreadSafeDataCollector(mesa.DataCollector):
    """DataCollector que tolera lecturas concurrentes con `collect()`.

    SolaraViz (Mesa >= 3.5) ejecuta `model.step()` en un hilo aparte mientras los
    gráficos leen `get_model_vars_dataframe()`. Como `collect()` agrega una columna
    por vez, una lectura a mitad de camino ve listas de distinto largo y pandas falla
    con "All arrays must be of the same length". Acá se descarta la fila incompleta.
    """

    def get_model_vars_dataframe(self):
        columns = {name: list(values) for name, values in self.model_vars.items()}
        complete_rows = min((len(values) for values in columns.values()), default=0)
        return pd.DataFrame({name: values[:complete_rows] for name, values in columns.items()})


class EpsteinCivilViolenceLLM(mesa.Model):
    """
    Modelo 1 del artículo "Modeling civil violence: An agent-based computational approach" de Joshua Epstein.
    https://www.pnas.org/content/99/suppl_3/7243.full

    Parámetros:
        height: altura de la grilla
        width: ancho de la grilla
        citizen_density: porcentaje aproximado de celdas ocupadas por ciudadanos
        cop_density: porcentaje aproximado de celdas ocupadas por policías
        citizen_vision: número de celdas en cada dirección (N, S, E y O) que el ciudadano puede inspeccionar
        cop_vision: número de celdas en cada dirección que el policía puede inspeccionar
        legitimacy: percepción de legitimidad del régimen por parte de los ciudadanos (L), igual para todos
        max_jail_term: sentencia máxima de cárcel (J_max)
        active_threshold: si (grievance - (risk_aversion * arrest_probability)) > threshold, el ciudadano se rebela
        arrest_prob_constant: constante para estimar probabilidad de arresto de forma plausible
        movement: binario, indica si los agentes intentan moverse al final del paso
        max_iters: número máximo de iteraciones (el modelo puede no tener punto de parada natural)
    """

    def __init__(
        self,
        width=MODEL_PARAMS["width"],
        height=MODEL_PARAMS["height"],
        citizen_density=MODEL_PARAMS["citizen_density"],
        cop_density=MODEL_PARAMS["cop_density"],
        citizen_vision=MODEL_PARAMS["citizen_vision"],
        cop_vision=MODEL_PARAMS["cop_vision"],
        legitimacy=MODEL_PARAMS["legitimacy"],
        max_jail_term=MODEL_PARAMS["max_jail_term"],
        active_threshold=AGENT_RULES["rebellion_threshold"],
        arrest_prob_constant=AGENT_RULES["risk_constant"],
        movement=MODEL_PARAMS["movement"],
        max_iters=MODEL_PARAMS["max_iters"],
        activation_order=MODEL_PARAMS["activation_order"],
        seed=None,
        decision_engine=None,
        decision_kind=None,
        llm_provider=None,
        llm_model=None,
        jev_model=None,
        secondary_kind=None,
        secondary_rate=None,
    ):
        try:
            seed = int(seed) if seed not in (None, "") else None
        except (TypeError, ValueError):
            seed = None

        if not 0.0 <= legitimacy <= 1.0:
            raise ValueError("legitimacy debe estar entre 0.0 y 1.0")
        if citizen_vision <= 0 or cop_vision <= 0:
            raise ValueError("citizen_vision y cop_vision deben ser positivos")
        if max_iters <= 0:
            raise ValueError("max_iters debe ser positivo")
        if cop_density + citizen_density > 1:
            raise ValueError("La densidad de policías + ciudadanos debe ser menor a 1")
        if activation_order not in ("random", "sequential"):
            raise ValueError("activation_order debe ser 'random' o 'sequential'")

        # rng=entero siembra model.random igual que el `seed` deprecado de Mesa
        super().__init__(rng=seed)
        self.movement = movement
        self.activation_order = activation_order
        self.max_iters = max_iters
        # self.steps ya lo inicializa mesa.Model.__init__ (y lo autoincrementa en cada step)

        # Almacenar parámetros ajustables para actualización dinámica
        self.legitimacy = legitimacy
        self.max_jail_term = max_jail_term
        self.citizen_vision = citizen_vision
        self.cop_vision = cop_vision
        self.active_threshold = active_threshold
        self.arrest_prob_constant = arrest_prob_constant

        self._engine_overrides = {
            "kind": decision_kind,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "jev_model": jev_model,
            "secondary_kind": secondary_kind,
            "secondary_rate": secondary_rate,
        }

        self.performance_recorder = PerformanceRecorder()
        self.decision_engine = decision_engine or build_engine(rng=self.random, **self._resolve_engine_spec())
        self._sync_decision_engine_params()

        self.grid = mesa.discrete_space.OrthogonalVonNeumannGrid(
            (width, height), capacity=1, torus=True, random=self.random
        )

        self.datacollector = ThreadSafeDataCollector(
            model_reporters=DATA_COLLECTION["model_reporters"],
            agent_reporters=DATA_COLLECTION["agent_reporters"],
        )

        # Inicialización de agentes en la grilla
        for cell in self.grid.all_cells:
            klass = self.random.choices(
                [CitizenLLM, Cop, None],
                cum_weights=[citizen_density, citizen_density + cop_density, 1],
            )[0]

            if klass == Cop:
                cop = Cop(self, vision=cop_vision, max_jail_term=max_jail_term)
                cop.move_to(cell)
            elif klass == CitizenLLM:
                citizen = CitizenLLM(self, vision=citizen_vision)
                citizen.move_to(cell)

        self.running = True
        self._update_counts()
        self.datacollector.collect(self)

    def _resolve_engine_spec(self) -> dict:
        """Combina DECISION_ENGINE_CONFIG con los overrides pasados al constructor."""
        overrides = self._engine_overrides
        kind = _normalize_kind(overrides["kind"] or DECISION_ENGINE_CONFIG["kind"])
        cache_cfg = DECISION_ENGINE_CONFIG["cache"]
        spec = {
            "kind": kind,
            "cache": cache_cfg["enabled"],
            "cache_precision": cache_cfg["precision"],
            "cache_count_cap": cache_cfg.get("count_cap"),
        }

        if kind in ("rule", "llm", "jev"):
            spec.update(self._engine_kwargs(kind))
        elif kind == "hybrid":
            hybrid_cfg = dict(DECISION_ENGINE_CONFIG["hybrid"])
            hybrid_cfg["primary_kwargs"] = self._engine_kwargs(
                hybrid_cfg["primary_kind"], hybrid_cfg.get("primary_kwargs", {})
            )
            # Los secondary_kwargs de config solo aplican si el secundario no fue cambiado desde la UI
            secondary_kind = _normalize_kind(overrides["secondary_kind"] or hybrid_cfg["secondary_kind"])
            configured_kwargs = (
                hybrid_cfg.get("secondary_kwargs", {}) if secondary_kind == hybrid_cfg["secondary_kind"] else {}
            )
            hybrid_cfg["secondary_kind"] = secondary_kind
            hybrid_cfg["secondary_kwargs"] = self._engine_kwargs(secondary_kind, configured_kwargs)
            if overrides["secondary_rate"] is not None:
                hybrid_cfg["secondary_rate"] = overrides["secondary_rate"]
            spec.update(hybrid_cfg)
        else:
            raise ValueError(f"DECISION_ENGINE_CONFIG['kind'] inválido: {kind!r}")
        return spec

    def _engine_kwargs(self, kind: str, configured: dict | None = None) -> dict:
        """kwargs de un motor simple: config global < `configured` (ej. hybrid.*_kwargs) < overrides de UI."""
        overrides = self._engine_overrides
        if kind == "rule":
            return {"threshold": self.active_threshold, "risk_constant": self.arrest_prob_constant, **(configured or {})}
        if kind == "llm":
            ui = {"provider": overrides["llm_provider"], "model": overrides["llm_model"]}
        elif kind == "jev":
            ui = {"model": overrides["jev_model"]}
        else:
            raise ValueError(f"Motor inválido: {kind!r}")
        kwargs = {**DECISION_ENGINE_CONFIG[kind], **(configured or {})}
        kwargs.update({k: v for k, v in ui.items() if v})
        return kwargs

    def _sync_decision_engine_params(self):
        """Propaga en vivo active_threshold/arrest_prob_constant al motor de regla (sliders)."""
        candidates = [self.decision_engine]
        if isinstance(self.decision_engine, HybridEngine):
            candidates.extend([self.decision_engine.primary, self.decision_engine.secondary])
        for engine in candidates:
            if isinstance(engine, RuleBasedEngine):
                engine.threshold = self.active_threshold
                engine.risk_constant = self.arrest_prob_constant

    def step(self):
        """
        Avanza el modelo un paso y recolecta datos.

        Nota: no incrementar `self.steps` acá; Mesa >= 3.3 ya lo hace automáticamente
        en `Model._wrapped_step` antes de invocar este método (ver `mesa.Model.__init__`).
        """
        self._sync_decision_engine_params()
        free_citizens = [c for c in self.agents_by_type.get(CitizenLLM, []) if c.jail_sentence == 0]
        self.decision_engine.prepare_step(free_citizens, CitizenLLM.decision_state)
        try:
            if self.activation_order == "random":
                # Activación asíncrona en orden aleatorio, como Epstein y la referencia de Mesa
                self.agents.shuffle_do("step")
            else:
                for agent in self.agents:
                    agent.step()
        finally:
            self.decision_engine.end_step()

        self._update_counts()
        self.datacollector.collect(self)

        if self.steps > self.max_iters:
            self.running = False

    def _update_counts(self):
        """
        Función auxiliar para contar el número de ciudadanos en cada estado.
        """
        citizen_table = self.agents_by_type.get(CitizenLLM)
        counts = citizen_table.groupby("state").count() if citizen_table is not None else {}

        for state in CitizenState:
            setattr(self, state.name, counts.get(state, 0))
