import mesa

from agents import (
    CitizenLLM,
    CitizenState,
    Cop,
)
from config import MODEL_PARAMS, DATA_COLLECTION

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
        width=40,
        height=40,
        citizen_density=0.7,
        cop_density=0.074,
        citizen_vision=7,
        cop_vision=7,
        legitimacy=0.8,
        max_jail_term=1000,
        active_threshold=0.1,
        arrest_prob_constant=2.3,
        movement=True,
        max_iters=1000,
        seed=None,
    ):
        super().__init__(seed=seed)
        self.movement = movement
        self.max_iters = max_iters
        self.steps = 0
        self._agent_counter = 0
        
        # Almacenar parámetros ajustables para actualización dinámica
        self.legitimacy = legitimacy
        self.max_jail_term = max_jail_term
        self.citizen_vision = citizen_vision
        self.cop_vision = cop_vision

        self.grid = mesa.discrete_space.OrthogonalVonNeumannGrid(
            (width, height), capacity=1, torus=True, random=self.random
        )

        model_reporters = {
            "active": CitizenState.ACTIVE.name,
            "quiet": CitizenState.QUIET.name,
            "arrested": CitizenState.ARRESTED.name,
        }
        agent_reporters = {
            "jail_sentence": lambda a: getattr(a, "jail_sentence", None),
            "arrest_probability": lambda a: getattr(a, "arrest_probability", None),
            "llm_response": lambda a: getattr(a, "llm_response", ""),
        }
        self.datacollector = mesa.DataCollector(
            model_reporters=model_reporters, agent_reporters=agent_reporters
        )

        if cop_density + citizen_density > 1:
            raise ValueError("La densidad de policías + ciudadanos debe ser menor a 1")

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

    def step(self):
        """
        Avanza el modelo un paso y recolecta datos.
        """
        self.steps += 1
        for agent in self.agents:
            agent.step()

        self._update_counts()
        self.datacollector.collect(self)

        if self.steps > self.max_iters:
            self.running = False

    def _update_counts(self):
        """
        Función auxiliar para contar el número de ciudadanos en cada estado.
        """
        counts = self.agents_by_type[CitizenLLM].groupby("state").count()

        for state in CitizenState:
            setattr(self, state.name, counts.get(state, 0))