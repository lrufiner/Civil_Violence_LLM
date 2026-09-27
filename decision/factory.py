"""Factory central para construir cualquier `DecisionEngine` a partir de configuración."""

from __future__ import annotations

import random
from typing import Any, Optional

from .base import DecisionEngine
from .cache import CachedDecisionEngine
from .hybrid import HybridEngine
from .jev import JevDecisionEngine
from .llm_chat import LLMChatEngine
from .rule_based import RuleBasedEngine


def build_engine(
    kind: str,
    *,
    cache: bool = False,
    cache_precision: int = 2,
    cache_count_cap: Optional[int] = None,
    rng: Optional[random.Random] = None,
    **kwargs: Any,
) -> DecisionEngine:
    """Construye un `DecisionEngine` según `kind` ("rule" | "llm" | "jev" | "hybrid").

    `rng` se pasa a los motores estocásticos (hybrid, jev) para que una corrida
    sea reproducible con la semilla del modelo.

    Para "hybrid", el cache (si está habilitado) se aplica solo al motor secundario,
    que es el que suele ser costoso (LLM/Jev); el motor "rule" nunca se cachea.
    """
    if kind == "rule":
        return RuleBasedEngine(
            threshold=kwargs.get("threshold", 0.1),
            risk_constant=kwargs.get("risk_constant", 2.3),
        )

    if kind == "llm":
        engine: DecisionEngine = LLMChatEngine(
            provider=kwargs["provider"],
            model=kwargs["model"],
            prompt_template=kwargs.get("prompt_template"),
            temperature=kwargs.get("temperature", 0.0),
            timeout=kwargs.get("timeout", 10.0),
            max_retries=kwargs.get("max_retries", 2),
            max_concurrency=kwargs.get("max_concurrency", 4),
            language=kwargs.get("language", "es"),
        )
    elif kind == "jev":
        engine = JevDecisionEngine(
            model=kwargs.get("model", "jev-latest"),
            mode=kwargs.get("mode", "sample"),
            rng=rng,
            max_concurrency=kwargs.get("max_concurrency", 16),
            explain=kwargs.get("explain", True),
            language=kwargs.get("language", "es"),
        )
    elif kind == "hybrid":
        primary = build_engine(kwargs["primary_kind"], rng=rng, **kwargs.get("primary_kwargs", {}))
        secondary = build_engine(
            kwargs["secondary_kind"],
            cache=cache,
            cache_precision=cache_precision,
            cache_count_cap=cache_count_cap,
            rng=rng,
            **kwargs.get("secondary_kwargs", {}),
        )
        return HybridEngine(
            primary,
            secondary,
            secondary_rate=kwargs.get("secondary_rate", 0.03),
            rng=rng,
            parallel_secondary=kwargs.get("parallel_secondary", False),
        )
    else:
        raise ValueError(f"Tipo de motor de decisión desconocido: '{kind}'")

    if cache:
        engine = CachedDecisionEngine(engine, precision=cache_precision, count_cap=cache_count_cap)
    return engine
