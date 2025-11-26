"""
Archivo de configuración para la simulación Civil Violence con LLM
Contiene todos los parámetros relevantes del modelo, LLM y visualización
"""

# ============================================================================
# CONFIGURACIÓN DEL LLM (Large Language Model)
# ============================================================================

LLM_CONFIG = {
    # Modelo de Ollama a utilizar
    "model": "phi3",
    
    # Porcentaje de agentes que consultan al LLM (0.01 = 1%)
    # El resto usa reglas matemáticas simples
    "llm_usage_rate": 0.03,
    
    # Máximo de palabras en la respuesta del LLM
    "max_response_tokens": 6,
    
    # Timeout para llamadas al LLM (segundos)
    "timeout": 10,
    
    # Prompt usado para consultar al LLM
    "prompt_template": (
        "Descontento: {grievance_pct}%, Aversión al riesgo: {risk_aversion_pct}%. "
        "¿Rebelarse? Responde SOLO: sí o no, sin explicaciones."
    ),
    
    # Palabras clave para detectar respuesta afirmativa
    "affirmative_keywords": ["sí", "si", "yes", "s"],
    
    # Mostrar respuestas del LLM en consola
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
    
    # Tasa de reemplazo de agentes (K en el modelo original)
    # Controla cuántos arrestados/activos son reemplazados por agentes tranquilos
    "max_iters": 1000,
}

# ============================================================================
# REGLAS DE DECISIÓN PARA AGENTES SIN LLM
# ============================================================================

AGENT_RULES = {
    # Regla simple: un agente se rebela si:
    # grievance > (risk_aversion + threshold)
    "rebellion_threshold": 0.1,
    
    # Fórmula de riesgo percibido:
    # arrest_probability = 1 - exp(-k * (cops_visible / (actives_visible + 1)))
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
        "llm_calls": lambda m: getattr(m, "llm_calls", 0),
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

def get_llm_agents_per_step():
    """Calcula cuántos agentes aproximadamente usarán LLM por paso"""
    return int(get_expected_citizens() * LLM_CONFIG["llm_usage_rate"])

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
    
    print(f"\n🤖 LLM:")
    print(f"   Modelo: {LLM_CONFIG['model']}")
    print(f"   Tasa de uso: {LLM_CONFIG['llm_usage_rate']:.1%} de agentes")
    print(f"   Agentes con LLM por paso: ~{get_llm_agents_per_step()}")
    print(f"   Máx. palabras respuesta: {LLM_CONFIG['max_response_tokens']}")
    print(f"   Timeout: {LLM_CONFIG['timeout']}s")
    
    print(f"\n📐 REGLAS:")
    print(f"   Rebelión si: descontento > (aversión_riesgo + {AGENT_RULES['rebellion_threshold']})")
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

1. LLM_USAGE_RATE:
   - 0.01 (1%) permite ver ejemplos de LLM sin ralentizar la simulación
   - Para más ejemplos de LLM, aumentar a 0.05 (5%) o 0.10 (10%)
   - 1.0 (100%) haría que todos los agentes usen LLM (muy lento)

2. LEGITIMACY:
   - Valores bajos (0.0-0.5): Alto descontento, más rebelión
   - Valores altos (0.8-1.0): Bajo descontento, menos rebelión
   - El descontento (grievance) se calcula como: hardship * (1 - legitimacy)

3. REBELLION_THRESHOLD:
   - Ajusta la sensibilidad de la decisión de rebelarse
   - Valores más altos: menos rebelión
   - Valores más bajos: más rebelión

4. PROMPT_TEMPLATE:
   - Debe ser conciso para obtener respuestas rápidas
   - Incluye {grievance_pct} y {risk_aversion_pct} como placeholders
   - Instrucciones claras ayudan a obtener respuestas "sí/no"

5. MAX_RESPONSE_TOKENS:
   - Limita la longitud de la respuesta del LLM
   - Valores pequeños (1-3) = respuestas más rápidas
   - Valores grandes pueden generar textos extensos

RENDIMIENTO:
- Con ~1100 ciudadanos y 1% LLM: ~11 consultas LLM por step
- Cada consulta LLM toma ~0.5-2 segundos con phi3
- Total por step: ~5-20 segundos (aceptable para simulación interactiva)
"""

if __name__ == "__main__":
    print_config_summary()
    print(NOTES)
