import pytest

from decision import factory
from decision.cache import CachedDecisionEngine
from decision.factory import build_engine
from decision.hybrid import HybridEngine
from decision.rule_based import RuleBasedEngine


def test_build_rule_engine():
    engine = build_engine("rule", threshold=0.1, risk_constant=2.3)
    assert isinstance(engine, RuleBasedEngine)
    assert engine.threshold == 0.1
    assert engine.risk_constant == 2.3


def test_build_unknown_kind_raises():
    with pytest.raises(ValueError):
        build_engine("not-a-real-kind")


def test_rule_engine_is_never_cached():
    engine = build_engine("rule", threshold=0.1, risk_constant=2.3, cache=True)
    assert isinstance(engine, RuleBasedEngine)


def test_llm_engine_is_wrapped_with_cache(monkeypatch):
    class DummyEngine:
        name = "llm:dummy:model"

    monkeypatch.setattr(factory, "LLMChatEngine", lambda **kwargs: DummyEngine())
    engine = build_engine("llm", provider="ollama", model="phi3", cache=True)
    assert isinstance(engine, CachedDecisionEngine)


def test_hybrid_engine_applies_cache_only_to_secondary(monkeypatch):
    class DummyEngine:
        def __init__(self, **kwargs):
            self.name = "dummy"

    monkeypatch.setattr(factory, "LLMChatEngine", lambda **kwargs: DummyEngine())
    engine = build_engine(
        "hybrid",
        primary_kind="rule",
        primary_kwargs={"threshold": 0.1, "risk_constant": 2.3},
        secondary_kind="llm",
        secondary_kwargs={"provider": "ollama", "model": "phi3"},
        secondary_rate=0.03,
        cache=True,
    )
    assert isinstance(engine, HybridEngine)
    assert isinstance(engine.primary, RuleBasedEngine)
    assert isinstance(engine.secondary, CachedDecisionEngine)
