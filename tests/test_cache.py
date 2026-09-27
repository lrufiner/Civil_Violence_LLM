from unittest.mock import MagicMock

from decision.cache import CachedDecisionEngine
from decision.types import CitizenDecisionState, DecisionResult


def _state(**overrides):
    base = dict(
        agent_id=1, hardship=0.8, risk_aversion=0.2, legitimacy=0.5,
        grievance=0.4, cops_visible=0, actives_visible=0,
    )
    base.update(overrides)
    return CitizenDecisionState(**base)


def test_second_call_with_equivalent_state_hits_cache():
    inner = MagicMock()
    inner.name = "llm:openai:gpt-4o-mini"
    inner.decide.return_value = DecisionResult(active=True, probability=0.9, source=inner.name, latency_ms=100.0)

    engine = CachedDecisionEngine(inner, precision=2)

    engine.decide(_state())
    result = engine.decide(_state())

    assert inner.decide.call_count == 1
    assert result.from_cache is True
    assert engine.hits == 1
    assert engine.misses == 1


def test_errors_are_not_cached():
    inner = MagicMock()
    inner.name = "jev:jev-latest"
    inner.decide.return_value = DecisionResult(
        active=False, probability=0.0, source=inner.name, latency_ms=10.0, error="boom"
    )

    engine = CachedDecisionEngine(inner, precision=2)
    engine.decide(_state())
    engine.decide(_state())

    assert inner.decide.call_count == 2


def test_states_rounded_differently_are_not_cache_hits():
    inner = MagicMock()
    inner.name = "jev:jev-latest"
    inner.decide.return_value = DecisionResult(active=False, probability=0.1, source=inner.name, latency_ms=10.0)

    engine = CachedDecisionEngine(inner, precision=2)
    engine.decide(_state(grievance=0.40))
    engine.decide(_state(grievance=0.55))

    assert inner.decide.call_count == 2


def test_count_cap_groups_large_visible_counts():
    inner = MagicMock()
    inner.name = "jev:jev-latest"
    inner.decide.return_value = DecisionResult(active=False, probability=0.1, source=inner.name, latency_ms=10.0)

    engine = CachedDecisionEngine(inner, precision=1, count_cap=5)
    engine.decide(_state(cops_visible=7, actives_visible=9))
    engine.decide(_state(cops_visible=12, actives_visible=5))

    assert inner.decide.call_count == 1


def test_hits_are_resampled_for_stochastic_engines():
    inner = MagicMock()
    inner.name = "jev:jev-latest"
    inner.stochastic = True
    inner.decide.return_value = DecisionResult(active=False, probability=0.7, source=inner.name, latency_ms=10.0)
    inner.resample.side_effect = lambda r: DecisionResult(
        active=True, probability=r.probability, source=r.source, latency_ms=r.latency_ms, from_cache=r.from_cache
    )

    engine = CachedDecisionEngine(inner, precision=2)
    engine.decide(_state())
    hit = engine.decide(_state())

    assert inner.resample.call_count == 1
    assert hit.active is True and hit.from_cache is True


def test_decide_many_queries_each_missing_key_once():
    inner = MagicMock()
    inner.name = "jev:jev-latest"
    inner.decide_many.side_effect = lambda states: [
        DecisionResult(active=False, probability=0.1, source=inner.name, latency_ms=10.0) for _ in states
    ]

    engine = CachedDecisionEngine(inner, precision=1)
    results = engine.decide_many([_state(agent_id=1), _state(agent_id=2), _state(agent_id=3, grievance=0.9)])

    assert len(inner.decide_many.call_args.args[0]) == 2  # dos claves distintas
    assert [r.from_cache for r in results] == [False, True, False]
    assert (engine.hits, engine.misses) == (1, 2)
