# Civil Violence LLM

Modelo de violencia civil de Epstein mejorado con Large Language Models (LLM) para la toma de decisiones de los agentes.

## Descripción

Este proyecto implementa el Modelo 1 del artículo "Modeling civil violence: An agent-based computational approach" de Joshua Epstein ([PNAS, 2002](https://www.pnas.org/content/99/suppl_3/7243.full)), con la innovación de utilizar modelos de lenguaje (LLM) para simular el proceso de toma de decisiones de los ciudadanos.

### Características principales

- **Simulación basada en agentes** utilizando [Mesa](https://mesa.readthedocs.io/)
- **Toma de decisiones con LLM**: Los ciudadanos usan Ollama (modelo phi3) para decidir si rebelarse
- **Visualización interactiva** con [Solara](https://solara.dev/)
- **Agentes**:
  - **Ciudadanos**: Toman decisiones de rebelión basadas en su nivel de descontento y aversión al riesgo
  - **Policías**: Arrestan a ciudadanos activos en su campo de visión

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.ai/) instalado con el modelo `phi3`

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/TU_USUARIO/Civil_Violence_LLM.git
cd Civil_Violence_LLM
```

2. Crear y activar un entorno virtual:

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # En Linux/Mac
# .venv\Scripts\activate  # En Windows
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Instalar y configurar Ollama:

```bash
# Instalar Ollama desde https://ollama.ai/
# Descargar el modelo phi3
ollama pull phi3
```

## Uso

### Ejecutar la simulación con visualización

```bash
source .venv/bin/activate
solara run app.py
```

Luego abre tu navegador en: `http://localhost:8765`

### Ejecutar en segundo plano

```bash
nohup solara run app.py > solara.log 2>&1 &
```

## Estructura del proyecto

```
Civil_Violence_LLM/
├── agents.py           # Definición de agentes (Ciudadanos y Policías)
├── model.py            # Modelo principal de simulación
├── app.py              # Interfaz de visualización con Solara
├── requirements.txt    # Dependencias de Python
├── README.md           # Este archivo
└── SOLUCIONES.md       # Documentación de soluciones técnicas
```

## Parámetros del modelo

- **`citizen_density`**: Densidad inicial de ciudadanos (0-1)
- **`cop_density`**: Densidad inicial de policías (0-1)
- **`citizen_vision`**: Radio de visión de los ciudadanos
- **`cop_vision`**: Radio de visión de los policías
- **`legitimacy`**: Percepción de legitimidad del régimen (0-1)
- **`max_jail_term`**: Sentencia máxima de cárcel
- **`active_threshold`**: Umbral para que un ciudadano se rebele
- **`arrest_prob_constant`**: Constante para calcular probabilidad de arresto

## Estados de los ciudadanos

- 🟠 **ACTIVE (Activo)**: En rebelión contra el régimen
- 🔵 **QUIET (Quieto)**: No está en rebelión
- ⚫ **ARRESTED (Arrestado)**: En prisión

## Tecnologías utilizadas

- [Mesa](https://mesa.readthedocs.io/) - Framework de modelado basado en agentes
- [Solara](https://solara.dev/) - Framework de visualización web reactiva
- [Ollama](https://ollama.ai/) - Motor de LLM local
- [Matplotlib](https://matplotlib.org/) - Visualización de datos
- [NetworkX](https://networkx.org/) - Análisis de redes

## Créditos

Basado en el trabajo original de:

- Epstein, J. M. (2002). "Modeling civil violence: An agent-based computational approach". *Proceedings of the National Academy of Sciences*, 99(suppl 3), 7243-7250.

## Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Autor

**Juan Aued (modificado por Leonardo Rufiner)**
