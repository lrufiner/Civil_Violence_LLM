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
from mesa.visualization.utils import update_counter
import solara
from config import AGENT_RULES, DECISION_ENGINE_CONFIG, MODEL_PARAMS, VISUALIZATION_CONFIG
from decision.cache import CachedDecisionEngine
from decision.hybrid import HybridEngine
import ui_mesa
from ui_texts import T  # textos en el idioma de config.UI_LANGUAGE

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

    # ~1 celda de la grilla de 40x40 en la figura de 5.6" (con 200 los puntos se pisaban)
    portrayal = AgentPortrayalStyle(size=60)

    if isinstance(agent, CitizenLLM):
        portrayal.update(("color", agent_colors[agent.state]))
    elif isinstance(agent, Cop):
        portrayal.update(("color", COP_COLOR))

    return portrayal


def post_process(ax):
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    # Tamaño pensado para la celda del layout (ver LAYOUT): 560 px a 100 dpi
    ax.get_figure().set_size_inches(5.6, 5.6)


# Claves = columnas reales de DATA_COLLECTION["model_reporters"] en config.py; valores = leyenda
SERIES_GRAFICO = T["series"]


def chart_post_process(ax):
    for line, label in zip(ax.get_lines(), SERIES_GRAFICO.values()):
        line.set_label(label)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_xlabel(T["x_axis"])
    # Mesa llama a ax.set_xlabel("Step") después del post_process; se anula solo en este eje
    ax.set_xlabel = lambda *args, **kwargs: None
    ax.set_ylabel(T["y_axis"])
    # Con un solo punto (paso 0) matplotlib centra el eje en 0 y muestra valores negativos
    lines = ax.get_lines()
    last_step = len(lines[0].get_xdata()) - 1 if lines else 0
    ax.set_xlim(0, max(1, last_step))
    ax.get_figure().set_size_inches(5.8, 3.0)
    ax.get_figure().tight_layout()


# Nombres de los motores en el selector (el modelo acepta los alias en español, ver model.KIND_ALIASES)
KIND_OPTIONS = T["kind_options"]

# Parámetros iniciales (panel izquierdo): se aplican al reiniciar el modelo
model_params = {
    "seed": {
        "type": "InputText",
        "value": "42",
        "label": T["seed"],
    },
    "height": MODEL_PARAMS["height"],
    "width": MODEL_PARAMS["width"],
    "citizen_density": Slider(T["citizen_density"], MODEL_PARAMS["citizen_density"], 0.1, 0.9, 0.1),
    # step 0.001: el default de Epstein (0.074) no es múltiplo de 0.01 y el slider lo redondeaba a 0.07
    "cop_density": Slider(T["cop_density"], MODEL_PARAMS["cop_density"], 0.0, 0.15, 0.001),
    "citizen_vision": Slider(T["citizen_vision"], MODEL_PARAMS["citizen_vision"], 1, 10, 1),
    "cop_vision": Slider(T["cop_vision"], MODEL_PARAMS["cop_vision"], 1, 10, 1),
    "legitimacy": Slider(T["legitimacy"], MODEL_PARAMS["legitimacy"], 0.0, 1.0, 0.01),
    "max_jail_term": Slider(T["max_jail_term"], MODEL_PARAMS["max_jail_term"], 0, 1000, 50),
    "active_threshold": Slider(T["active_threshold"], AGENT_RULES["rebellion_threshold"], 0.0, 1.0, 0.01),
    "arrest_prob_constant": Slider(T["arrest_prob_constant"], AGENT_RULES["risk_constant"], 0.1, 5.0, 0.1),
    "decision_kind": {
        "type": "Select",
        "value": KIND_OPTIONS[DECISION_ENGINE_CONFIG["kind"]],
        "values": list(KIND_OPTIONS.values()),
        "label": T["decision_kind"],
    },
    "secondary_kind": {
        "type": "Select",
        "value": DECISION_ENGINE_CONFIG["hybrid"]["secondary_kind"],
        "values": ["llm", "jev"],
        "label": T["secondary_kind"],
    },
    "secondary_rate": Slider(T["secondary_rate"], DECISION_ENGINE_CONFIG["hybrid"]["secondary_rate"], 0.0, 0.2, 0.01),
    "llm_provider": {
        "type": "Select",
        "value": DECISION_ENGINE_CONFIG["llm"]["provider"],
        "values": ["ollama", "openai", "anthropic"],
        "label": T["llm_provider"],
    },
}

# Estilo común: cada panel ocupa exactamente su celda del layout y hace scroll si no entra
PANEL_STYLE = {"height": "100%", "overflow-y": "auto", "padding": "4px 12px"}
SMALL = {"font-size": "0.85em"}
MUTED = {"font-size": "0.8em", "color": "#777"}


def _labeled_slider(slider, label, **kwargs):
    """Label arriba del slider: en línea, los labels largos lo aplastan en pantallas angostas."""
    solara.Text(label, style={"font-size": "0.9em", "margin-top": "4px"})
    slider("", **kwargs)


@solara.component
def DynamicControls(model):
    """Parámetros que se aplican en vivo, sin reiniciar la simulación."""
    legitimacy = solara.use_reactive(model.legitimacy)
    citizen_vision = solara.use_reactive(model.citizen_vision)
    cop_vision = solara.use_reactive(model.cop_vision)
    max_jail_term = solara.use_reactive(model.max_jail_term)
    active_threshold = solara.use_reactive(model.active_threshold)
    arrest_prob_constant = solara.use_reactive(model.arrest_prob_constant)

    def update_model():
        model.legitimacy = legitimacy.value
        model.citizen_vision = citizen_vision.value
        model.cop_vision = cop_vision.value
        model.max_jail_term = max_jail_term.value
        model.active_threshold = active_threshold.value
        model.arrest_prob_constant = arrest_prob_constant.value

    solara.use_effect(update_model, [legitimacy.value, citizen_vision.value,
                                     cop_vision.value, max_jail_term.value,
                                     active_threshold.value, arrest_prob_constant.value])

    with solara.Card(T["live_title"], elevation=1, style=PANEL_STYLE):
        with solara.Columns([1, 1]):
            with solara.Column(gap="0px"):
                # step=0.01 como el slider inicial: un paso más grueso redondearía (y cambiaría) el valor del modelo
                _labeled_slider(solara.SliderFloat, T["live_legitimacy"].format(value=legitimacy.value),
                                value=legitimacy, min=0.0, max=1.0, step=0.01)
                _labeled_slider(solara.SliderInt, T["live_citizen_vision"].format(value=citizen_vision.value),
                                value=citizen_vision, min=1, max=10)
                _labeled_slider(solara.SliderInt, T["live_cop_vision"].format(value=cop_vision.value),
                                value=cop_vision, min=1, max=10)
            with solara.Column(gap="0px"):
                _labeled_slider(solara.SliderInt, T["live_jail"].format(value=max_jail_term.value),
                                value=max_jail_term, min=0, max=1000, step=50)
                _labeled_slider(solara.SliderFloat, T["live_threshold"].format(value=active_threshold.value),
                                value=active_threshold, min=0.0, max=1.0, step=0.01)
                _labeled_slider(solara.SliderFloat, T["live_k"].format(value=arrest_prob_constant.value),
                                value=arrest_prob_constant, min=0.1, max=5.0, step=0.1)


def describe_engine(engine) -> str:
    """Descripción legible del motor activo (engine.name es un identificador técnico)."""
    if isinstance(engine, HybridEngine):
        return T["engine_hybrid"].format(
            primary=describe_engine(engine.primary),
            secondary=describe_engine(engine.secondary),
            rate=engine.secondary_rate,
            parallel=T["engine_parallel"] if engine.parallel_secondary else "",
        )
    if isinstance(engine, CachedDecisionEngine):
        return T["engine_cached"].format(inner=describe_engine(engine.inner))
    name = engine.name
    if name == "rule":
        return T["engine_rule"]
    if name.startswith("llm:"):
        return f"LLM {name.split(':', 1)[1]}"
    if name.startswith("jev:"):
        return f"Jev ({name.split(':', 1)[1]})"
    return name


def _source_label(source: str) -> str:
    return T["rule_source"] if source == "rule" else source


def performance_table(model):
    # Función común (no @solara.component): se dibuja dentro de DecisionsPanel y se refresca con él
    recorder = model.performance_recorder
    solara.Text(T["engine_label"].format(engine=describe_engine(model.decision_engine)), style=SMALL)
    rows = "\n".join(
        f"| {_source_label(source)} | {s.decisions:,} | {s.cache_hits / s.decisions:.0%} | {s.errors} | "
        + (f"{s.mean_latency_ms:,.0f} ms |" if s.mean_latency_ms >= 1 else f"{s.mean_latency_ms:.3f} ms |")
        for source, s in recorder.by_source().items()
    )
    if rows:
        solara.Markdown(T["table_header"] + "\n|---|---:|---:|---:|---:|\n" + rows, style={"font-size": "0.85em"})
    else:
        solara.Text(T["no_decisions_yet"], style=MUTED)


def recent_decisions(model):
    symbols = VISUALIZATION_CONFIG["symbols"]
    state_symbol = {
        CitizenState.ACTIVE: symbols["active"],
        CitizenState.QUIET: symbols["quiet"],
        CitizenState.ARRESTED: symbols["arrested"],
    }
    # Solo decisiones LLM/Jev tomadas en el último paso; las de la regla no tienen texto
    decided = [
        agent for agent in model.agents_by_type.get(CitizenLLM, [])
        if agent.last_decision is not None
        and agent.last_decision_step == model.steps
        and agent.last_decision.source != "rule"
    ]
    max_responses = VISUALIZATION_CONFIG.get("max_llm_responses_display", 5)
    solara.Text(T["decisions_in_step"].format(step=model.steps, count=len(decided),
                                              shown=min(len(decided), max_responses)), style=MUTED)

    for agent in decided[-max_responses:]:
        result = agent.last_decision
        with solara.Column(gap="0px", style={"border-left": "3px solid #ccc", "padding": "2px 0 2px 8px",
                                              "margin": "6px 0"}):
            solara.Text(T["citizen_line"].format(
                symbol=state_symbol[agent.state], id=agent.unique_id,
                decision=T["rebels"] if result.active else T["stays_quiet"],
                p=result.probability, source=result.source,
                cache=T["from_cache"] if result.from_cache else "",
            ), style=SMALL)
            if result.explanation:
                # Los LLM chicos (phi3) no siempre respetan el límite de palabras; el texto completo queda en el CSV
                text = result.explanation if len(result.explanation) <= 160 else result.explanation[:157] + "..."
                solara.Text(f"“{text}”", style={**SMALL, "font-style": "italic"})
            solara.Text(T["citizen_traits"].format(grievance=agent.grievance, risk=agent.risk_aversion),
                        style=MUTED)

    if not decided:
        solara.Text(T["press_play"] if model.steps == 0 else T["none_this_step"], style=MUTED)


def pending_changes_warning(model):
    """Avisa que hay cambios del panel izquierdo que Mesa recién aplica al tocar Reiniciar."""
    pending = sorted(ui_mesa.parametros_pendientes.value)
    if pending:
        names = ", ".join(f"«{label}»" for label in pending)
        solara.Warning(T["pending"].format(names=names, engine=describe_engine(model.decision_engine)),
                       dense=True)


@solara.component
def DecisionsPanel(model):
    """Desempeño por motor y últimas decisiones LLM/Jev con su justificación."""
    # SolaraViz solo envuelve con auto-refresh las funciones comunes; un @solara.component
    # debe suscribirse explícitamente al contador de pasos para redibujarse en cada step.
    update_counter.get()
    # Un modelo nuevo (Reiniciar) ya incluye los parámetros pendientes: se limpia el aviso
    solara.use_effect(lambda: ui_mesa.parametros_pendientes.set(frozenset()), [id(model)])
    with solara.Card(T["decisions_title"], elevation=1, style=PANEL_STYLE):
        pending_changes_warning(model)
        with solara.Columns([1, 1]):
            with solara.Column():
                solara.Text(T["performance_title"], style={"font-weight": "bold"})
                performance_table(model)
            with solara.Column():
                solara.Text(T["justifications_title"], style={"font-weight": "bold"})
                recent_decisions(model)


@solara.component
def AboutPanel(model):
    """Descripción breve de la simulación para quien abre la aplicación por primera vez."""
    with solara.Card(T["about_title"], elevation=1, style=PANEL_STYLE):
        solara.Markdown(T["about"], style={"font-size": "0.9em"})


@solara.component
def HelpPanel(model):
    """Pestaña "Cómo funciona": fórmulas de Epstein y cómo deciden el LLM y Jev."""
    with solara.Card(T["help_title"], elevation=1, style=PANEL_STYLE):
        solara.Markdown(T["help"], style={"font-size": "0.95em"})


chart_component = make_plot_component(
    {column: agent_colors[state] for column, state in zip(
        SERIES_GRAFICO, (CitizenState.QUIET, CitizenState.ACTIVE, CitizenState.ARRESTED)
    )},
    post_process=chart_post_process,
)

# Grilla de 12 columnas con filas de 30 px (+10 px de margen): alto en px = 40*h - 10.
# Pestaña 1, orden = [mapa (lo agrega SolaraViz), gráfico, ajustes en vivo, decisiones, acerca de]
LAYOUT = [
    {"i": 0, "x": 0, "y": 6, "w": 6, "h": 15, "moved": False},   # mapa
    {"i": 1, "x": 6, "y": 6, "w": 6, "h": 8, "moved": False},    # gráfico
    {"i": 2, "x": 6, "y": 14, "w": 6, "h": 7, "moved": False},   # ajustes en vivo
    {"i": 3, "x": 0, "y": 21, "w": 12, "h": 13, "moved": False},  # decisiones
    {"i": 4, "x": 0, "y": 0, "w": 12, "h": 6, "moved": False},   # acerca de (arriba de todo)
]
# Pestaña 2: la ayuda ocupa todo el ancho
HELP_LAYOUT = [{"i": 0, "x": 0, "y": 0, "w": 12, "h": 52, "moved": False}]


def _param_label(options) -> str:
    return options.label if isinstance(options, Slider) else options.get("label", "")


ui_mesa.instalar(
    textos=T["mesa_texts"],
    nombres_vistas=T["page_names"],
    formato_paso=f"{T['x_axis']}: {{}}",
    layouts={len(LAYOUT): LAYOUT, len(HELP_LAYOUT): HELP_LAYOUT},
    parametros_iniciales={_param_label(o) for o in model_params.values() if isinstance(o, (Slider, dict))},
)


def make_renderer(model):
    renderer = SpaceRenderer(model, backend="matplotlib")
    renderer.setup_agents(citizen_cop_portrayal)
    renderer.draw_agents()
    renderer.post_process = post_process
    return renderer


@solara.component
def Page():
    # Un modelo por sesión del navegador: con un modelo a nivel de módulo, todas las pestañas
    # arrancaban del mismo objeto (y una podía avanzar la simulación de otra).
    model = solara.use_memo(EpsteinCivilViolenceLLM, dependencies=[])
    renderer = solara.use_memo(lambda: make_renderer(model), dependencies=[model])
    SolaraViz(
        model,
        renderer,
        components=[
            chart_component,  # make_plot_component ya devuelve (componente, pestaña 0)
            (DynamicControls, 0), (DecisionsPanel, 0), (AboutPanel, 0),
            (HelpPanel, 1),
        ],
        model_params=model_params,
        name=T["app_name"],
    )
