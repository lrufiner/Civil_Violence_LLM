from decision.rule_based import RuleBasedEngine
from model import EpsteinCivilViolenceLLM


def _model(**overrides):
    # Se inyecta un motor para no construir clientes LLM/Jev; solo se prueba la resolución de la spec.
    model = EpsteinCivilViolenceLLM(width=5, height=5, decision_engine=RuleBasedEngine(0.1, 2.3))
    model._engine_overrides.update(overrides)
    return model


def test_hybrid_secondary_can_be_switched_to_jev():
    spec = _model(kind="hybrid", secondary_kind="jev", jev_model="jev-test", secondary_rate=0.05)._resolve_engine_spec()

    assert spec["secondary_kind"] == "jev"
    assert spec["secondary_kwargs"]["model"] == "jev-test"
    assert "provider" not in spec["secondary_kwargs"]  # no hereda los kwargs del secundario llm de config
    assert spec["secondary_rate"] == 0.05
    assert spec["primary_kwargs"] == {"threshold": 0.1, "risk_constant": 2.3}


def test_hybrid_llm_secondary_applies_ui_provider():
    spec = _model(kind="hybrid", secondary_kind="llm", llm_provider="openai")._resolve_engine_spec()

    assert spec["secondary_kwargs"]["provider"] == "openai"
    assert "timeout" in spec["secondary_kwargs"]
