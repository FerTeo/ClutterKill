"""
Decider Agent — ai/agent_decider.py

Agent 2: Primește rezumatul (A1) și regula (A0) și decide ce face cu fișierul.
Uses PydanticOutputParser with the class ActionDecision(status, suggested_name, suggested_folder).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal, Optional

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from ai.llm_config import get_llm, MODEL_CLASSIFIER
from ai.agent_compiler import CompiledRule

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2

# =====================================================================
#  Pydantic schema — formatul deciziei
# =====================================================================


class ActionDecision(BaseModel):
    """Decizia finală luată de Agent 2."""

    status: Literal["move", "quarantine"] = Field(
        ...,
        description="Statusul deciziei: 'move' dacă fișierul corespunde regulii, 'quarantine' dacă nu sau dacă informațiile lipsesc.",
    )
    suggested_name: Optional[str] = Field(
        default=None,
        description="Numele sugerat pentru fișier (conform naming_convention din regulă). Dacă e carantină, se păstrează numele original.",
    )
    suggested_folder: Optional[str] = Field(
        default=None,
        description="Folderul de destinație. Dacă e 'quarantine', valoarea va fi 'Quarantine'.",
    )

    @field_validator("suggested_name")
    @classmethod
    def sanitize_filename(cls, v: str | None) -> str | None:
        """Asigură-te că numele fișierului nu conține caractere invalide."""
        if not v:
            return v
        # Îndepărtăm caracterele care ar putea cauza erori de filepath
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", v)
        return sanitized


# =====================================================================
#  Prompt template
# =====================================================================

_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert decision-making agent for the ClutterKill system.
Your job is to analyze a document summary and decide the exact folder and filename based strictly on the provided templates.

{format_instructions}

Preset Query/Intent: {rule_category}
Target Folder Template: {rule_folder}
Naming Convention Template: {rule_naming}

Document Summary:
{document_summary}

Original Filename: {original_filename}

Instructions:
1. CHECK PRESET QUERY FIRST: Does the Document Summary match the Preset Query/Intent?
   - The query might be broad (e.g., "Toate fișierele", "Pozele mele", "Orice imagine").
   - If YES, or if you are UNSURE but it doesn't explicitly contradict the query -> status "move".
   - ONLY if the Document explicitly contradicts the query (e.g., query is "Facturi emag" but the document is a "Poza cu un caine") -> status "quarantine".
3. Build the TARGET FOLDER:
   - The user wants all files to go directly into the main output folder (Flattened structure).
   - Therefore, YOU MUST output exactly "." (a single dot) for the target folder.
4. Build the NEW FILENAME using the Naming Convention Template:
   - Similarly, replace ALL bracketed variables (e.g. `[Emitent]`, `[SubiectAI]`) with extracted/deduced values.
   - Example: `[An]_[Emitent]_[SubiectAI]` -> `2023_eMAG_Laptop_Gaming`.
   - If the template is literally "{{original_filename}}", keep the original filename.
5. CRITICAL: The new filename MUST keep the exact same file extension as the Original Filename (e.g. .pdf, .docx, .jpeg).
6. CRITICAL: Do NOT include spaces in the filename or folder name. Use underscores (_) or CamelCase instead.
7. If the status is "quarantine", the folder must be exactly "Quarantine".

CRITICAL: You must return ONLY the raw JSON object containing the ACTUAL evaluated folder and filename based on the templates.
"""

_REPAIR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You previously attempted to output a JSON decision but your JSON was invalid or did not match the schema. "
            "Fix the JSON below so it matches the required schema exactly. "
            "Output ONLY valid JSON, nothing else.",
        ),
        ("human", "Broken output:\n{broken_json}\n\nValidation error:\n{error}"),
    ]
)

# =====================================================================
#  DeciderAgent
# =====================================================================


class DeciderAgent:
    """Agent that decides whether a file matches a rule based on its summary.

    Usage::

        agent = DeciderAgent()
        decision = agent.decide(summary, original_filename, rule)
        print(decision.model_dump_json())
    """

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm or get_llm(model=MODEL_CLASSIFIER)
        self._parser = PydanticOutputParser(pydantic_object=ActionDecision)

        self._prompt = PromptTemplate(
            template=_SYSTEM_PROMPT_TEMPLATE,
            input_variables=[
                "rule_category",
                "rule_folder",
                "rule_naming",
                "document_summary",
                "original_filename",
            ],
            partial_variables={
                "format_instructions": self._parser.get_format_instructions()
            },
        )

        self._chain = self._prompt | self._llm | StrOutputParser()
        self._repair_chain = _REPAIR_PROMPT | self._llm | StrOutputParser()

    # ── public API ───────────────────────────────────────────────────

    def decide(
        self, summary: str, original_filename: str, rule: CompiledRule
    ) -> ActionDecision:
        """Decide the fate of a document.

        Parameters
        ----------
        summary : str
            Technical summary extracted from the document.
        original_filename : str
            The original name of the file.
        rule : CompiledRule
            The compiled rule containing category, folder, and naming.

        Returns
        -------
        ActionDecision
            Validated Pydantic model with status, suggested_name, and suggested_folder.
        """
        logger.info(
            "DeciderAgent: Evaluăm documentul '%s' față de regula '%s'",
            original_filename,
            rule.category,
        )

        import time

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                raw_output = self._chain.invoke(
                    {
                        "rule_category": rule.category,
                        "rule_folder": rule.folder_structure,
                        "rule_naming": rule.naming_convention,
                        "document_summary": summary,
                        "original_filename": original_filename,
                    }
                )
                break
            except Exception as e:
                if "429" in str(e) and attempt < max_attempts - 1:
                    logger.warning(
                        f"API Rate Limit Hit (429) in Decider. Sleeping 15s... (Attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(15)
                else:
                    raise e

        last_error: Exception | None = None
        current_output = raw_output

        for attempt in range(_MAX_RETRIES + 1):
            try:
                # Funcția self._parser.parse suportă markdown fences fallback din LangChain
                return self._parser.parse(current_output)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Parse attempt %d/%d failed: %s",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    current_output = self._repair_chain.invoke(
                        {"broken_json": current_output, "error": str(exc)}
                    )

        logger.error("Eroare în timpul deciziei (după retry-uri): %s", last_error)
        raise ValueError(
            f"Failed to parse decision after retries: {last_error}"
        ) from last_error


# ─── Quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = DeciderAgent()

    test_rule = CompiledRule(
        category="factură",
        folder_structure="Facturi_Luna_Curenta",
        naming_convention="factura_enel_10/20.pdf",  # intenționat cu caractere invalide pentru test
    )

    test_summary_match = "Emitent: ENEL SA, Dată: 12.05.2023, Sumă: 150 RON, Tip: Factură energie electrică."

    test_filename = "doc_scanned_123.pdf"

    print(f"\n{'=' * 60}")
    print("TEST 1: Sanitizare si Retry")
    try:
        decision1 = agent.decide(test_summary_match, test_filename, test_rule)
        print("Output JSON (observă cum / a fost înlocuit):")
        print(decision1.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}")
    print(f"{'=' * 60}\n")
