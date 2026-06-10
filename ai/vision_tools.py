"""
Vision Tools — ai/vision_tools.py

Modul de analiză vizuală a imaginilor folosind modele multimodale (Vision AI).

Arhitectură
───────────
  imagine.jpg  ──►  _encode_image()  ──►  base64 string
                          │
                    describe_image()
                          │
                    ┌─────┴─────┐
                    │  Ollama   │  sau  │  Google  │
                    │ ck-vision │       │  Gemini  │
                    │ (llava:7b)│       │  Flash   │
                    └─────┬─────┘       └────┬─────┘
                          │                  │
                       "dog"              "dog"

Modelul Vision (ck-vision) este bazat pe llava:7b (~4.5GB) și returnează
UN SINGUR CUVÂNT care identifică subiectul principal al imaginii.

Provider-ul se selectează prin variabila de mediu AI_PROVIDER:
  - "ollama" (default): folosește ck-vision local prin Docker
  - "google": folosește Google Gemini multimodal (necesită GOOGLE_API_KEY)

Utilizare:
    from ai.vision_tools import describe_image
    result = describe_image("/path/to/photo.jpg")  # → "dog"

Dependințe:
    - Ollama container cu modelul ck-vision creat:
      docker exec -it clutterkill_ollama ollama create ck-vision -f /app/ai/Modelfile.vision
    - SAU GOOGLE_API_KEY setat în .env cu AI_PROVIDER=google
"""

import base64
import logging
import os
from pathlib import Path
from typing import Union

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# Replicăm defaulturile din llm_config pentru a fi safe, sau putem importa
_DEFAULT_PROVIDER = "ollama"
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
_DEFAULT_GOOGLE_MODEL = "gemini-flash-lite-latest"


def _encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def describe_image(path: Union[str, Path]) -> str:
    """
    Trimite imaginea către un model Multimodal (Vision) pentru a obține o descriere
    vizuală a obiectelor sau textului prezent în poză.
    """
    file_path = Path(path)
    if not file_path.exists():
        logger.error(f"Imaginea nu a fost găsită: {file_path}")
        return ""

    try:
        base64_image = _encode_image(file_path)
        ext = file_path.suffix.lower()
        mime_type = "image/jpeg"
        if ext == ".png":
            mime_type = "image/png"
        elif ext == ".bmp":
            mime_type = "image/bmp"

        provider = os.getenv("AI_PROVIDER", _DEFAULT_PROVIDER).lower()

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Analyze this image and suggest a highly descriptive, clean filename for it. Use PascalCase or underscores (e.g. Dog_Playing_Park.jpeg, Vodafone_Invoice_Summary.png, Python_Code_Screenshot.png). Reply ONLY with the exact filename.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                },
            ]
        )

        if provider == "google":
            from google import genai
            from google.genai.errors import ClientError
            import time
            
            api_key = os.getenv("GOOGLE_API_KEY")
            client = genai.Client(api_key=api_key)
            google_model = os.getenv("GOOGLE_MODEL_NAME", _DEFAULT_GOOGLE_MODEL)
            
            prompt = "Analyze this image and suggest a concise, 2-3 word descriptive filename for it. Use PascalCase. DO NOT INCLUDE ANY EXTENSION like .jpeg or .png in your reply. Example: Gray_Cottage, Rural_Stop_Sign, Yellow_Corvette. Reply ONLY with the exact name."
            
            from PIL import Image
            img = Image.open(file_path)
            
            try:
                response = client.models.generate_content(model=google_model, contents=[prompt, img])
                return response.text.strip()
            except Exception as e:
                if "429" in str(e):
                    logger.warning("API Rate Limit Hit (429). Sleeping 15 seconds and retrying...")
                    time.sleep(15)
                    response = client.models.generate_content(model=google_model, contents=[prompt, img])
                    return response.text.strip()
                else:
                    raise e

        elif provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL)
            ollama_llm = ChatOllama(model="ck-vision", base_url=base_url, temperature=0.1)
            response = ollama_llm.invoke([message])
            return str(response.content).strip()

        return ""

    except Exception as e:
        logger.error(f"Eroare la procesarea Vision AI pentru {file_path}: {e}")
        return f"Eroare Vision AI: {e}"
