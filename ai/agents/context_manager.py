"""
Context Window Management

Acest modul se asigură că textul extras din fișiere (PDF-uri lungi, etc.)
nu depășește limita de tokeni a modelului LLM (pentru a evita erori de overflow).
Folosim `tiktoken` ca o aproximare rapidă și robustă.
"""
import logging
import tiktoken

logger = logging.getLogger(__name__)

# Folosim o codificare standard. "cl100k_base" este folosit de OpenAI (GPT-3.5/4)
# și este o aproximare excelentă și rapidă pentru majoritatea LLM-urilor moderne (inclusiv Llama3).
_ENCODING_NAME = "cl100k_base"
_DEFAULT_MAX_TOKENS = 2000

def truncate_to_token_limit(text: str, max_tokens: int = _DEFAULT_MAX_TOKENS) -> str:
    """
    Trunchiază textul dacă depășește limita de tokeni.
    Păstrează primele și ultimele porțiuni ale textului, deoarece adesea
    metadatele importante (titlu, data) sunt la început, iar semnăturile/totalurile la sfârșit.
    
    Args:
        text (str): Textul brut extras din document.
        max_tokens (int): Limita maximă de tokeni dorită.
        
    Returns:
        str: Textul trunchiat care se încadrează în limita de tokeni.
    """
    if not text:
        return ""

    try:
        encoding = tiktoken.get_encoding(_ENCODING_NAME)
    except Exception as e:
        logger.error(f"Eroare la inițializarea tiktoken: {e}")
        # Fallback rudimentar dacă tiktoken eșuează (aprox. 4 caractere per token)
        fallback_limit = max_tokens * 4
        if len(text) > fallback_limit:
            return text[:fallback_limit//2] + "\n...[TRUNCATED]...\n" + text[-fallback_limit//2:]
        return text

    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
        
    logger.info(f"Document prea lung ({len(tokens)} tokeni). Se trunchiază la {max_tokens} tokeni.")
    
    # Păstrăm 70% din început și 30% din final
    keep_start = int(max_tokens * 0.7)
    keep_end = max_tokens - keep_start - 10  # 10 tokeni rezervați pentru mesajul de [TRUNCATED]
    
    start_tokens = tokens[:keep_start]
    end_tokens = tokens[-keep_end:] if keep_end > 0 else []
    
    truncated_text = encoding.decode(start_tokens)
    truncated_text += "\n\n...[TEXT TRUNCHIAT DE CONTEXT MANAGER]...\n\n"
    if end_tokens:
        truncated_text += encoding.decode(end_tokens)
        
    return truncated_text

def count_tokens(text: str) -> int:
    """Returnează numărul estimat de tokeni dintr-un text."""
    if not text:
        return 0
    try:
        encoding = tiktoken.get_encoding(_ENCODING_NAME)
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4
