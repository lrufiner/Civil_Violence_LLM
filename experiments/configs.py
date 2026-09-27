"""Presets de motores de decisión para correr experimentos comparativos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EnginePreset:
    key: str
    label: str
    kind: str  # "rule" | "llm" | "jev"
    kwargs: Dict[str, Any] = field(default_factory=dict)


PRESETS: List[EnginePreset] = [
    EnginePreset(key="rule", label="Regla matemática (Epstein)", kind="rule"),
    EnginePreset(
        key="ollama", label="LLM chat (Ollama local)", kind="llm",
        kwargs={"provider": "ollama", "model": "phi3"},
    ),
    EnginePreset(
        key="openai", label="LLM chat (OpenAI)", kind="llm",
        kwargs={"provider": "openai", "model": "gpt-4o-mini"},
    ),
    EnginePreset(
        key="anthropic", label="LLM chat (Anthropic Claude)", kind="llm",
        kwargs={"provider": "anthropic", "model": "claude-haiku-4-5"},
    ),
    EnginePreset(
        key="jev", label="Jev (TypeSafe AI System One)", kind="jev",
        kwargs={"model": "jev-latest"},
    ),
]
