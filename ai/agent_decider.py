"""
Decider Agent — ai/agent_decider.py

Agent 2: Primește rezumatul (A1) și regula (A0) și decide ce face cu fișierul.
Uses PydanticOutputParser with the class ActionDecision(status, suggested_name, suggested_folder).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from ai.llm_config import get_llm, MODEL_CLASSIFIER
from ai.agent_compiler import CompiledRule

logger = logging.getLogger(__name__)

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

        self._chain = self._prompt | self._llm | self._parser

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
        try:
            result = self._chain.invoke(
                {
                    "rule_category": rule.category,
                    "rule_folder": rule.folder_structure,
                    "rule_naming": rule.naming_convention,
                    "document_summary": summary,
                    "original_filename": original_filename,
                }
            )
            return result
        except Exception as e:
            logger.error("Eroare în timpul deciziei: %s", e)
            raise


# ─── Quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = DeciderAgent()

    test_rule = CompiledRule(
        category="factură",
        folder_structure="Facturi_Luna_Curenta",
        naming_convention="factura_{original_filename}",
    )

    test_summary_match = "Emitent: ENEL SA, Dată: 12.05.2023, Sumă: 150 RON, Tip: Factură energie electrică."
    test_summary_fail = "Emitent: N/A, Dată: N/A, Sumă: N/A, Tip: Poză pisică."

    test_filename = "doc_scanned_123.pdf"

    print(f"\n{'=' * 60}")
    print("TEST 1: Document care se potrivește")
    try:
        decision1 = agent.decide(test_summary_match, test_filename, test_rule)
        print("Output JSON:")
        print(decision1.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}")

    print(f"\n{'=' * 60}")
    print("TEST 2: Document care NU se potrivește")
    try:
        decision2 = agent.decide(test_summary_fail, test_filename, test_rule)
        print("Output JSON:")
        print(decision2.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}")
    print(f"{'=' * 60}\n")
