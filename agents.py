
#import Agent

from enum import Enum

import mesa

import subprocess
import json
import random

class CitizenState(Enum):
    ACTIVE = 1
    QUIET = 2
    ARRESTED = 3

def consultar_llm(prompt, model="phi3"):
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        output = result.stdout.decode("utf-8").strip().lower()
        return output
    except Exception as e:
        print(f"Error al consultar LLM: {e}")
        return "no"

class EpsteinAgent(mesa.discrete_space.CellAgent):
    def update_neighbors(self):
        """
        Look around and see who my neighbors are
        """
        self.neighborhood = self.cell.get_neighborhood(radius=self.vision)
        self.neighbors = self.neighborhood.agents
        self.empty_neighbors = [c for c in self.neighborhood if c.is_empty]

    def move(self):
        if self.model.movement and self.empty_neighbors:
            new_pos = self.random.choice(self.empty_neighbors)
            self.move_to(new_pos)

class CitizenLLM(EpsteinAgent):
    def __init__(self, unique_id, model, grievance=None, risk_aversion=None):
        super().__init__(unique_id, model)
        self.grievance = grievance if grievance is not None else random.uniform(0, 1)
        self.risk_aversion = risk_aversion if risk_aversion is not None else random.uniform(0, 1)
        self.active = False
        self.jail_sentence = 0

    def step(self):
        if self.jail_sentence > 0:
            self.jail_sentence -= 1
            self.active = False
            return

        prompt = (
            #Una opción en español:
            #f"Soy un ciudadano con un nivel de descontento de {self.grievance:.2f} "
            #f"y una aversión al riesgo de {self.risk_aversion:.2f}. "
            #Otra opción en español:
            "Eres ciudadano de un país que está sufriendo violencia civil. Eres un miembro de la población general, "
            f"puedes o no estar en rebelión activa. En general, si sufres más de {self.grievance:.2f}, más tendencia tienes a volverte activo. "
            f"y si tienes más de {self.risk_aversion:.2f} tiendes a evitar el riesgo. "
            "¿Debería rebelarme contra el régimen? Responde solo con 'sí' o 'no'."
        )

        respuesta = consultar_llm(prompt)
        self.active = "sí" in respuesta or "si" in respuesta

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
        self.update_neighbors()
        active_neighbors = []
        for agent in self.neighbors:
            if isinstance(agent, CitizenLLM) and agent.state == CitizenState.ACTIVE:
                active_neighbors.append(agent)
        if active_neighbors:
            arrestee = self.random.choice(active_neighbors)
            arrestee.jail_sentence = self.random.randint(0, self.max_jail_term)
            arrestee.state = CitizenState.ARRESTED

        self.move()