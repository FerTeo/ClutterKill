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
from dotenv import load_dotenv

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

# Încarcă variabilele de mediu din fișierul .env, dacă există
load_dotenv()

logger = logging.getLogger(__name__)

# ─── Defaults (match docker-compose.yml & .env.example) ─────────────
_DEFAULT_PROVIDER = "ollama"
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
_DEFAULT_REQUEST_TIMEOUT = 300.0  # seconds — CPU inference can take minutes

_DEFAULT_GOOGLE_MODEL = "gemini-flash-lite-latest"

# Model registry — one entry per Modelfile
MODEL_CLASSIFIER = "ck-model"  # ai/Modelfile
MODEL_EXTRACTOR = "ck-extractor"  # ai/Modelfile.extractor


# =====================================================================
#  Public API
# =====================================================================


def get_llm(
    *,
    model: str = MODEL_CLASSIFIER,
    temperature: float | None = None,
    num_ctx: int | None = None,
    timeout: float | None = None,
) -> BaseChatModel:
    """Return a chat model instance based on chosen AI_PROVIDER.

    Parameters
    ----------
    model : str
        Ollama model name or placeholder. For Google, uses the
        defined DEFAULT_GOOGLE_MODEL override.
    temperature : float, optional
        Override sampling temperature (default: 0.1).
    num_ctx : int, optional
        Override context-window size (Ollama only).
    timeout : float, optional
        Override HTTP request timeout (default: 120 s).

    Returns
    -------
    BaseChatModel
        A LangChain chat-model instance ready for ``.invoke()`` /
        ``.ainvoke()`` / agent binding.
    """
    provider = os.getenv("AI_PROVIDER", _DEFAULT_PROVIDER).lower()

    if provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required when AI_PROVIDER='google'")

        google_model = os.getenv("GOOGLE_MODEL_NAME", _DEFAULT_GOOGLE_MODEL)
        temp = temperature if temperature is not None else 0.1

        logger.info(
            "Initializing ChatGoogleGenerativeAI  model=%s",
            google_model,
        )

        g_llm = ChatGoogleGenerativeAI(
            model=google_model,
            temperature=temp,
            google_api_key=api_key,
        )
        return g_llm

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
