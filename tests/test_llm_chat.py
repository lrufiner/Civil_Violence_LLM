from unittest.mock import MagicMock, patch

from decision.llm_chat import LLMChatEngine
from decision.types import CitizenDecisionState, RebellionDecision


def _state():
    return CitizenDecisionState(
        agent_id=1, hardship=0.8, risk_aversion=0.2, legitimacy=0.5,
        grievance=0.4, cops_visible=1, actives_visible=1,
    )


@patch("decision.llm_chat.get_chat_model")
def test_decide_returns_structured_result(mock_get_chat_model):
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value.invoke.return_value = RebellionDecision(
        active=True, confidence=0.9
    )
    mock_get_chat_model.return_value = mock_model

    engine = LLMChatEngine(provider="openai", model="gpt-4o-mini")
    result = engine.decide(_state())

    assert result.active is True
    assert result.confidence == 0.9
    assert result.source == "llm:openai:gpt-4o-mini"
    assert result.error is None


@patch("decision.llm_chat.get_chat_model")
def test_decide_captures_errors_without_raising(mock_get_chat_model):
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value.invoke.side_effect = RuntimeError("timeout")
    mock_get_chat_model.return_value = mock_model

    engine = LLMChatEngine(provider="ollama", model="phi3")
    result = engine.decide(_state())

    assert result.error == "timeout"
    assert result.active is False


@patch("decision.llm_chat.get_chat_model")
def test_decide_exposes_reason_as_explanation(mock_get_chat_model):
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value.invoke.return_value = RebellionDecision(
        active=False, confidence=0.8, reason="  Hay demasiada policía cerca, no vale el riesgo. "
    )
    mock_get_chat_model.return_value = mock_model

    result = LLMChatEngine(provider="openai", model="gpt-4o-mini").decide(_state())

    assert result.explanation == "Hay demasiada policía cerca, no vale el riesgo."


@patch("decision.llm_chat.get_chat_model")
def test_prompt_language_follows_setting(mock_get_chat_model):
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value.invoke.return_value = RebellionDecision(active=False, confidence=0.5)
    mock_get_chat_model.return_value = mock_model

    LLMChatEngine(provider="ollama", model="phi3", language="en").decide(_state())

    prompt = mock_model.with_structured_output.return_value.invoke.call_args.args[0]
    assert "You are a citizen" in prompt and "in English" in prompt
