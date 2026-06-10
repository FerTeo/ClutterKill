"""
Compiler Agent — ai/agent_compiler.py

Agent 0: Traduce promptul natural în JSON (Reguli).
Uses PydanticOutputParser to extract CompiledRule from user natural language prompts.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from ai.llm_config import get_llm, MODEL_CLASSIFIER

logger = logging.getLogger(__name__)

# =====================================================================
#  Pydantic schema — formatul regulii
# =====================================================================


class CompiledRule(BaseModel):
    """Regulă de organizare fișiere, compilată dintr-un prompt natural."""

    category: str = Field(
        ...,
        description="Categoria sau tipul fișierului (e.g., 'factura', 'curs', 'contract').",
    )
    folder_structure: str = Field(
        ...,
        description="Structura de directoare unde va fi salvat fișierul (e.g., 'Facturi', 'Facultate/Materie').",
    )
    naming_convention: str = Field(
        default="{original_filename}",
        description="Convenția de denumire a fișierului. Dacă utilizatorul nu specifică, folosește un format implicit sau '{original_filename}'.",
    )


# =====================================================================
#  Prompt template
# =====================================================================

_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert rule translator for the ClutterKill system.
Your job is to translate a user's natural language instruction about where and how to save files into a structured JSON rule.

{format_instructions}

User instruction: "{user_prompt}"

Extract the category, folder structure, and naming convention.
CRITICAL RULES FOR EXTRACTION:
1. CATEGORY: If the user instruction applies to ALL files without filtering (e.g. "organize them", "rename them", "toate", "toate pozele", "orice"), set category to "any". Otherwise, extract the specific category (e.g. "factura").
2. NAMING CONVENTION: If the user explicitly asks to give files suggestive names, new names, or rename them (e.g. "da le nume sugestive", "redenumeste-le", "nume dupa continut", "nume sugestiv"), you MUST set naming_convention to "descriptive_name_based_on_content". If they do not ask for renames, set it to "{{original_filename}}".

CRITICAL: You must return ONLY the raw JSON object containing the ACTUAL values based on the user instruction. Do NOT return a JSON schema. Do NOT return properties definitions. DO NOT echo back the format instructions.

Example of expected valid output:
{{
  "category": "factura",
  "folder_structure": "Facturi",
  "naming_convention": "factura_data.pdf"
}}
"""


# =====================================================================
#  CompilerAgent
# =====================================================================


class CompilerAgent:
    """Agent that translates natural language prompts into structured JSON rules.

    Usage::

        agent = CompilerAgent()
        rule = agent.compile("Cursurile merg în folderul Facultate/Materie")
        print(rule.model_dump_json())
    """

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm or get_llm(model=MODEL_CLASSIFIER)
        self._parser = PydanticOutputParser(pydantic_object=CompiledRule)

        self._prompt = PromptTemplate(
            template=_SYSTEM_PROMPT_TEMPLATE,
            input_variables=["user_prompt"],
            partial_variables={
                "format_instructions": self._parser.get_format_instructions()
            },
        )

        self._chain = self._prompt | self._llm | self._parser

    # ── public API ───────────────────────────────────────────────────

    def compile(self, user_prompt: str) -> CompiledRule:
        """Translate a natural language prompt into a CompiledRule.

        Parameters
        ----------
        user_prompt : str
            Natural language instruction from the user (e.g., "facturile în folderul X").

        Returns
        -------
        CompiledRule
            Validated Pydantic model with category, folder_structure, and naming_convention.
        """
        logger.info("CompilerAgent: compiling prompt: '%s'", user_prompt)
        try:
            import time
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    result = self._chain.invoke({"user_prompt": user_prompt})
                    return result
                except Exception as loop_e:
                    if "429" in str(loop_e) and attempt < max_attempts - 1:
                        logger.warning(f"API Rate Limit Hit (429) in Compiler. Sleeping 15s... (Attempt {attempt+1}/{max_attempts})")
                        time.sleep(15)
                    else:
                        raise loop_e
        except Exception as e:
            logger.error("Failed to compile rule: %s", e)
            raise


# ─── Quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = CompilerAgent()

    test_prompts = [
        "Cursurile merg în folderul Facultate/Materie",
        "facturile în folderul Facturi_Curente și le denumești factura_data.pdf",
    ]

    for p in test_prompts:
        print(f"\n{'=' * 60}")
        print(f"Input: {p}")
        try:
            res = agent.compile(p)
            print(f"Output JSON: {res.model_dump_json(indent=2)}")
        except Exception as e:
            print(f"Error: {e}")
        print(f"{'=' * 60}")
