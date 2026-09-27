from unittest.mock import MagicMock

from decision.hybrid import HybridEngine
from decision.types import CitizenDecisionState, DecisionResult


def _state():
    return CitizenDecisionState(
        agent_id=1, hardship=0.8, risk_aversion=0.2, legitimacy=0.5,
        grievance=0.4, cops_visible=0, actives_visible=0,
    )


def test_uses_secondary_engine_when_random_below_rate():
    primary = MagicMock()
    primary.name = "rule"
    secondary = MagicMock()
    secondary.name = "llm:openai:gpt-4o-mini"
    secondary.decide.return_value = DecisionResult(
        active=True, probability=0.9, source=secondary.name, latency_ms=5.0
    )

    rng = MagicMock()
    rng.random.return_value = 0.0  # siempre menor que secondary_rate
    engine = HybridEngine(primary, secondary, secondary_rate=0.5, rng=rng)

    result = engine.decide(_state())

    secondary.decide.assert_called_once()
    primary.decide.assert_not_called()
    assert result.active is True


def test_falls_back_to_primary_when_secondary_errors():
    primary = MagicMock()
    primary.name = "rule"
    primary.decide.return_value = DecisionResult(active=False, probability=0.0, source="rule", latency_ms=0.1)
    secondary = MagicMock()
    secondary.name = "llm:ollama:phi3"
    secondary.decide.return_value = DecisionResult(
        active=False, probability=0.0, source=secondary.name, latency_ms=5.0, error="timeout"
    )

    rng = MagicMock()
    rng.random.return_value = 0.0
    engine = HybridEngine(primary, secondary, secondary_rate=1.0, rng=rng)

    result = engine.decide(_state())

    primary.decide.assert_called_once()
    assert result.source == "rule"
    assert result.error is None


def test_never_uses_secondary_when_rate_is_zero():
    primary = MagicMock()
    primary.name = "rule"
    primary.decide.return_value = DecisionResult(active=False, probability=0.0, source="rule", latency_ms=0.1)
    secondary = MagicMock()
    secondary.name = "llm:ollama:phi3"

    rng = MagicMock()
    rng.random.return_value = 0.999
    engine = HybridEngine(primary, secondary, secondary_rate=0.0, rng=rng)

    engine.decide(_state())

    secondary.decide.assert_not_called()


def test_parallel_secondary_prefetches_selected_citizens_in_one_batch():
    import random

    primary = MagicMock()
    primary.name = "rule"
    primary.decide.side_effect = lambda s: DecisionResult(active=False, probability=0.0, source="rule", latency_ms=0.0)
    secondary = MagicMock()
    secondary.name = "jev:jev-latest"
    secondary.decide_many.side_effect = lambda states: [
        DecisionResult(active=True, probability=0.9, source=secondary.name, latency_ms=5.0) for _ in states
    ]

    engine = HybridEngine(primary, secondary, secondary_rate=0.5, rng=random.Random(0), parallel_secondary=True)
    citizens = list(range(20))
    state_of = lambda agent_id: CitizenDecisionState(
        agent_id=agent_id, hardship=0.8, risk_aversion=0.2, legitimacy=0.5,
        grievance=0.4, cops_visible=0, actives_visible=0,
    )

    engine.prepare_step(citizens, state_of)
    results = [engine.decide(state_of(i)) for i in citizens]
    engine.end_step()

    selected = len(secondary.decide_many.call_args.args[0])
    assert secondary.decide_many.call_count == 1
    assert secondary.decide.call_count == 0
    assert 0 < selected < 20
    assert sum(r.source == secondary.name for r in results) == selected
    assert engine._prefetched is None
