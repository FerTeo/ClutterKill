"""
LLM Factory

Returns the configured language model based on the LLM_MODE environment variable.

Modes:
  openai  — Uses the OpenAI API (requires OPENAI_API_KEY in .env)
  local   — Uses a local GGUF model via llama.cpp (requires MODEL_PATH in .env)
"""
import os


def get_llm():
    mode = os.getenv("LLM_MODE", "openai").lower()

    if mode == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
        )

    elif mode == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0,
        )

    elif mode == "local":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "gemma4"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )

    else:
        raise ValueError(
            f"Unknown LLM_MODE: '{mode}'. "
            "Set LLM_MODE to 'openai', 'gemini', or 'local' in your .env file."
        )
