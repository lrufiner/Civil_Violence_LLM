import warnings
# Suprimir advertencias de hooks de Solara
warnings.filterwarnings("ignore", category=UserWarning, module="solara.validate_hooks")

from agents import (
    CitizenLLM,
    CitizenState,
    Cop,
)
from model import EpsteinCivilViolenceLLM
from mesa.visualization import (
    Slider,
    SolaraViz,
    SpaceRenderer,
    make_plot_component,
)
from mesa.visualization.components import AgentPortrayalStyle
import solara
from config import MODEL_PARAMS, VISUALIZATION_CONFIG

# Usar colores de configuración
COP_COLOR = VISUALIZATION_CONFIG["colors"]["cop"]

agent_colors = {
    CitizenState.ACTIVE: VISUALIZATION_CONFIG["colors"]["active_citizen"],
    CitizenState.QUIET: VISUALIZATION_CONFIG["colors"]["quiet_citizen"],
    CitizenState.ARRESTED: VISUALIZATION_CONFIG["colors"]["arrested_citizen"],
}


def citizen_cop_portrayal(agent):
    if agent is None:
        return

    portrayal = AgentPortrayalStyle(size=200)

    if isinstance(agent, CitizenLLM):
        # Determinar el estado basado en las propiedades del agente
        if agent.jail_sentence > 0:
            color = agent_colors[CitizenState.ARRESTED]
        elif agent.active:
            color = agent_colors[CitizenState.ACTIVE]
        else:
            color = agent_colors[CitizenState.QUIET]
        
        portrayal.update(("color", color))
    elif isinstance(agent, Cop):
        portrayal.update(("color", COP_COLOR))

    return portrayal


def post_process(ax):
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.get_figure().set_size_inches(10, 10)


# Initial model parameters (left panel - restart the model)
model_params = {
    "seed": {
        "type": "InputText",
        "value": 42,
        "label": "Random Seed",
    },
    "height": MODEL_PARAMS["height"],
    "width": MODEL_PARAMS["width"],
    "citizen_density": Slider(
        "Initial Agent Density", 
        MODEL_PARAMS["citizen_density"], 
        0.1, 0.9, 0.1
    ),
    "cop_density": Slider(
        "Initial Cop Density", 
        MODEL_PARAMS["cop_density"], 
        0.0, 0.15, 0.01
    ),
    "citizen_vision": Slider(
        "Citizen Vision", 
        MODEL_PARAMS["citizen_vision"], 
        1, 10, 1
    ),
    "cop_vision": Slider(
        "Cop Vision", 
        MODEL_PARAMS["cop_vision"], 
        1, 10, 1
    ),
    "legitimacy": Slider(
        "Government Legitimacy", 
        MODEL_PARAMS["legitimacy"], 
        0.0, 1.0, 0.01
    ),
    "max_jail_term": Slider(
        "Max Jail Term", 
        MODEL_PARAMS["max_jail_term"], 
        0, 1000, 50
    ),
}


@solara.component
def DynamicControls(model):
    """Compact controls that update the model live without restarting"""
    
    # Reactive states for each parameter
    legitimacy = solara.use_reactive(model.legitimacy)
    citizen_vision = solara.use_reactive(model.citizen_vision)
    cop_vision = solara.use_reactive(model.cop_vision)
    max_jail_term = solara.use_reactive(model.max_jail_term)
    
    # Function to update model when values change
    def update_model():
        model.legitimacy = legitimacy.value
        model.citizen_vision = citizen_vision.value
        model.cop_vision = cop_vision.value
        model.max_jail_term = max_jail_term.value
    
    # Update model when values change
    solara.use_effect(update_model, [legitimacy.value, citizen_vision.value, 
                                     cop_vision.value, max_jail_term.value])
    
    with solara.Card("⚙️ Live Settings (no restart)", elevation=1, 
                     style={"margin": "10px 0", "padding": "8px"}):
        solara.Text("Real-time changes:", 
                   style={"color": "#666", "font-size": "0.8em", "margin-bottom": "5px"})
        
        # Controles más compactos
        with solara.Column(style={"gap": "5px"}):
            solara.SliderFloat(
                f"🏛️ Legitimacy: {legitimacy.value:.2f}",
                value=legitimacy,
                min=0.0,
                max=1.0,
                step=0.05,
            )
            
            solara.SliderInt(
                f"👁️ Citizen Vision: {citizen_vision.value}",
                value=citizen_vision,
                min=1,
                max=10,
            )
            
            solara.SliderInt(
                f"🚔 Cop Vision: {cop_vision.value}",
                value=cop_vision,
                min=1,
                max=10,
            )
            
            solara.SliderInt(
                f"⚖️ Jail Term: {max_jail_term.value}",
                value=max_jail_term,
                min=0,
                max=1000,
                step=100,
            )


@solara.component
def LLMResponsesDisplay(model):
    """Compact component to display LLM responses"""
    with solara.Card("💭 LLM (last 3)", elevation=1, 
                     style={"margin": "10px 0", "padding": "8px"}):
        # Get all citizens with LLM responses
        responses = []
        total_citizens = 0
        
        if hasattr(model, 'agents'):
            try:
                for agent in model.agents:
                    if isinstance(agent, CitizenLLM):
                        total_citizens += 1
                        if hasattr(agent, 'llm_response') and agent.llm_response:
                            # Only exclude initial placeholder responses
                            if agent.llm_response not in ["⏸️ Initial", "⚫ Arrested"]:
                                estado = "🟠" if agent.active else "🔵"
                                if agent.jail_sentence > 0:
                                    estado = "⚫"
                                # Add agent ID, grievance and risk info
                                agent_id = agent.unique_id
                                g = int(agent.grievance * 100)
                                r = int(agent.risk_aversion * 100)
                                info = f"#{agent_id} G:{g}% R:{r}%"
                                responses.append((estado, agent.llm_response, info))
            except Exception as e:
                solara.Text(f"⚠️ Error: {str(e)}", style={"color": "red", "font-size": "0.7em"})
        
        # Show compact debug info
        solara.Text(f"👥 {total_citizens} | 💬 {len(responses)}", 
                   style={"color": "#666", "font-size": "0.7em", "margin-bottom": "5px"})
        
        # Show only last 3 responses (more compact)
        if responses:
            recent = responses[-3:] if len(responses) > 3 else responses
            for item in recent:
                if len(item) == 3:
                    estado, respuesta, info = item
                    # Shorten response if too long (extract only important part)
                    resp_short = respuesta[:35] + "..." if len(respuesta) > 35 else respuesta
                    solara.Text(f"{estado} {resp_short}", 
                               style={"font-size": "0.75em", "margin": "2px 0"})
                    solara.Text(f"   {info}", 
                               style={"font-size": "0.65em", "margin": "0 0 3px 0", "color": "#888"})
        else:
            if total_citizens > 0:
                solara.Text("⏸️ Press Play to see responses", style={"color": "#666", "font-size": "0.75em"})
            else:
                solara.Text("🤔 Initializing...", style={"color": "#666", "font-size": "0.75em"})


chart_component = make_plot_component(
    {state.name.lower(): agent_colors[state] for state in CitizenState}
)

epstein_model = EpsteinCivilViolenceLLM()
renderer = SpaceRenderer(epstein_model, backend="matplotlib")
renderer.draw_agents(citizen_cop_portrayal)
renderer.post_process = post_process

page = SolaraViz(
    epstein_model,
    renderer,
    components=[chart_component, DynamicControls],
    model_params=model_params,
    name="Epstein Civil Violence (LLM) - Dynamic Parameters",
)
page  # noqa
