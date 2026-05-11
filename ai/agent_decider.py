"""
Decider Agent — ai/agent_decider.py

Agent 2: Primește rezumatul (A1) și regula (A0) și decide ce face cu fișierul.
Uses PydanticOutputParser with the class ActionDecision(status, suggested_name, suggested_folder).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

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
    suggested_name: str = Field(
        ...,
        description="Numele sugerat pentru fișier (conform naming_convention din regulă). Dacă e carantină, se păstrează numele original.",
    )
    suggested_folder: str = Field(
        ...,
        description="Folderul de destinație. Dacă e 'quarantine', valoarea va fi 'Quarantine'.",
    )

    @field_validator("suggested_name")
    @classmethod
    def sanitize_filename(cls, v: str) -> str:
        """Asigură-te că numele fișierului nu conține caractere invalide."""
        # Îndepărtăm caracterele care ar putea cauza erori de filepath
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", v)
        return sanitized


# =====================================================================
#  Prompt template
# =====================================================================

_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert decision-making agent for the ClutterKill system.
Your job is to analyze a document summary and a set of organization rules, and decide if the document should be moved to the correct folder or placed in quarantine.

Rule Category: {rule_category}
Target Folder: {rule_folder}
Naming Convention: {rule_naming}

Document Summary:
{document_summary}

Original Filename: {original_filename}

Instructions:
1. If the Document Summary MATCHES the Rule Category, your status must be "move".
2. If it DOES NOT match, or if you are unsure, your status must be "quarantine".
3. Calculate the new filename based on the Naming Convention. If the naming convention includes {{original_filename}}, replace it with the actual original filename.
4. If the status is "quarantine", the folder must be "Quarantine".
5. If the status is "quarantine", the suggested_name MUST be exactly the Original Filename.

IMPORTANT: You must return ONLY the raw JSON object containing the actual values. Do NOT return a JSON schema, and do NOT wrap your answer in markdown fences (like ```json).

{format_instructions}
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

        raw_output = self._chain.invoke(
            {
                "rule_category": rule.category,
                "rule_folder": rule.folder_structure,
                "rule_naming": rule.naming_convention,
                "document_summary": summary,
                "original_filename": original_filename,
            }
        )

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
    print("TEST 1: Sanitizare și Retry")
    try:
        decision1 = agent.decide(test_summary_match, test_filename, test_rule)
        print("Output JSON (observă cum / a fost înlocuit):")
        print(decision1.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}")
    print(f"{'=' * 60}\n")
