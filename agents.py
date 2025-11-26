
#import Agent

from enum import Enum

import mesa

import subprocess
import random
from typing import Optional
from config import LLM_CONFIG, AGENT_RULES, VISUALIZATION_CONFIG

class CitizenState(Enum):
    ACTIVE = 1
    QUIET = 2
    ARRESTED = 3

def consultar_llm(prompt: str, model: Optional[str] = None, max_tokens: Optional[int] = None):
    """
    Consulta al LLM con un límite de tokens en la respuesta.
    Usa configuración de config.py si no se especifican parámetros.
    """
    if model is None:
        model = LLM_CONFIG["model"]
    if max_tokens is None:
        max_tokens = LLM_CONFIG["max_response_tokens"]
    
    try:
        prompt_mejorado = f"{prompt}\n\nRespuesta (máximo {max_tokens} palabras):"

        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt_mejorado.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=LLM_CONFIG["timeout"],
        )

        if result.returncode != 0:
            if LLM_CONFIG["show_console_output"]:
                print(
                    f"Error al consultar LLM (code {result.returncode}): {result.stderr.decode('utf-8').strip()}"
                )
            return "no"

        output = result.stdout.decode("utf-8").strip().lower()

        palabras = output.split()
        if len(palabras) > max_tokens:
            output = " ".join(palabras[:max_tokens])

        return output or "no"
    except Exception as e:
        if LLM_CONFIG["show_console_output"]:
            print(f"Error al consultar LLM: {e}")
        return "no"

class EpsteinAgent(mesa.discrete_space.CellAgent):
    def __init__(self, model):
        super().__init__(model)
        self.vision = 7  # Valor por defecto
        
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
    def __init__(self, model, grievance=None, risk_aversion=None, vision=7):
        super().__init__(model)
        self.vision = vision
        # Almacenar hardship (privación) como valor fijo
        self.hardship = random.uniform(0, 1)
        # risk_aversion también es fijo
        self.risk_aversion = risk_aversion if risk_aversion is not None else random.uniform(0, 1)
        self.active = False
        self.jail_sentence = 0
        self.state = CitizenState.QUIET  # Estado inicial
        self.llm_response = f"{VISUALIZATION_CONFIG['symbols']['initial']} Initial"  # Almacena la última respuesta del LLM
    
    @property
    def grievance(self):
        """
        Calcula grievance dinámicamente basado en la legitimacy actual del modelo.
        grievance = hardship × (1 - legitimacy)
        """
        return self.hardship * (1 - self.model.legitimacy)

    def step(self):
        if self.jail_sentence > 0:
            self.jail_sentence -= 1
            self.active = False
            self.state = CitizenState.ARRESTED
            self.llm_response = f"{VISUALIZATION_CONFIG['symbols']['arrested']} Arrested"
            return
        
        # Actualizar visión si cambió en el modelo
        if hasattr(self.model, 'citizen_vision'):
            self.vision = self.model.citizen_vision

        # Usar LLM solo para una pequeña muestra de agentes (configurable)
        use_llm = random.random() < LLM_CONFIG["llm_usage_rate"]
        
        if use_llm:
            # Convert values to percentages for prompt
            grievance_pct = int(self.grievance * 100)
            risk_aversion_pct = int(self.risk_aversion * 100)
            
            # Use prompt template from configuration
            prompt = LLM_CONFIG["prompt_template"].format(
                grievance_pct=grievance_pct,
                risk_aversion_pct=risk_aversion_pct
            )

            respuesta = consultar_llm(prompt)
            
            # Print to console if enabled
            if LLM_CONFIG["show_console_output"]:
                print(f"🤖 Agent {self.unique_id} | G:{grievance_pct}% R:{risk_aversion_pct}% | LLM responded: '{respuesta}'")
            
            self.llm_response = f"{VISUALIZATION_CONFIG['symbols']['llm_decision']} LLM: {respuesta[:20]}"  # Mark that it used LLM
            
            # Detect affirmative response using keywords from configuration
            respuesta_lower = respuesta.lower()
            self.active = any(keyword in respuesta_lower for keyword in LLM_CONFIG["affirmative_keywords"])
            if self.model is not None:
                self.model.llm_calls += 1
        else:
            # Most agents use simple mathematical rule (faster)
            threshold = AGENT_RULES["rebellion_threshold"]
            self.active = self.grievance > (self.risk_aversion + threshold)
            decision = "yes" if self.active else "no"
            self.llm_response = f"{VISUALIZATION_CONFIG['symbols']['rule_decision']} Rule: {decision}"
        
        # Update state according to decision
        if self.active:
            self.state = CitizenState.ACTIVE
        else:
            self.state = CitizenState.QUIET

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
        # Actualizar visión y max_jail_term si cambiaron en el modelo
        if hasattr(self.model, 'cop_vision'):
            self.vision = self.model.cop_vision
        if hasattr(self.model, 'max_jail_term'):
            self.max_jail_term = self.model.max_jail_term
            
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
