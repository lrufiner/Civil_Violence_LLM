"""Textos de la interfaz en español e inglés; el idioma se elige con `config.UI_LANGUAGE`."""

from __future__ import annotations

from typing import Dict

from config import UI_LANGUAGE

# Traducción de los textos fijos de Mesa (SolaraViz), que vienen en inglés
MESA_TEXTS_ES: Dict[str, str] = {
    "Controls": "Controles",
    "Play Interval (ms)": "Intervalo de reproducción (ms)",
    "Render Interval (steps)": "Redibujar cada (pasos)",
    "Increase play interval to avoid skipping plots": "Aumentá el intervalo para no saltear gráficos",
    "Use Threads": "Usar hilos",
    "Model Parameters": "Parámetros del modelo (se aplican al reiniciar)",
    "Information": "Información",
    "Command Console": "Consola",
    "Reset": "Reiniciar",
    "Step": "Paso",
}

ABOUT_ES = """
**Modelo de violencia civil de Epstein (2002).** Cada punto es un ciudadano (🔵 tranquilo,
🟠 activo, ⚫ preso) o un policía (gris). Un ciudadano se rebela cuando su descontento, que crece
si el gobierno pierde legitimidad, supera el riesgo de ser arrestado por los policías que ve
cerca; los policías detienen a los activos que ven.

Decide la **regla** de Epstein, un **LLM** (que justifica en una frase) o **Jev** (que da una
probabilidad y el factor que más pesó); en modo **híbrido** la regla decide casi todo y una fracción
consulta al LLM o a Jev. **Uso:** elegí parámetros a la izquierda y tocá **Reiniciar**; **▶** corre la
simulación y **Paso** avanza de a uno. Las fórmulas y los detalles están en la pestaña **Cómo funciona**.
"""

ABOUT_EN = """
**Epstein's civil violence model (2002).** Each dot is a citizen (🔵 quiet, 🟠 active,
⚫ jailed) or a cop (gray). A citizen rebels when their grievance, which grows as the government
loses legitimacy, outweighs the risk of being arrested by the cops they can see; cops arrest the
active citizens in their sight.

The decision is made by Epstein's **rule**, an **LLM** (which justifies it in one sentence) or
**Jev** (which gives a probability and the factor that weighed most); in **hybrid** mode the rule
decides almost everything and a fraction of citizens asks the LLM or Jev. **Usage:** choose the
parameters on the left and press **Reset**; **▶** runs the simulation and **Step** advances one step.
Formulas and details are in the **How it works** tab.
"""

HELP_ES = r"""
## 1. La regla de Epstein (Modelo 1)

Cada ciudadano tiene dos rasgos fijos, sorteados al crearlo: la **privación** $H \sim U(0,1)$ y la
**aversión al riesgo** $R \sim U(0,1)$. La **legitimidad** $L$ del gobierno es la misma para todos.

| Magnitud | Fórmula | Control en la interfaz |
|---|---|---|
| Descontento | $G = H\,(1 - L)$ | Legitimidad del gobierno ($L$) |
| Probabilidad estimada de arresto | $P = 1 - \exp\left(-k \cdot \mathrm{round}\left(\dfrac{C_v}{A_v + 1}\right)\right)$ | Constante de riesgo de arresto ($k$) |
| Riesgo neto | $N = R \cdot P$ | — |
| Regla de rebelión | activo si $G - N > T$, si no tranquilo | Umbral de rebelión ($T$) |

- $C_v$ y $A_v$ son los policías y los ciudadanos activos que el ciudadano **ve**: los que están en
  su vecindario de von Neumann de radio $v$ (celdas a distancia de Manhattan $\le v$, *Visión de los
  ciudadanos*). El $+1$ cuenta al propio ciudadano, como en el artículo original.
- El **redondeo** del cociente no figura en el artículo, pero lo usa la implementación de referencia
  de Mesa porque sin él no se reproducen las dinámicas publicadas: si hay menos de la mitad de policías
  que de activos a la vista, el cociente redondea a 0 y el riesgo percibido desaparece.
- **Policías:** en cada paso miran su vecindario (*Visión de los policías*) y arrestan a un ciudadano
  activo al azar. La condena se sortea entre $0$ y $J_{max}$ pasos (*Condena máxima*); mientras está
  preso, el ciudadano no decide.
- **Movimiento:** al final de su turno, cada agente libre (ciudadano o policía) se mueve a una celda
  vacía al azar dentro de su visión. La grilla es un toro (los bordes se conectan).
- **Activación:** en cada paso todos los agentes actúan uno por uno, en un **orden aleatorio** que
  cambia en cada paso; cada uno ve los cambios de los que actuaron antes.

En modo **regla**, la simulación reproduce paso a paso la implementación de referencia de Mesa del
Modelo 1 (misma semilla, mismas posiciones y estados); un test automático lo verifica.

La intuición: bajar $L$ aumenta el descontento de todos; más policías visibles o menos rebeldes
alrededor aumentan el riesgo percibido. Por eso aparecen las "explosiones" de rebelión cuando se
juntan varios activos lejos de la policía.

## 2. Cómo decide un LLM

En lugar de aplicar la fórmula, el ciudadano le describe su situación a un modelo de lenguaje
(Ollama local, OpenAI o Anthropic) con este prompt:

> *Sos un ciudadano en una simulación de disturbios civiles. Descontento: $G$ %. Aversión al riesgo:
> $R$ %. Policías visibles: $C_v$. Ciudadanos activos visibles: $A_v$. Decidí si te rebelás…*

- El LLM **no** recibe $L$, $P$, $k$ ni $T$: tiene que "razonar" el riesgo a partir de los conteos.
- La respuesta es **estructurada** (no se interpreta texto libre): `active` (sí/no), `confidence`
  (0 a 1) y `reason`, una justificación de hasta 15 palabras que se muestra en *Últimas justificaciones*.
- La decisión es directamente `active`. La probabilidad que se muestra es
  $p = \text{confidence}$ si se rebela y $p = 1 - \text{confidence}$ si no.
- Se usa temperatura 0, así que el mismo estado suele dar la misma respuesta.

## 3. Cómo decide Jev

Jev (TypeSafe AI, "System One") no genera texto: responde **preguntas tipadas** con probabilidades
calibradas. Recibe una descripción del estado en lenguaje natural: descontento, aversión al riesgo y
legitimidad (en %), si su descontento es bajo, moderado o alto, cuántos policías y rebeldes ve y en cuántas celdas (para dar escala), cuántos
rebeldes habría por policía, y que cada policía arresta a uno solo por turno. No recibe la fórmula ni
el umbral de Epstein. Se le hacen dos preguntas en la misma consulta:

- **¿Se rebela?** (pregunta sí/no, `Noul`): devuelve la probabilidad $p$. En modo `sample` el
  ciudadano se rebela con probabilidad $p$ (un sorteo con la semilla del modelo); en modo
  `threshold`, si $p \ge 0.5$.
- **¿Qué factor pesa más?** (pregunta de opción, `Choice`): descontento, miedo a la policía, contagio
  de activos o legitimidad. Solo se usa para la explicación
  (`p(rebelión)=0.10 · factor: miedo a la policía (85%)`); no cambia la decisión. Es cómo clasifica
  Jev el estado que recibe, no una explicación de cómo calculó $p$.

## 4. Modo híbrido, cache y fallas

- **Híbrido:** en cada paso, cada ciudadano libre usa el motor secundario (LLM o Jev) con
  probabilidad $q$ (*Fracción al motor secundario*, 3% por defecto) y la regla en el resto de los casos.
- **En paralelo:** los ciudadanos sorteados para el secundario se consultan todos juntos al inicio del
  paso, así que deciden con el vecindario que tenían en ese momento. Es la única diferencia con la
  activación uno por uno, y baja un paso con Jev de ~10 s a ~0.4 s.
- **Cache:** dos estados con $G$, $R$ y $L$ iguales redondeados a un decimal, y con $C_v$, $A_v$
  iguales (contando hasta 5), reutilizan la misma respuesta. Con Jev en modo `sample` se guarda $p$ y
  se vuelve a sortear en cada uso.
- **Fallas:** si el LLM o Jev no responden, ese ciudadano decide con la regla y el error se cuenta en
  *Desempeño por motor*.

**Referencia:** Epstein, J. M. (2002). *Modeling civil violence: An agent-based computational
approach.* PNAS 99(suppl 3), 7243–7250.
"""

HELP_EN = r"""
## 1. Epstein's rule (Model 1)

Each citizen has two fixed traits drawn at creation: **hardship** $H \sim U(0,1)$ and **risk
aversion** $R \sim U(0,1)$. The government's **legitimacy** $L$ is the same for everyone.

| Quantity | Formula | Control in the interface |
|---|---|---|
| Grievance | $G = H\,(1 - L)$ | Government legitimacy ($L$) |
| Estimated arrest probability | $P = 1 - \exp\left(-k \cdot \mathrm{round}\left(\dfrac{C_v}{A_v + 1}\right)\right)$ | Arrest risk constant ($k$) |
| Net risk | $N = R \cdot P$ | — |
| Rebellion rule | active if $G - N > T$, otherwise quiet | Rebellion threshold ($T$) |

- $C_v$ and $A_v$ are the cops and active citizens the citizen **sees**: those in their von Neumann
  neighborhood of radius $v$ (cells at Manhattan distance $\le v$, *Citizen vision*). The $+1$ counts
  the citizen themselves, as in the original paper.
- The **rounding** of the ratio is not in the paper, but Mesa's reference implementation uses it
  because without it the published dynamics cannot be reproduced: with fewer than half as many cops as
  active citizens in sight, the ratio rounds to 0 and the perceived risk vanishes.
- **Cops:** each step they scan their neighborhood (*Cop vision*) and arrest one random active
  citizen. The sentence is drawn between $0$ and $J_{max}$ steps (*Max jail term*); while jailed, a
  citizen does not decide.
- **Movement:** at the end of its turn, each free agent (citizen or cop) moves to a random empty cell
  within its vision. The grid is a torus (edges wrap around).
- **Activation:** each step all agents act one by one, in a **random order** that changes every step;
  each one sees the changes made by those who acted before.

In **rule** mode the simulation reproduces Mesa's reference implementation of Model 1 step by step
(same seed, same positions and states); an automated test checks it.

The intuition: lowering $L$ raises everyone's grievance; more visible cops or fewer nearby rebels
raise the perceived risk. That is why rebellion "bursts" appear where several active citizens gather
away from the police.

## 2. How an LLM decides

Instead of applying the formula, the citizen describes its situation to a language model (local
Ollama, OpenAI or Anthropic) with this prompt:

> *You are a citizen in a civil violence simulation. Grievance: $G$ %. Risk aversion: $R$ %. Visible
> cops: $C_v$. Visible active citizens: $A_v$. Decide whether you rebel…*

- The LLM does **not** receive $L$, $P$, $k$ or $T$: it has to "reason" about the risk from the counts.
- The answer is **structured** (no free-text parsing): `active` (yes/no), `confidence` (0 to 1) and
  `reason`, a justification of up to 15 words shown under *Latest justifications*.
- The decision is `active` itself. The probability shown is $p = \text{confidence}$ if it rebels and
  $p = 1 - \text{confidence}$ otherwise.
- Temperature is 0, so the same state usually gets the same answer.

## 3. How Jev decides

Jev (TypeSafe AI, "System One") produces no text: it answers **typed questions** with calibrated
probabilities. It receives a natural-language description of the state: grievance, risk aversion and
legitimacy (in %), whether its grievance is low, moderate or high, how many cops and rebels it sees and across how many cells (for scale), how many
rebels there would be per cop, and that each cop arrests only one rebel per turn. It does not receive
Epstein's formula or threshold. It is asked two questions in the same request:

- **Does it rebel?** (yes/no question, `Noul`): returns the probability $p$. In `sample` mode the
  citizen rebels with probability $p$ (a draw using the model's seed); in `threshold` mode, if
  $p \ge 0.5$.
- **Which factor weighs most?** (choice question, `Choice`): grievance, fear of the police, contagion
  from active citizens or legitimacy. It is only used for the explanation
  (`p(rebellion)=0.10 · factor: fear of the police (85%)`) and does not change the decision. It is how
  Jev classifies the state it receives, not an account of how it computed $p$.

## 4. Hybrid mode, cache and failures

- **Hybrid:** each step, each free citizen uses the secondary engine (LLM or Jev) with probability
  $q$ (*Fraction to the secondary engine*, 3% by default) and the rule otherwise.
- **In parallel:** the citizens drawn for the secondary engine are all queried together at the start
  of the step, so they decide with the neighborhood they had at that moment. This is the only
  difference from one-by-one activation, and it cuts a Jev step from ~10 s to ~0.4 s.
- **Cache:** two states with the same $G$, $R$ and $L$ rounded to one decimal, and the same $C_v$,
  $A_v$ (counting up to 5), reuse the same answer. For Jev in `sample` mode $p$ is stored and drawn
  again on each use.
- **Failures:** if the LLM or Jev does not answer, that citizen decides with the rule and the error is
  counted in *Performance by engine*.

**Reference:** Epstein, J. M. (2002). *Modeling civil violence: An agent-based computational
approach.* PNAS 99(suppl 3), 7243–7250.
"""

TEXTS: Dict[str, Dict] = {
    "es": {
        "app_name": "Violencia civil de Epstein con LLM y Jev",
        "page_names": ["Simulación", "Cómo funciona"],
        "mesa_texts": MESA_TEXTS_ES,
        # Gráfico
        "series": {"quiet_citizens": "Tranquilos", "active_citizens": "Activos", "jailed_citizens": "Presos"},
        "x_axis": "Paso",
        "y_axis": "Ciudadanos",
        # Parámetros iniciales
        "seed": "Semilla aleatoria (entero)",
        "citizen_density": "Densidad inicial de ciudadanos",
        "cop_density": "Densidad inicial de policías",
        "citizen_vision": "Visión de los ciudadanos",
        "cop_vision": "Visión de los policías",
        "legitimacy": "Legitimidad del gobierno",
        "max_jail_term": "Condena máxima (pasos)",
        "active_threshold": "Umbral de rebelión (regla de Epstein)",
        "arrest_prob_constant": "Constante de riesgo de arresto (k)",
        "decision_kind": "Motor de decisión",
        "kind_options": {"hybrid": "híbrido", "rule": "regla", "llm": "llm", "jev": "jev"},
        "secondary_kind": "Motor secundario (solo en híbrido)",
        "secondary_rate": "Fracción al motor secundario",
        "llm_provider": "Proveedor LLM (motor llm o secundario llm)",
        # Ajustes en vivo
        "live_title": "⚙️ Ajustes en vivo (sin reiniciar)",
        "live_legitimacy": "🏛️ Legitimidad: {value:.2f}",
        "live_citizen_vision": "👁️ Visión ciudadanos: {value}",
        "live_cop_vision": "🚔 Visión policías: {value}",
        "live_jail": "⚖️ Condena máxima: {value}",
        "live_threshold": "🔥 Umbral de rebelión: {value:.2f}",
        "live_k": "🚨 Riesgo de arresto (k): {value:.1f}",
        # Descripción de motores
        "engine_hybrid": "Híbrido: {primary} + {secondary} para el {rate:.0%} de las decisiones{parallel}",
        "engine_parallel": ", en paralelo",
        "engine_cached": "{inner} con cache",
        "engine_rule": "regla de Epstein",
        "rule_source": "Regla",
        # Panel de decisiones
        "decisions_title": "💭 Decisiones de los ciudadanos",
        "performance_title": "📈 Desempeño por motor",
        "justifications_title": "🗨️ Últimas justificaciones",
        "engine_label": "Motor: {engine}",
        "table_header": "| Motor | Decisiones | Cache | Errores | Latencia |",
        "no_decisions_yet": "Sin decisiones todavía: tocá ▶ o Paso.",
        "decisions_in_step": "Decisiones LLM/Jev en el paso {step}: {count} (se muestran las últimas {shown})",
        "rebels": "se rebela",
        "stays_quiet": "se queda quieto",
        "from_cache": " · ♻️ desde cache",
        "citizen_line": "{symbol} Ciudadano #{id}: {decision} (p={p:.2f}) · {source}{cache}",
        "citizen_traits": "Descontento {grievance:.0%} · Aversión al riesgo {risk:.0%}",
        "press_play": "Tocá ▶ o Paso para ver decisiones.",
        "none_this_step": "Ninguna decisión LLM/Jev en este paso.",
        "pending": ("Cambiaste {names} en el panel izquierdo: tocá REINICIAR para aplicarlo. "
                    "Mientras tanto sigue corriendo el motor actual ({engine})."),
        # Acerca de / ayuda
        "about_title": "ℹ️ Acerca de esta simulación",
        "about": ABOUT_ES,
        "help_title": "📘 Cómo funciona: reglas de Epstein y decisiones con LLM y Jev",
        "help": HELP_ES,
    },
    "en": {
        "app_name": "Epstein civil violence with LLM and Jev",
        "page_names": ["Simulation", "How it works"],
        "mesa_texts": {},
        "series": {"quiet_citizens": "Quiet", "active_citizens": "Active", "jailed_citizens": "Jailed"},
        "x_axis": "Step",
        "y_axis": "Citizens",
        "seed": "Random seed (integer)",
        "citizen_density": "Initial citizen density",
        "cop_density": "Initial cop density",
        "citizen_vision": "Citizen vision",
        "cop_vision": "Cop vision",
        "legitimacy": "Government legitimacy",
        "max_jail_term": "Max jail term (steps)",
        "active_threshold": "Rebellion threshold (Epstein's rule)",
        "arrest_prob_constant": "Arrest risk constant (k)",
        "decision_kind": "Decision engine",
        "kind_options": {"hybrid": "hybrid", "rule": "rule", "llm": "llm", "jev": "jev"},
        "secondary_kind": "Secondary engine (hybrid only)",
        "secondary_rate": "Fraction to the secondary engine",
        "llm_provider": "LLM provider (llm engine or llm secondary)",
        "live_title": "⚙️ Live settings (no restart)",
        "live_legitimacy": "🏛️ Legitimacy: {value:.2f}",
        "live_citizen_vision": "👁️ Citizen vision: {value}",
        "live_cop_vision": "🚔 Cop vision: {value}",
        "live_jail": "⚖️ Max jail term: {value}",
        "live_threshold": "🔥 Rebellion threshold: {value:.2f}",
        "live_k": "🚨 Arrest risk (k): {value:.1f}",
        "engine_hybrid": "Hybrid: {primary} + {secondary} for {rate:.0%} of decisions{parallel}",
        "engine_parallel": ", in parallel",
        "engine_cached": "{inner} with cache",
        "engine_rule": "Epstein's rule",
        "rule_source": "Rule",
        "decisions_title": "💭 Citizen decisions",
        "performance_title": "📈 Performance by engine",
        "justifications_title": "🗨️ Latest justifications",
        "engine_label": "Engine: {engine}",
        "table_header": "| Engine | Decisions | Cache | Errors | Latency |",
        "no_decisions_yet": "No decisions yet: press ▶ or Step.",
        "decisions_in_step": "LLM/Jev decisions in step {step}: {count} (showing the last {shown})",
        "rebels": "rebels",
        "stays_quiet": "stays quiet",
        "from_cache": " · ♻️ from cache",
        "citizen_line": "{symbol} Citizen #{id}: {decision} (p={p:.2f}) · {source}{cache}",
        "citizen_traits": "Grievance {grievance:.0%} · Risk aversion {risk:.0%}",
        "press_play": "Press ▶ or Step to see decisions.",
        "none_this_step": "No LLM/Jev decisions in this step.",
        "pending": ("You changed {names} in the left panel: press RESET to apply it. "
                    "Meanwhile the current engine keeps running ({engine})."),
        "about_title": "ℹ️ About this simulation",
        "about": ABOUT_EN,
        "help_title": "📘 How it works: Epstein's rules and LLM/Jev decisions",
        "help": HELP_EN,
    },
}

T = TEXTS[UI_LANGUAGE]
