"""
LLM Configuration & Factory — ai/llm_config.py

Centralized factory for obtaining LLM instances used by ALL agents in
the ClutterKill pipeline:

    - ``ck-model``       → classification agent (Agent 0 Compiler, Agent 2 Decider)
    - ``ck-extractor``   → extraction agent (Agent 1 Extractor)

Reads configuration from environment variables so it works transparently
both on the host machine and inside the Docker ``app`` container:

    AI_PROVIDER      = "ollama" | "google"         (default: "ollama")
    OLLAMA_BASE_URL  = "http://ollama:11434"        (Docker-internal default)
    GOOGLE_API_KEY   = "..."                        (only when provider is google)

Model creation (inside Docker)::

    docker exec -it clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile
    docker exec -it clutterkill_ollama ollama create ck-extractor -f /app/ai/Modelfile.extractor

Usage::

    from ai.llm_config import get_llm
    llm = get_llm()                          # default → ck-model (classification)
    llm = get_llm(model="ck-extractor")      # extraction agent
"""

from __future__ import annotations

import logging
import os

from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)

# ─── Defaults (match docker-compose.yml & .env.example) ─────────────
_DEFAULT_PROVIDER = "ollama"
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
_DEFAULT_REQUEST_TIMEOUT = 120.0    # seconds — OCR docs can be big

# Model registry — one entry per Modelfile
MODEL_CLASSIFIER = "ck-model"           # ai/Modelfile
MODEL_EXTRACTOR = "ck-extractor"        # ai/Modelfile.extractor


# =====================================================================
#  Public API
# =====================================================================

def get_llm(
    *,
    model: str = MODEL_CLASSIFIER,
    temperature: float | None = None,
    num_ctx: int | None = None,
    timeout: float | None = None,
) -> ChatOllama:
    """Return a ChatOllama instance for the requested model.

    Parameters
    ----------
    model : str
        Ollama model name. Use the module constants:
        ``MODEL_CLASSIFIER`` (default) or ``MODEL_EXTRACTOR``.
    temperature : float, optional
        Override sampling temperature (model default: 0.1).
    num_ctx : int, optional
        Override context-window size.
    timeout : float, optional
        Override HTTP request timeout (default: 120 s).

    Returns
    -------
    ChatOllama
        A LangChain chat-model instance ready for ``.invoke()`` /
        ``.ainvoke()`` / agent binding.
    """
    provider = os.getenv("AI_PROVIDER", _DEFAULT_PROVIDER).lower()

    if provider == "google":
        # Future: return ChatGoogleGenerativeAI(...)
        raise NotImplementedError(
            "Google AI provider is not yet implemented. "
            "Set AI_PROVIDER=ollama or leave unset."
        )

    if provider != "ollama":
        raise ValueError(
            f"Unknown AI_PROVIDER '{provider}'. Expected 'ollama' or 'google'."
        )

    base_url = os.getenv("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL)
    tout = timeout if timeout is not None else _DEFAULT_REQUEST_TIMEOUT

    kwargs: dict = {
        "base_url": base_url,
        "model": model,
        "timeout": tout,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if num_ctx is not None:
        kwargs["num_ctx"] = num_ctx

    logger.info(
        "Initializing ChatOllama  model=%s  base_url=%s  %s",
        model,
        base_url,
        {k: v for k, v in kwargs.items() if k not in ("base_url", "model", "timeout")},
    )

    llm = ChatOllama(**kwargs)
    logger.info("ChatOllama instance ready  (%s).", model)
    return llm


# ── Convenience aliases ──────────────────────────────────────────────
get_local_llm = get_llm


# ─── Quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _llm = get_llm()
    _resp = _llm.invoke("Hello — are you alive?")
    print(f"[{MODEL_CLASSIFIER}] responded: {_resp.content}")
