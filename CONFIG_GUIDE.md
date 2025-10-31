# 📋 Guía de Configuración

Este archivo explica cómo personalizar la simulación usando `config.py`.

## 🎯 Configuración Rápida

Para cambiar parámetros de la simulación, edita `config.py`:

### Cambiar el modelo de LLM

```python
LLM_CONFIG = {
    "model": "llama2",  # Cambiar de "phi3" a "llama2", "mistral", etc.
    ...
}
```

### Aumentar uso del LLM

```python
LLM_CONFIG = {
    "llm_usage_rate": 0.05,  # 5% en lugar de 1%
    ...
}
```

### Modificar el prompt

```python
LLM_CONFIG = {
    "prompt_template": (
        "Tienes {grievance_pct}% descontento y {risk_aversion_pct}% miedo. "
        "¿Te rebelarías contra el gobierno? Sí o No"
    ),
    ...
}
```

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

### LLM_CONFIG

- **model**: Modelo de Ollama (`phi3`, `llama2`, `mistral`, etc.)
- **llm_usage_rate**: Fracción de agentes que usan LLM (0.01 = 1%)
- **max_response_tokens**: Máximo de palabras en respuesta
- **timeout**: Segundos máximo para esperar respuesta
- **prompt_template**: Plantilla del prompt (usa `{grievance_pct}` y `{risk_aversion_pct}`)
- **affirmative_keywords**: Palabras que indican "sí" en la respuesta
- **show_console_output**: Mostrar respuestas LLM en consola

### MODEL_PARAMS

- **height/width**: Dimensiones de la cuadrícula
- **citizen_density**: Densidad de ciudadanos (0.0 a 1.0)
- **cop_density**: Densidad de policías (0.0 a 1.0)
- **citizen_vision/cop_vision**: Radio de visión en celdas
- **legitimacy**: Legitimidad percibida del gobierno (0.0 a 1.0)
  - 0.0 = gobierno totalmente ilegítimo → mucho descontento
  - 1.0 = gobierno totalmente legítimo → poco descontento
- **max_jail_term**: Duración máxima de prisión
- **movement**: Si los agentes pueden moverse

### AGENT_RULES

- **rebellion_threshold**: Umbral para rebelarse (valores más bajos = más rebelión)
- **risk_constant**: Constante k en el cálculo de riesgo

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

### Experimento 3: Más Decisiones con LLM

```python
LLM_CONFIG = {
    "llm_usage_rate": 0.10,  # 10% usa LLM
    "model": "llama2",  # Modelo más grande
}
```

### Experimento 4: Respuestas Más Elaboradas

```python
LLM_CONFIG = {
    "max_response_tokens": 10,  # Respuestas más largas
    "prompt_template": (
        "Contexto: Vives en un país en crisis. "
        "Tu descontento es {grievance_pct}% y tu miedo {risk_aversion_pct}%. "
        "¿Participarías en una protesta? Explica brevemente."
    ),
}
```

## 💡 Tips de Rendimiento

1. **LLM lento**: Reduce `llm_usage_rate` a 0.005 (0.5%)
2. **Simulación muy lenta**: Reduce tamaño de cuadrícula o densidad
3. **Pocas rebeliones**: Baja `legitimacy` o `rebellion_threshold`
4. **Muchas rebeliones**: Sube `legitimacy` o `cop_density`

## 🚀 Aplicar Cambios

Después de editar `config.py`:

1. **Guarda el archivo**
2. **Reinicia Solara**:
   ```bash
   pkill -f "solara run app.py"
   solara run app.py
   ```
3. **Recarga el navegador**: http://localhost:8765

Los cambios se aplicarán automáticamente.

## 📝 Notas Importantes

- Los cambios en `config.py` NO requieren modificar código
- Todos los archivos importan de `config.py` automáticamente
- Puedes veionar diferentes configuraciones con Git
- Prueba `python config.py` para verificar que no hay errores de sintaxis
