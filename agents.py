"""Agentes del modelo Epstein de disturbios civiles con decisión de rebelión enchufable."""

from enum import Enum

import mesa

from config import DECISION_ENGINE_CONFIG, UI_LANGUAGE, VISUALIZATION_CONFIG
from decision.types import CitizenDecisionState

INITIAL_RESPONSE = f"{VISUALIZATION_CONFIG['symbols']['initial']} Initial"
ARRESTED_RESPONSE = f"{VISUALIZATION_CONFIG['symbols']['arrested']} Arrested"


class CitizenState(Enum):
    ACTIVE = 1
    QUIET = 2
    ARRESTED = 3


def _symbol_for_source(source: str) -> str:
    """Elige el símbolo de UI según qué motor de decisión produjo el resultado."""
    symbols = VISUALIZATION_CONFIG["symbols"]
    if source == "rule":
        return symbols["rule_decision"]
    if source.startswith("llm:"):
        return symbols["llm_decision"]
    if source.startswith("jev:"):
        return symbols["jev_decision"]
    return "❓"

class EpsteinAgent(mesa.discrete_space.CellAgent):
    def __init__(self, model):
        super().__init__(model)
        self.vision = 7  # Valor por defecto

    def update_neighbors(self):
        """
        Look around and see who my neighbors are
        """
        self.neighborhood = self.cell.get_neighborhood(radius=self.vision)
        # list(): en Mesa 3.5 `.agents` es un iterador de una sola pasada; contar policías lo
        # agotaba y los activos visibles daban siempre 0
        self.neighbors = list(self.neighborhood.agents)
        self.empty_neighbors = [c for c in self.neighborhood if c.is_empty]

    def move(self):
        if self.model.movement and self.empty_neighbors:
            new_pos = self.random.choice(self.empty_neighbors)
            self.move_to(new_pos)

class CitizenLLM(EpsteinAgent):
    def __init__(self, model, risk_aversion=None, vision=7):
        super().__init__(model)
        self.vision = vision
        # hardship y risk_aversion son fijos; se usa self.random (sembrado por el modelo) para reproducibilidad
        self.hardship = self.random.uniform(0, 1)
        self.risk_aversion = risk_aversion if risk_aversion is not None else self.random.uniform(0, 1)
        self.jail_sentence = 0
        self.state = CitizenState.QUIET
        self.neighbors = []
        self.llm_response = INITIAL_RESPONSE  # Última decisión tomada
        self.last_decision = None  # DecisionResult completo de la última decisión
        self.last_decision_step = None

    @property
    def active(self) -> bool:
        return self.state == CitizenState.ACTIVE

    @property
    def grievance(self):
        """
        Calcula grievance dinámicamente basado en la legitimacy actual del modelo.
        grievance = hardship × (1 - legitimacy)
        """
        return self.hardship * (1 - self.model.legitimacy)

    def _visible_counts(self):
        """Cuenta cops y ciudadanos activos en el vecindario visible (fórmula de Epstein)."""
        cops_visible = sum(1 for a in self.neighbors if isinstance(a, Cop))
        actives_visible = sum(1 for a in self.neighbors if isinstance(a, CitizenLLM) and a.active)
        return cops_visible, actives_visible

    def decision_state(self) -> CitizenDecisionState:
        """Observa el vecindario actual y arma el estado que recibe el motor de decisión."""
        # La visión puede cambiar en vivo desde la UI
        self.vision = self.model.citizen_vision
        self.update_neighbors()
        cops_visible, actives_visible = self._visible_counts()
        return CitizenDecisionState(
            agent_id=self.unique_id,
            hardship=self.hardship,
            risk_aversion=self.risk_aversion,
            legitimacy=self.model.legitimacy,
            grievance=self.grievance,
            cops_visible=cops_visible,
            actives_visible=actives_visible,
            vision_cells=len(self.neighborhood),
        )

    def step(self):
        if self.jail_sentence > 0:
            self.jail_sentence -= 1
            self.state = CitizenState.ARRESTED
            self.llm_response = ARRESTED_RESPONSE
            return

        result = self.model.decision_engine.decide(self.decision_state())
        self.model.performance_recorder.record(self.model.steps, self.unique_id, result)

        if DECISION_ENGINE_CONFIG["show_console_output"] and result.source != "rule":
            print(
                f"{_symbol_for_source(result.source)} Agent {self.unique_id} | "
                f"{result.source} | active={result.active} p={result.probability:.2f}"
                + (f" | {result.explanation}" if result.explanation else "")
                + (f" | ERROR: {result.error}" if result.error else "")
            )

        self.last_decision = result
        self.last_decision_step = self.model.steps

        self.state = CitizenState.ACTIVE if result.active else CitizenState.QUIET
        # Regla de movimiento M de Epstein: después de decidir, moverse a una celda vacía a la vista
        self.move()
        decision_txt = ("sí" if UI_LANGUAGE == "es" else "yes") if result.active else "no"
        self.llm_response = (
            f"{_symbol_for_source(result.source)} {result.source}: {decision_txt} (p={result.probability:.2f})"
        )

class Cop(EpsteinAgent):
    """
    A cop for life.  No defection.
    Summary of rule: Inspect local vision and arrest a random active agent.

    Attributes:
        unique_id: unique int
        x, y: Grid coordinates
        vision: number of cells in each direction (N, S, E and W) that cop is
            able to inspect
    """

    def __init__(self, model, vision, max_jail_term):
        """
        Create a new Cop.
        Args:
            x, y: Grid coordinates
            vision: number of cells in each direction (N, S, E and W) that
                agent can inspect. Exogenous.
            model: model instance
        """
        super().__init__(model)
        self.vision = vision
        self.max_jail_term = max_jail_term

    def step(self):
        """
        Inspect local vision and arrest a random active agent. Move if
        applicable.
        """
        # Visión y max_jail_term pueden cambiar en vivo desde la UI
        self.vision = self.model.cop_vision
        self.max_jail_term = self.model.max_jail_term

        self.update_neighbors()
        active_neighbors = [a for a in self.neighbors if isinstance(a, CitizenLLM) and a.active]
        if active_neighbors:
            arrestee = self.random.choice(active_neighbors)
            arrestee.jail_sentence = self.random.randint(0, self.max_jail_term)
            arrestee.state = CitizenState.ARRESTED

        self.move()
