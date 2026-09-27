"""Factory para instanciar chat models de LangChain a partir de configuración simple.

Mantiene el resto del código independiente del SDK concreto de cada proveedor,
para poder cambiar de OpenAI/Anthropic/Ollama (o agregar uno nuevo) sin tocar
la lógica de decisión de los agentes.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic")


def get_chat_model(
    provider: str,
    model: str,
    *,
    temperature: float = 0.0,
    timeout: float = 10.0,
    max_retries: int = 2,
    **kwargs: Any,
) -> BaseChatModel:
    """Instancia el chat model de LangChain correspondiente al proveedor pedido.

    Las API keys se leen de las variables de entorno estándar de cada SDK
    (OPENAI_API_KEY, ANTHROPIC_API_KEY); Ollama no requiere key, solo un
    servidor local corriendo (por defecto en http://localhost:11434).
    """
    provider = provider.lower()
    try:
        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(model=model, temperature=temperature, **kwargs)
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model, temperature=temperature, timeout=timeout, max_retries=max_retries, **kwargs
            )
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model, temperature=temperature, timeout=timeout, max_retries=max_retries, **kwargs
            )
    except ImportError as exc:
        raise ImportError(
            f"Falta instalar el SDK de LangChain para el proveedor '{provider}'. "
            "Revisá requirements.txt e instalá las dependencias faltantes."
        ) from exc

    raise ValueError(f"Proveedor LLM no soportado: '{provider}'. Opciones válidas: {SUPPORTED_PROVIDERS}")
