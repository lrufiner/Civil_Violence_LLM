import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_classifier(monkeypatch):
    """Simula el paquete opcional `langchain_typesafe` sin necesitar la dependencia real."""
    fake_module = types.ModuleType("langchain_typesafe")
    fake_module.Noul = lambda **kwargs: kwargs  # type: ignore[attr-defined]
    fake_module.Choice = lambda **kwargs: kwargs  # type: ignore[attr-defined]
    classifier_instance = MagicMock()
    fake_module.TypeSafeClassifier = MagicMock(return_value=classifier_instance)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_typesafe", fake_module)
    return classifier_instance


def _response(probability, factor=None, factor_probability=0.6):
    """Respuesta de Jev con la probabilidad de rebelión y, opcionalmente, el factor principal."""
    choices = {}
    if factor is not None:
        choices["factor"] = types.SimpleNamespace(
            choice=factor, confidence=0.5, probabilities={factor: factor_probability}
        )
    return types.SimpleNamespace(nouls={"rebellion": MagicMock(noul=probability)}, choices=choices)


def _state():
    from decision.types import CitizenDecisionState

    return CitizenDecisionState(
        agent_id=1, hardship=0.8, risk_aversion=0.2, legitimacy=0.5,
        grievance=0.4, cops_visible=1, actives_visible=1,
    )


def test_jev_decide_uses_noul_probability_threshold_mode(fake_classifier):
    from decision.jev import JevDecisionEngine

    fake_classifier.invoke.return_value = _response(0.9)

    engine = JevDecisionEngine(model="jev-latest", mode="threshold")
    result = engine.decide(_state())

    assert result.probability == 0.9
    assert result.active is True
    assert result.source == "jev:jev-latest"
    assert result.error is None


def test_jev_decide_captures_errors_without_raising(fake_classifier):
    from decision.jev import JevDecisionEngine

    fake_classifier.invoke.side_effect = RuntimeError("api down")

    engine = JevDecisionEngine(model="jev-latest", mode="threshold")
    result = engine.decide(_state())

    assert result.error == "api down"
    assert result.active is False


def test_invalid_mode_raises(fake_classifier):
    from decision.jev import JevDecisionEngine

    with pytest.raises(ValueError):
        JevDecisionEngine(model="jev-latest", mode="not-a-mode")


def test_jev_decide_many_is_reproducible_regardless_of_thread_order(fake_classifier):
    import random

    from decision.types import CitizenDecisionState
    from decision.jev import JevDecisionEngine

    def invoke(request):
        # La probabilidad depende del estado, así el orden de las respuestas importa
        return _response(0.5 if "Policías visibles: 1" in request["state"] else 0.2)

    fake_classifier.invoke.side_effect = invoke
    states = [
        CitizenDecisionState(agent_id=i, hardship=0.8, risk_aversion=0.2, legitimacy=0.5,
                             grievance=0.4, cops_visible=i % 2, actives_visible=0)
        for i in range(40)
    ]

    parallel = JevDecisionEngine(mode="sample", rng=random.Random(3), max_concurrency=8).decide_many(states)
    engine_seq = JevDecisionEngine(mode="sample", rng=random.Random(3))
    sequential = [engine_seq.decide(s) for s in states]

    assert [(r.active, r.probability) for r in parallel] == [(r.active, r.probability) for r in sequential]


def test_jev_explanation_includes_main_factor(fake_classifier):
    from decision.jev import JevDecisionEngine

    fake_classifier.invoke.return_value = _response(0.72, factor="descontento", factor_probability=0.61)

    result = JevDecisionEngine(mode="threshold").decide(_state())

    assert result.explanation == "p(rebelión)=0.72 · factor: descontento (61%)"
    assert set(fake_classifier.invoke.call_args.args[0]["questions"]) == {"rebellion", "factor"}


def test_jev_without_explain_asks_only_rebellion(fake_classifier):
    from decision.jev import JevDecisionEngine

    fake_classifier.invoke.return_value = _response(0.3)

    result = JevDecisionEngine(mode="threshold", explain=False).decide(_state())

    assert result.explanation == "p(rebelión)=0.30"
    assert set(fake_classifier.invoke.call_args.args[0]["questions"]) == {"rebellion"}


def test_jev_explanation_in_english(fake_classifier):
    from decision.jev import JevDecisionEngine

    fake_classifier.invoke.return_value = _response(0.1, factor="miedo a la policía", factor_probability=0.85)

    result = JevDecisionEngine(mode="threshold", language="en").decide(_state())

    assert result.explanation == "p(rebellion)=0.10 · factor: fear of the police (85%)"


def test_jev_state_gives_scale_and_rebels_per_cop(fake_classifier):
    from decision.jev import JevDecisionEngine
    from decision.types import CitizenDecisionState

    def state(cops, actives):
        return CitizenDecisionState(agent_id=1, hardship=0.8, risk_aversion=0.3, legitimacy=0.2, grievance=0.64,
                                    cops_visible=cops, actives_visible=actives, vision_cells=112)

    crowded = JevDecisionEngine._build_state(state(cops=8, actives=39))
    assert "112 celdas" in crowded and "5.0 rebeldes por cada policía" in crowded and "64%" in crowded
    assert "muy enojado" in crowded  # lectura cualitativa del descontento, para que no lo opaque el riesgo
    assert "único rebelde frente a 8 policías" in JevDecisionEngine._build_state(state(cops=8, actives=0))
    assert "ningún policía" in JevDecisionEngine._build_state(state(cops=0, actives=3))
