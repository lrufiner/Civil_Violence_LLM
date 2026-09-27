# 📋 Guía de Configuración

Este archivo explica cómo personalizar la simulación usando `config.py`.

## 🎯 Configuración Rápida

Para cambiar parámetros de la simulación, edita `config.py`:

### Idioma de la interfaz

```python
UI_LANGUAGE = "es"  # "es" (español) | "en" (inglés)
```

Define todos los textos de la interfaz, incluida la pestaña **Cómo funciona**, y el idioma en que el LLM justifica sus decisiones: el prompt se arma en ese idioma. También se puede elegir sin tocar el archivo, con la variable de entorno `UI_LANGUAGE`:

```bash
# Linux/Mac
UI_LANGUAGE=en .venv/bin/python -m solara run app.py
# Windows (PowerShell)
$env:UI_LANGUAGE="en"; .venv\Scripts\python.exe -m solara run app.py
```

Los textos están en `ui_texts.py`. Para cambiar una etiqueta, editala en los dos idiomas (un test verifica que los dos tengan las mismas claves).

### Cambiar el motor de decisión

```python
DECISION_ENGINE_CONFIG = {
    "kind": "rule",  # "rule" | "llm" | "jev" | "hybrid"
    ...
}
```

Esto define el motor con el que arranca la aplicación. En la interfaz se puede cambiar sin tocar el código, desde el selector **Motor de decisión** (`híbrido`, `regla`, `llm`, `jev`) y tocando **Reiniciar**.

### Cambiar el proveedor/modelo de LLM (si kind es "llm" o el secundario del "hybrid")

```python
DECISION_ENGINE_CONFIG["llm"] = {
    "provider": "openai",  # "ollama" | "openai" | "anthropic"
    "model": "gpt-4o-mini",
    "temperature": 0.0,
    "timeout": 10.0,
    "max_retries": 2,
}
```

Recordá setear la API key correspondiente en `.env` (copiá `.env.example`): `OPENAI_API_KEY` u `ANTHROPIC_API_KEY`. Con `provider="ollama"` no hace falta key, pero sí tener el servidor local corriendo (`ollama pull phi3`).

### Usar Jev (TypeSafe AI System One)

```python
DECISION_ENGINE_CONFIG["jev"] = {
    "model": "jev-latest",
    "mode": "sample",       # "sample" (probabilístico) | "threshold" (>=0.5)
    "max_concurrency": 16,  # consultas simultáneas cuando se decide en lote
    "explain": True,        # pregunta extra "factor principal" para la interfaz
}
```

Requiere `TYPESAFE_API_KEY` en `.env`. Jev no genera texto: responde preguntas tipadas sobre el estado del ciudadano con probabilidades calibradas. Se le hacen dos preguntas en la misma consulta:

- `Noul` (sí/no): probabilidad de rebelarse, que decide la acción
- `Choice` (solo con `explain=True`): qué factor pesa más (descontento, miedo a la policía, contagio de activos o legitimidad). La interfaz lo muestra como `p(rebelión)=0.72 · factor: descontento (61%)`. Es cómo clasifica Jev el estado que recibe, no una explicación de cómo calculó la probabilidad. Suma ~40 ms por consulta; con `explain=False` se omite

**Jev puro (`kind="jev"`) es lento**: cada consulta tarda ~290 ms, casi todo de red (~240 ms de ida y vuelta a `api.typesafe.ai`), y con ~1100 ciudadanos consultando en serie un paso tarda minutos. Para usarlo en la interfaz conviene el híbrido con Jev como secundario:

```python
DECISION_ENGINE_CONFIG["kind"] = "hybrid"
DECISION_ENGINE_CONFIG["hybrid"]["secondary_kind"] = "jev"
DECISION_ENGINE_CONFIG["hybrid"]["secondary_kwargs"] = {}  # toma model/mode de DECISION_ENGINE_CONFIG["jev"]
```

Con `parallel_secondary=True` (el valor por defecto) y el cache, un paso tarda ~0.4 s. En la interfaz: **Motor de decisión** = `híbrido`, **Motor secundario** = `jev`.

### Aumentar uso del motor secundario (esquema híbrido)

```python
DECISION_ENGINE_CONFIG["hybrid"]["secondary_rate"] = 0.05  # 5% en lugar de 3%
```

### Modificar el prompt del LLM de chat

```python
from decision.llm_chat import DEFAULT_PROMPT_TEMPLATE  # referencia

DECISION_ENGINE_CONFIG["hybrid"]["secondary_kwargs"]["prompt_template"] = (
    "Tenés {grievance_pct}% de descontento y {risk_aversion_pct}% de aversión al riesgo. "
    "Policías visibles: {cops_visible}. Activos visibles: {actives_visible}. ¿Te rebelás?"
)
```

A diferencia de la versión anterior, la respuesta del LLM ya no se parsea por palabras clave: se exige una salida estructurada vía LangChain `with_structured_output`, con tres campos:

- `active: bool`: si el ciudadano se rebela
- `confidence: float`: confianza del modelo en su decisión (0 a 1)
- `reason: str`: justificación breve en primera persona (máximo 15 palabras), que la interfaz muestra en el panel **Últimas justificaciones**

Hay un prompt por idioma (`PROMPT_TEMPLATES` en `decision/llm_chat.py`); `llm.language` elige cuál se usa. Si cambiás el prompt, pedí también la justificación para que el panel la muestre. Los modelos chicos como `phi3` no siempre respetan el límite de palabras: la interfaz corta el texto en 160 caracteres, y el CSV de decisiones guarda el texto completo.

### Cambiar tamaño de la simulación

```python
MODEL_PARAMS = {
    "height": 50,  # Cuadrícula más grande
    "width": 50,
    "citizen_density": 0.8,  # Más ciudadanos
    ...
}
```

### Ajustar legitimidad del gobierno

```python
MODEL_PARAMS = {
    "legitimacy": 0.5,  # Menos legítimo = más rebelión
    ...
}
```

## 📊 Ver la Configuración Actual

Ejecuta:

```bash
python config.py
```

Mostrará un resumen completo de todos los parámetros activos.

## 🔧 Parámetros Clave

### UI_LANGUAGE

- `"es"` | `"en"`: idioma de la interfaz y de las justificaciones del LLM. Se copia en `DECISION_ENGINE_CONFIG["llm"]["language"]` y `["jev"]["language"]`, que se pueden cambiar por separado

### DECISION_ENGINE_CONFIG

- **kind**: `"rule"` | `"llm"` | `"jev"` | `"hybrid"` (motor de decisión de rebelión). La interfaz muestra `regla` y `híbrido`; el modelo acepta esos alias (`model.KIND_ALIASES`)
- **hybrid.primary_kind / secondary_kind**: motores combinados en el esquema híbrido (por defecto `rule` + `llm`)
- **hybrid.secondary_rate**: fracción de agentes que usan el motor secundario (0.03 = 3%, igual que el comportamiento original)
- **hybrid.parallel_secondary**: `True` consulta en paralelo, al inicio de cada paso, a los ciudadanos sorteados para el secundario (~10 s → ~0.4 s por paso con Jev). Esos ciudadanos deciden con su estado al inicio del paso; `False` los consulta uno por uno, como en la activación asíncrona original
- **llm.provider**: `"ollama"` | `"openai"` | `"anthropic"`
- **llm.model**: nombre del modelo (`phi3`, `gpt-4o-mini`, `claude-haiku-4-5`, etc.)
- **llm.temperature / timeout / max_retries**: parámetros del chat model de LangChain
- **llm.max_concurrency / jev.max_concurrency**: consultas simultáneas cuando se decide en lote (4 y 16 por defecto)
- **jev.model**: ruta de modelo Jev (`jev-latest`, `jev-1.13.0`, etc.)
- **jev.mode**: `"sample"` (activa probabilísticamente según la probabilidad devuelta) o `"threshold"` (activa si p >= 0.5)
- **jev.explain**: `True` agrega en la misma consulta la pregunta `Choice` sobre el factor principal, que se muestra en la interfaz
- **llm.language / jev.language**: idioma del prompt del LLM (y por lo tanto de su justificación) y del texto de Jev en la interfaz; por defecto, `UI_LANGUAGE`
- **cache.enabled / cache.precision / cache.count_cap**: cachea decisiones de motores costosos (llm/jev) para estados equivalentes: grievance/aversión/legitimidad redondeados a `precision` decimales (1 por defecto) y conteos de policías/activos topeados en `count_cap` (5). Con Jev en modo `sample` se cachea la probabilidad y cada hit vuelve a sortear
- **show_console_output**: mostrar en consola cada decisión no trivial (LLM/Jev), con su justificación

### MODEL_PARAMS

- **height/width**: Dimensiones de la cuadrícula
- **citizen_density**: Densidad de ciudadanos (0.0 a 1.0)
- **cop_density**: Densidad de policías (0.0 a 1.0)
- **citizen_vision/cop_vision**: Radio de visión en celdas
- **legitimacy**: Legitimidad percibida del gobierno (0.0 a 1.0)
  - 0.0 = gobierno totalmente ilegítimo → mucho descontento
  - 1.0 = gobierno totalmente legítimo → poco descontento
- **max_jail_term**: Duración máxima de prisión
- **movement**: Si los agentes (ciudadanos y policías) se mueven después de actuar
- **activation_order**: `"random"` (los agentes actúan en un orden aleatorio distinto en cada paso, como en Epstein) | `"sequential"` (siempre el mismo orden)

### AGENT_RULES (usados por el motor "rule")

- **rebellion_threshold**: Umbral para rebelarse (valores más bajos = más rebelión)
- **risk_constant** (k): Constante en `arrest_probability = 1 - exp(-k * round(cops_visible/(actives_visible+1)))`. El `round` es el de la implementación de referencia de Mesa, que sin él no reproduce las dinámicas del artículo

Con el motor `rule`, la simulación reproduce exactamente la implementación de referencia de Mesa del Modelo 1 de Epstein (misma semilla ⇒ mismas posiciones y estados en cada paso); lo verifica `tests/test_epstein_equivalence.py`.

### Variables de entorno (`.env`, ver `.env.example`)

- **OPENAI_API_KEY**: requerida si `llm.provider == "openai"`
- **ANTHROPIC_API_KEY**: requerida si `llm.provider == "anthropic"`
- **TYPESAFE_API_KEY**: requerida si `kind == "jev"`
- **OLLAMA_BASE_URL**: opcional, por defecto `http://localhost:11434`

`.env` nunca debe commitearse (ya está en `.gitignore`); `config.py` lo carga automáticamente con `python-dotenv`.

## 🎮 Experimentos Sugeridos

### Experimento 1: Gobierno Represivo

```python
MODEL_PARAMS = {
    "legitimacy": 0.3,  # Baja legitimidad
    "cop_density": 0.15,  # Muchos policías
}
```

### Experimento 2: Alta Tensión Social

```python
MODEL_PARAMS = {
    "legitimacy": 0.5,
    "citizen_density": 0.85,  # Muchos ciudadanos
}
AGENT_RULES = {
    "rebellion_threshold": 0.05,  # Fácil rebelarse
}
```

### Experimento 3: Más Decisiones con LLM/Jev

```python
DECISION_ENGINE_CONFIG["hybrid"]["secondary_rate"] = 0.10  # 10% usa el motor secundario
DECISION_ENGINE_CONFIG["hybrid"]["secondary_kind"] = "jev"
```

### Experimento 4: Comparar todos los motores con reporte de desempeño

```bash
python -m experiments.run_comparison --engines rule ollama openai anthropic jev --steps 30 --seeds 1 2 3
```

Genera `results/comparison_report.md` con latencia, tasa de error, costo estimado y características cualitativas de cada alternativa. También podés explorar los mismos datos en `experiments/compare_report.ipynb`.

## 💡 Tips de Rendimiento

1. **LLM/Jev lento o caro**: usá el modo `hybrid` con `parallel_secondary=True` y `cache.enabled=True` (los valores por defecto), o bajá `secondary_rate` a 0.01 (1%). En la interfaz: slider **Fracción al motor secundario**
2. **Simulación muy lenta**: Reduce tamaño de cuadrícula o densidad
3. **Pocas rebeliones**: Baja `legitimacy` o `active_threshold`
4. **Muchas rebeliones**: Sube `legitimacy` o `cop_density`
5. **Medir desempeño real**: corré `python -m experiments.run_comparison` y revisá `results/comparison_report.md`

## 🚀 Aplicar Cambios

Después de editar `config.py`:

1. **Guarda el archivo**
2. **Reinicia Solara**: cortá el servidor con Ctrl+C en su terminal y volvé a lanzarlo con el Python del entorno virtual:

   ```bash
   # Linux/Mac
   .venv/bin/python -m solara run app.py
   # Windows
   .venv\Scripts\python.exe -m solara run app.py
   ```

3. **Recarga el navegador**: `http://localhost:8765`

Los cambios se aplicarán automáticamente.

## 📝 Notas Importantes

- Los cambios en `config.py` NO requieren modificar código
- Todos los archivos importan de `config.py` automáticamente
- Puedes versionar diferentes configuraciones con Git
- Prueba `python config.py` para verificar que no hay errores de sintaxis

## 🩺 Problemas Frecuentes

- **`AttributeError: module 'reacton.ipyvuetify' has no attribute 'TabsItems'`**: se está usando un Python con Mesa < 3.5 junto con `ipyvuetify` 3. Lanzá la app con el Python del `.venv` (que tiene `mesa==3.5.1`, como pide `requirements.txt`) o actualizá Mesa en ese entorno.
- **El panel de justificaciones no muestra nada**: el motor `regla` no genera texto. Elegí `híbrido` con secundario `llm` o `jev`, o los motores `llm`/`jev`, tocá **Reiniciar** y después **▶** o **Paso**.
- **Cambié el motor en el panel izquierdo y sigue apareciendo el anterior**: los parámetros de ese panel (incluidos los motores) se aplican recién al tocar **Reiniciar**. Mientras haya cambios sin aplicar, el panel *Decisiones de los ciudadanos* muestra un aviso con los parámetros pendientes.
- **Jev tarda minutos por paso**: estás usando `kind="jev"` puro; ver la sección *Usar Jev* más arriba.
- **Errores de conexión con Ollama**: verificá que el servidor esté corriendo (`ollama serve`) y que el modelo esté descargado (`ollama pull phi3`). Si un motor secundario falla, ese ciudadano decide con la regla y el error queda contado en la tabla **Desempeño por motor**.
