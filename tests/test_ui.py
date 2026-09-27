import reacton

import ui_mesa
from decision.base import DecisionEngine
from decision.hybrid import HybridEngine
from decision.rule_based import RuleBasedEngine
from decision.types import DecisionResult
from mesa.visualization.utils import force_update
from model import EpsteinCivilViolenceLLM


def test_mesa_texts_follow_the_configured_language():
    from ui_texts import TEXTS

    ui_mesa.instalar(textos=TEXTS["es"]["mesa_texts"], nombres_vistas=TEXTS["es"]["page_names"],
                     formato_paso="Paso: {}")
    assert ui_mesa.traducir("Reset") == "Reiniciar"
    assert ui_mesa.traducir("Time: 12.0") == "Paso: 12"
    assert ui_mesa.traducir("Page 1") == "Cómo funciona"
    assert ui_mesa.traducir("texto propio") == "texto propio"

    ui_mesa.instalar(textos=TEXTS["en"]["mesa_texts"], nombres_vistas=TEXTS["en"]["page_names"])
    assert ui_mesa.traducir("Reset") == "Reset"
    assert ui_mesa.traducir("Time: 12.0") == "Step: 12"
    assert ui_mesa.traducir("Page 0") == "Simulation"


def test_both_languages_define_the_same_texts():
    from ui_texts import TEXTS

    assert set(TEXTS["es"]) == set(TEXTS["en"])
    assert set(TEXTS["es"]["kind_options"]) == set(TEXTS["en"]["kind_options"]) == {"hybrid", "rule", "llm", "jev"}


class _ExplainingEngine(DecisionEngine):
    name = "llm:stub:test"

    def decide(self, state):
        return DecisionResult(
            active=False, probability=0.2, source=self.name, latency_ms=1.0,
            explanation=f"justificación del agente {state.agent_id}",
        )


def _texts(widget):
    found = []
    for attr in ("value", "children"):
        value = getattr(widget, attr, None)
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, (list, tuple)):
            for child in value:
                found.extend([child] if isinstance(child, str) else _texts(child))
    return found


def test_decisions_panel_refreshes_after_each_step():
    import app

    model = EpsteinCivilViolenceLLM(
        width=15, height=15, seed=1,
        decision_engine=HybridEngine(RuleBasedEngine(0.1, 2.3), _ExplainingEngine(), 0.2),
    )
    box, _ = reacton.render(app.DecisionsPanel(model), handle_error=False)

    for _ in range(2):
        model.step()
    force_update()
    texts = " ".join(_texts(box))

    assert "en el paso 2" in texts
    assert "justificación del agente" in texts
    assert "llm:stub:test" in texts  # fila de la tabla de desempeño por motor


def test_sidebar_changes_are_flagged_until_reset():
    import app

    ui_mesa.instalar(parametros_iniciales={"Motor secundario (solo en híbrido)"})
    received = []
    select = ui_mesa._con_textos_traducidos(lambda label, **kwargs: kwargs["on_value"])
    select("Motor secundario (solo en híbrido)", on_value=received.append)("jev")  # el usuario elige "jev"
    assert received == ["jev"]
    assert "Motor secundario (solo en híbrido)" in ui_mesa.parametros_pendientes.value

    model = EpsteinCivilViolenceLLM(width=10, height=10, seed=1, decision_engine=RuleBasedEngine(0.1, 2.3))
    box, _ = reacton.render(app.DecisionsPanel(model), handle_error=False)
    # Al montarse con un modelo nuevo (lo que hace Reiniciar) el aviso se limpia
    assert ui_mesa.parametros_pendientes.value == frozenset()

    ui_mesa.parametros_pendientes.set(frozenset({"Motor secundario (solo en híbrido)"}))
    assert "REINICIAR" in " ".join(_texts(box))
