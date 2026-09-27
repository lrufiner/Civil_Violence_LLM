from decision.rule_based import RuleBasedEngine
from decision.types import CitizenDecisionState


def _state(**overrides):
    base = dict(
        agent_id=1, hardship=0.8, risk_aversion=0.2, legitimacy=0.5,
        grievance=0.4, cops_visible=0, actives_visible=0,
    )
    base.update(overrides)
    return CitizenDecisionState(**base)


def test_rebels_when_grievance_exceeds_threshold():
    engine = RuleBasedEngine(threshold=0.1, risk_constant=2.3)
    result = engine.decide(_state(grievance=0.5, risk_aversion=0.1))
    assert result.active is True
    assert result.source == "rule"
    assert result.error is None


def test_stays_quiet_when_risk_too_high():
    engine = RuleBasedEngine(threshold=0.1, risk_constant=2.3)
    result = engine.decide(_state(grievance=0.2, risk_aversion=0.9, cops_visible=5, actives_visible=0))
    assert result.active is False


def test_more_cops_visible_increase_arrest_probability():
    engine = RuleBasedEngine(threshold=0.1, risk_constant=2.3)
    low = engine.decide(_state(cops_visible=0))
    high = engine.decide(_state(cops_visible=5))
    assert high.raw["arrest_probability"] > low.raw["arrest_probability"]
