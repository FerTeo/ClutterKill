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

User instruction: "{user_prompt}"

Extract the category, folder structure, and naming convention.
If the naming convention is not explicitly stated, use a default placeholder like "{{original_filename}}" or infer a sensible one if the context implies it.

{format_instructions}
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
            # invoke the chain which formats the prompt, calls LLM, and parses output
            result = self._chain.invoke({"user_prompt": user_prompt})
            return result
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
