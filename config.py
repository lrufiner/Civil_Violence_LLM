"""
Archivo de configuración para la simulación Civil Violence con LLM
Contiene todos los parámetros relevantes del modelo, motores de decisión y visualización
"""

import logging
import os

try:
    from dotenv import load_dotenv

    load_dotenv()  # Carga OPENAI_API_KEY / ANTHROPIC_API_KEY / TYPESAFE_API_KEY desde .env si existe
except ImportError:
    logging.getLogger(__name__).warning(
        "python-dotenv no está instalado; las variables de entorno deben setearse manualmente."
    )

# ============================================================================
# IDIOMA DE LA INTERFAZ
# ============================================================================

# "es" (español) | "en" (inglés). Define los textos de la interfaz y el idioma en que el LLM
# justifica sus decisiones. También se puede elegir con la variable de entorno UI_LANGUAGE.
UI_LANGUAGE = os.environ.get("UI_LANGUAGE", "es")
SUPPORTED_LANGUAGES = ("es", "en")
if UI_LANGUAGE not in SUPPORTED_LANGUAGES:
    raise ValueError(f"UI_LANGUAGE debe ser uno de {SUPPORTED_LANGUAGES}, recibido: {UI_LANGUAGE!r}")

# ============================================================================
# LOGGING
# ============================================================================

LOGGING_CONFIG = {
    "level": os.environ.get("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
}


def configure_logging() -> None:
    """Configura logging una sola vez para todo el proyecto (idempotente)."""
    logging.basicConfig(level=LOGGING_CONFIG["level"], format=LOGGING_CONFIG["format"])


# ============================================================================
# MOTOR DE DECISIÓN DE REBELIÓN DE LOS CIUDADANOS
# ============================================================================

DECISION_ENGINE_CONFIG = {
    # Tipo de motor: "rule" | "llm" | "jev" | "hybrid"
    "kind": "hybrid",

    # Si kind == "hybrid": mezcla un motor primario (rápido, ej. regla) con uno
    # secundario (costoso, ej. LLM o Jev) para una fracción de los agentes.
    "hybrid": {
        "primary_kind": "rule",
        "primary_kwargs": {},
        "secondary_kind": "llm",
        "secondary_kwargs": {"provider": "ollama", "model": "phi3"},
        "secondary_rate": 0.03,  # fracción de agentes que usan el motor secundario
        # Consulta en paralelo, al inicio de cada paso, a los ciudadanos sorteados para el
        # secundario. Esos ciudadanos deciden con su estado al inicio del paso (desviación
        # menor de la activación asíncrona de Epstein); False = uno por uno, como el original.
        "parallel_secondary": True,
    },

    # Configuración usada cuando kind == "llm" (chat LLM vía LangChain)
    "llm": {
        "provider": "ollama",  # "ollama" | "openai" | "anthropic"
        "model": "phi3",
        "temperature": 0.0,
        "timeout": 10.0,
        "max_retries": 2,
        "max_concurrency": 4,  # consultas simultáneas en decide_many (Ollama local suele encolarlas)
        "language": UI_LANGUAGE,  # idioma del prompt y de la justificación ("es" | "en")
    },

    # Configuración usada cuando kind == "jev" (TypeSafe AI System One)
    "jev": {
        "model": "jev-latest",
        "mode": "sample",  # "sample" (probabilístico) | "threshold" (>=0.5)
        "max_concurrency": 16,  # consultas simultáneas; la latencia es casi toda red (~240 ms)
        "explain": True,  # suma una pregunta Choice "factor principal" en la misma consulta, para la UI
        "language": UI_LANGUAGE,  # idioma del texto que se muestra en la UI ("es" | "en")
    },

    # Cache de decisiones para motores costosos (llm/jev); nunca aplica a "rule"
    "cache": {
        "enabled": True,
        "precision": 1,  # decimales de grievance/risk_aversion/legitimacy en la clave
        "count_cap": 5,  # policías/activos visibles por encima de este valor cuentan como iguales
    },

    # Mostrar logs de cada decisión en consola
    "show_console_output": True,
}

# ============================================================================
# PARÁMETROS DEL MODELO DE SIMULACIÓN
# ============================================================================

MODEL_PARAMS = {
    # Dimensiones de la cuadrícula
    "height": 40,
    "width": 40,

    # Número de agentes ciudadanos
    "citizen_density": 0.7,  # 70% de las celdas con ciudadanos

    # Número de agentes policía
    "cop_density": 0.074,  # ~7.4% de las celdas con policías

    # Visión de los ciudadanos (radio de celdas)
    "citizen_vision": 7,

    # Visión de los policías (radio de celdas)
    "cop_vision": 7,

    # Legitimidad del gobierno percibida (0.0 a 1.0)
    # Valores bajos = más descontento
    "legitimacy": 0.82,

    # Duración máxima de sentencias de cárcel
    "max_jail_term": 1000,

    # Los agentes pueden moverse
    "movement": True,

    # Número máximo de pasos de simulación
    "max_iters": 1000,

    # Orden en que actúan los agentes en cada paso: "random" (se mezclan en cada paso, como en
    # Epstein) | "sequential" (siempre el mismo orden)
    "activation_order": "random",
}

# ============================================================================
# REGLAS DE DECISIÓN PARA AGENTES SIN LLM
# ============================================================================

AGENT_RULES = {
    # Regla de Epstein: un agente se rebela si
    # grievance - risk_aversion * arrest_probability > threshold
    # con arrest_probability = 1 - exp(-k * round(cops_visibles / (activos_visibles + 1)))
    "rebellion_threshold": 0.1,

    # Constante k de la probabilidad de arresto (2.3 da P = 0.9 con 1 policía y 1 activo a la vista)
    "risk_constant": 2.3,  # Constante k en la fórmula de riesgo
}

# ============================================================================
# CONFIGURACIÓN DE VISUALIZACIÓN
# ============================================================================

VISUALIZATION_CONFIG = {
    # Número de respuestas LLM a mostrar en el panel
    "max_llm_responses_display": 5,

    # Colores de los agentes en la visualización
    "colors": {
        "quiet_citizen": "#648FFF",      # Azul - ciudadano tranquilo
        "active_citizen": "#FE6100",     # Naranja - ciudadano activo/rebelde
        "arrested_citizen": "#000000",   # Negro - ciudadano arrestado
        "cop": "#808080",                # Gris - policía
    },

    # Símbolos para estados de agentes
    "symbols": {
        "initial": "⏸️",
        "arrested": "🔒",
        "llm_decision": "💭",
        "rule_decision": "📐",
        "jev_decision": "⚡",
        "active": "🟠",
        "quiet": "🔵",
    },
}

# ============================================================================
# PARÁMETROS DE RECOLECCIÓN DE DATOS
# ============================================================================

DATA_COLLECTION = {
    # Variables a nivel de modelo
    "model_reporters": {
        "quiet_citizens": lambda m: getattr(m, "QUIET", 0),
        "active_citizens": lambda m: getattr(m, "ACTIVE", 0),
        "jailed_citizens": lambda m: getattr(m, "ARRESTED", 0),
        "decision_calls": lambda m: len(m.performance_recorder) if hasattr(m, "performance_recorder") else 0,
        "decision_errors": lambda m: m.performance_recorder.error_count() if hasattr(m, "performance_recorder") else 0,
        "avg_decision_latency_ms": lambda m: (
            m.performance_recorder.mean_latency_ms() if hasattr(m, "performance_recorder") else 0.0
        ),
    },

    # Variables a nivel de agente
    "agent_reporters": {
        "x": lambda a: a.pos[0] if hasattr(a, "pos") and a.pos else None,
        "y": lambda a: a.pos[1] if hasattr(a, "pos") and a.pos else None,
        "state": lambda a: getattr(a, "state", None).name if hasattr(a, "state") else None,
        "jail_sentence": lambda a: getattr(a, "jail_sentence", None),
        "hardship": lambda a: getattr(a, "hardship", None),
        "risk_aversion": lambda a: getattr(a, "risk_aversion", None),
        "llm_response": lambda a: getattr(a, "llm_response", ""),
        "explanation": lambda a: a.last_decision.explanation if getattr(a, "last_decision", None) else None,
    },
}

# ============================================================================
# CONFIGURACIÓN DEL SERVIDOR SOLARA
# ============================================================================

SERVER_CONFIG = {
    # Puerto del servidor
    "port": 8765,

    # Host (localhost para acceso local)
    "host": "localhost",

    # Modo de desarrollo
    "debug": False,
}

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_total_cells():
    """Calcula el número total de celdas en la cuadrícula"""
    return MODEL_PARAMS["height"] * MODEL_PARAMS["width"]

def get_expected_citizens():
    """Calcula el número esperado de ciudadanos"""
    return int(get_total_cells() * MODEL_PARAMS["citizen_density"])

def get_expected_cops():
    """Calcula el número esperado de policías"""
    return int(get_total_cells() * MODEL_PARAMS["cop_density"])

def get_secondary_decisions_per_step():
    """Estima cuántas decisiones por paso van al motor secundario (solo kind == "hybrid")."""
    return int(get_expected_citizens() * DECISION_ENGINE_CONFIG["hybrid"]["secondary_rate"])

def print_config_summary():
    """Imprime un resumen de la configuración"""
    print("=" * 70)
    print("CONFIGURACIÓN DE LA SIMULACIÓN CIVIL VIOLENCE CON LLM")
    print("=" * 70)
    print(f"\n📊 MODELO:")
    print(f"   Cuadrícula: {MODEL_PARAMS['width']}x{MODEL_PARAMS['height']} = {get_total_cells()} celdas")
    print(f"   Ciudadanos esperados: ~{get_expected_citizens()}")
    print(f"   Policías esperados: ~{get_expected_cops()}")
    print(f"   Legitimidad del gobierno: {MODEL_PARAMS['legitimacy']:.0%}")
    print(f"   Visión ciudadanos: {MODEL_PARAMS['citizen_vision']} celdas")
    print(f"   Visión policías: {MODEL_PARAMS['cop_vision']} celdas")

    kind = DECISION_ENGINE_CONFIG["kind"]
    llm_cfg = DECISION_ENGINE_CONFIG["llm"]
    print(f"\n🤖 MOTOR DE DECISIÓN: {kind}")
    if kind == "hybrid":
        hybrid_cfg = DECISION_ENGINE_CONFIG["hybrid"]
        print(f"   Primario: {hybrid_cfg['primary_kind']} | Secundario: {hybrid_cfg['secondary_kind']} "
              f"{hybrid_cfg['secondary_kwargs']}")
        print(f"   Tasa secundario: {hybrid_cfg['secondary_rate']:.1%} (~{get_secondary_decisions_per_step()} por paso)")
    elif kind == "llm":
        print(f"   Proveedor/modelo: {llm_cfg['provider']}:{llm_cfg['model']} | Timeout: {llm_cfg['timeout']}s")
    elif kind == "jev":
        print(f"   Modelo: {DECISION_ENGINE_CONFIG['jev']['model']} | Modo: {DECISION_ENGINE_CONFIG['jev']['mode']}")
    print(f"   Cache: {'sí' if DECISION_ENGINE_CONFIG['cache']['enabled'] else 'no'}")

    print(f"\n📐 REGLAS:")
    print(f"   Rebelión si: descontento - aversión_riesgo * P(arresto) > {AGENT_RULES['rebellion_threshold']}")
    print(f"   Constante de riesgo: {AGENT_RULES['risk_constant']}")

    print(f"\n🌐 SERVIDOR:")
    print(f"   URL: http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
    print(f"   Debug: {SERVER_CONFIG['debug']}")
    print("=" * 70)

# ============================================================================
# NOTAS Y DOCUMENTACIÓN
# ============================================================================

NOTES = """
NOTAS SOBRE LA CONFIGURACIÓN:

1. DECISION_ENGINE_CONFIG["kind"]:
   - "rule": regla de Epstein, instantánea y determinista
   - "llm" / "jev": todos los ciudadanos consultan al proveedor (lento/costoso)
   - "hybrid": regla para la mayoría y el motor secundario para `secondary_rate`

2. SECONDARY_RATE (hybrid):
   - 0.01-0.05 permite ver decisiones LLM/Jev sin ralentizar la simulación
   - 1.0 equivale a usar solo el motor secundario (muy lento)

3. LEGITIMACY:
   - Valores bajos (0.0-0.5): Alto descontento, más rebelión
   - Valores altos (0.8-1.0): Bajo descontento, menos rebelión
   - El descontento (grievance) se calcula como: hardship * (1 - legitimacy)

4. REBELLION_THRESHOLD:
   - Valores más altos: menos rebelión
   - Valores más bajos: más rebelión

5. CACHE:
   - Reutiliza decisiones de LLM/Jev para estados redondeados a `precision` decimales
   - Menor precisión = más hits de cache y menos llamadas pagas

RENDIMIENTO:
- Con ~1100 ciudadanos y 3% hybrid: ~33 decisiones secundarias por step (menos con cache)
- Cada consulta LLM toma ~0.5-2 segundos con phi3 local
"""

if __name__ == "__main__":
    print_config_summary()
    print(NOTES)
