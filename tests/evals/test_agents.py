"""
Evals pentru agenții AI din ClutterKill.

Testele de mai jos evaluează *calitatea logicii* agenților fără a necesita
un LLM real — LLM-ul este înlocuit cu un mock care returnează răspunsuri
pre-definite, similare cu ce ar produce un model real.

Sunt acoperite trei dimensiuni de calitate:
  1. Corectitudinea schema-ului (Pydantic parsing + validare)
  2. Logica de rutare (move vs. quarantine)
  3. Rezistența la output malformat (JSON repair loop)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from ai.agent_compiler import CompilerAgent, CompiledRule
from ai.agent_decider import ActionDecision, DeciderAgent
from ai.agent_extractor import ExtractionResult, ExtractorAgent


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers — construiesc mock-uri de LLM
# ─────────────────────────────────────────────────────────────────────────────


def _make_llm(response_text: str) -> MagicMock:
    """Returnează un LLM mock care produce întotdeauna `response_text`."""
    llm = MagicMock()
    # ExtractorAgent folosește llm.invoke(prompt_val).content
    msg = MagicMock()
    msg.content = response_text
    llm.invoke.return_value = msg
    # DeciderAgent și CompilerAgent folosesc chain-uri cu StrOutputParser/PydanticOutputParser,
    # deci mock-uim __or__ ca să suporte sintaxa `prompt | llm | parser`
    llm.__or__ = lambda self, other: _ChainMock(response_text, other)
    return llm


class _ChainMock:
    """Simulează un LangChain chain: ignoră prompt-ul și returnează mereu același text."""

    def __init__(self, text: str, next_step: Any) -> None:
        self._text = text
        self._next = next_step

    def __or__(self, other: Any) -> "_ChainMock":
        return _ChainMock(self._text, other)

    def invoke(self, _: Any) -> Any:
        # Dacă next_step e un parser Pydantic/Str, îl invocăm cu textul nostru
        if hasattr(self._next, "parse"):
            return self._next.parse(self._text)
        if hasattr(self._next, "invoke"):
            return self._next.invoke(self._text)
        return self._text


# ─────────────────────────────────────────────────────────────────────────────
#  EVAL 1 — ExtractorAgent: extrage corect entitățile dintr-o factură
# ─────────────────────────────────────────────────────────────────────────────

INVOICE_JSON = json.dumps(
    {
        "document_type": "invoice",
        "summary": "Factură ENEL SA, data 12.05.2023, sumă 150 RON.",
        "suggested_filename": "ENEL_Invoice_May2023",
        "entities": [
            {
                "field_name": "issuer",
                "value": "ENEL SA",
                "confidence": 0.98,
                "reasoning": "Menționat explicit ca emitent.",
            },
            {
                "field_name": "date",
                "value": "12.05.2023",
                "confidence": 0.97,
                "reasoning": "Data emisiunii factură.",
            },
            {
                "field_name": "total_amount",
                "value": "150 RON",
                "confidence": 0.95,
                "reasoning": "Suma totală de plată.",
            },
        ],
    }
)


@pytest.fixture()
def extractor_invoice() -> ExtractorAgent:
    return ExtractorAgent(llm=_make_llm(INVOICE_JSON))


def test_extractor_document_type(extractor_invoice: ExtractorAgent) -> None:
    result = extractor_invoice.extract("Factură ENEL...")
    assert result.document_type == "invoice"


def test_extractor_entity_count(extractor_invoice: ExtractorAgent) -> None:
    result = extractor_invoice.extract("Factură ENEL...")
    assert len(result.entities) == 3


def test_extractor_entity_values(extractor_invoice: ExtractorAgent) -> None:
    result = extractor_invoice.extract("Factură ENEL...")
    values = {e.field_name: e.value for e in result.entities}
    assert values["issuer"] == "ENEL SA"
    assert values["date"] == "12.05.2023"
    assert values["total_amount"] == "150 RON"


def test_extractor_confidence_scores(extractor_invoice: ExtractorAgent) -> None:
    """Toate entitățile dintr-o factură clară trebuie să aibă confidence >= 0.90."""
    result = extractor_invoice.extract("Factură ENEL...")
    low_conf = [e for e in result.entities if e.confidence < 0.90]
    assert low_conf == [], f"Entități cu confidence scăzut: {low_conf}"


def test_extractor_summary_length(extractor_invoice: ExtractorAgent) -> None:
    """Rezumatul tehnic trebuie să fie sub 200 de caractere."""
    result = extractor_invoice.extract("Factură ENEL...")
    assert len(result.get_technical_summary()) <= 200


def test_extractor_suggested_filename_no_extension(
    extractor_invoice: ExtractorAgent,
) -> None:
    """suggested_filename nu trebuie să conțină extensie."""
    result = extractor_invoice.extract("Factură ENEL...")
    assert "." not in result.suggested_filename, (
        f"suggested_filename conține extensie: {result.suggested_filename!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  EVAL 2 — ExtractorAgent: document necunoscut / OCR slab
# ─────────────────────────────────────────────────────────────────────────────

UNKNOWN_JSON = json.dumps(
    {
        "document_type": "unknown",
        "summary": "Document ilizibil.",
        "suggested_filename": "Unknown_Document",
        "entities": [
            {
                "field_name": "content",
                "value": "N/A",
                "confidence": 0.0,
                "reasoning": "Text necitibil.",
            }
        ],
    }
)


def test_extractor_unknown_document_low_confidence() -> None:
    """Document neclar → document_type 'unknown' și confidence 0.0."""
    agent = ExtractorAgent(llm=_make_llm(UNKNOWN_JSON))
    result = agent.extract("@@##$$ garbled OCR $$##@@")
    assert result.document_type == "unknown"
    assert all(e.confidence == 0.0 for e in result.entities)


# ─────────────────────────────────────────────────────────────────────────────
#  EVAL 3 — ExtractorAgent: rezistență la JSON malformat (repair loop)
# ─────────────────────────────────────────────────────────────────────────────

MALFORMED_JSON = "{ document_type: 'invoice', oops }"
REPAIRED_JSON = INVOICE_JSON


def test_extractor_repairs_malformed_json() -> None:
    """Agentul trebuie să repare JSON-ul malformat prin repair_chain și să returneze un rezultat valid."""
    # Primul apel returnează JSON stricat; al doilea (repair) returnează JSON corect
    llm = MagicMock()
    call_count = 0

    def side_effect(prompt_val):
        nonlocal call_count
        call_count += 1
        msg = MagicMock()
        msg.content = MALFORMED_JSON if call_count == 1 else REPAIRED_JSON
        return msg

    llm.invoke.side_effect = side_effect
    llm.__or__ = lambda self, other: _ChainMock(REPAIRED_JSON, other)

    agent = ExtractorAgent(llm=llm)
    # Înlocuim repair_chain-ul cu unul care returnează JSON-ul bun
    agent._repair_chain = MagicMock()
    agent._repair_chain.invoke = MagicMock(return_value=REPAIRED_JSON)

    result = agent.extract("Factură ENEL...")
    assert result.document_type == "invoice"


# ─────────────────────────────────────────────────────────────────────────────
#  EVAL 4 — DeciderAgent: rutare corectă (move vs. quarantine)
# ─────────────────────────────────────────────────────────────────────────────

DECISION_MOVE_JSON = json.dumps(
    {
        "status": "move",
        "suggested_name": "2023_ENEL_Factura.pdf",
        "suggested_folder": ".",
    }
)

DECISION_QUARANTINE_JSON = json.dumps(
    {
        "status": "quarantine",
        "suggested_name": "poza_caine.jpg",
        "suggested_folder": "Quarantine",
    }
)


@pytest.fixture()
def compiled_rule_factura() -> CompiledRule:
    return CompiledRule(
        category="factura",
        folder_structure="Facturi",
        naming_convention="[An]_[Emitent]_Factura.[ext]",
    )


def test_decider_routes_matching_document_to_move(
    compiled_rule_factura: CompiledRule,
) -> None:
    """Document care corespunde regulii → status 'move'."""
    agent = DeciderAgent(llm=_make_llm(DECISION_MOVE_JSON))
    # Mock-uim chain-ul intern direct
    agent._chain = MagicMock()
    agent._chain.invoke = MagicMock(return_value=DECISION_MOVE_JSON)

    decision = agent.decide(
        summary="Factură ENEL, 150 RON, mai 2023",
        original_filename="doc_scan.pdf",
        rule=compiled_rule_factura,
    )
    assert decision.status == "move"


def test_decider_routes_unrelated_document_to_quarantine(
    compiled_rule_factura: CompiledRule,
) -> None:
    """Document care NU corespunde regulii → status 'quarantine'."""
    agent = DeciderAgent(llm=_make_llm(DECISION_QUARANTINE_JSON))
    agent._chain = MagicMock()
    agent._chain.invoke = MagicMock(return_value=DECISION_QUARANTINE_JSON)

    decision = agent.decide(
        summary="Poză cu un câine în parc.",
        original_filename="poza_caine.jpg",
        rule=compiled_rule_factura,
    )
    assert decision.status == "quarantine"
    assert decision.suggested_folder == "Quarantine"


def test_decider_move_produces_valid_filename(
    compiled_rule_factura: CompiledRule,
) -> None:
    """Filename-ul sugerat la 'move' nu trebuie să conțină caractere invalide."""
    agent = DeciderAgent(llm=_make_llm(DECISION_MOVE_JSON))
    agent._chain = MagicMock()
    agent._chain.invoke = MagicMock(return_value=DECISION_MOVE_JSON)

    decision = agent.decide("Factură ENEL", "doc.pdf", compiled_rule_factura)
    invalid_chars = set('<>:"/\\|?*')
    assert not invalid_chars.intersection(set(decision.suggested_name or "")), (
        f"Filename conține caractere invalide: {decision.suggested_name!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  EVAL 5 — ActionDecision Pydantic: validare schema
# ─────────────────────────────────────────────────────────────────────────────


def test_action_decision_sanitizes_filename_slashes() -> None:
    d = ActionDecision(
        status="move", suggested_name="factura/enel:2023.pdf", suggested_folder="."
    )
    assert "/" not in d.suggested_name
    assert ":" not in d.suggested_name


def test_action_decision_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ActionDecision(
            status="delete", suggested_name="doc.pdf", suggested_folder="Trash"
        )


def test_action_decision_allows_none_name() -> None:
    d = ActionDecision(
        status="quarantine", suggested_name=None, suggested_folder="Quarantine"
    )
    assert d.suggested_name is None


# ─────────────────────────────────────────────────────────────────────────────
#  EVAL 6 — CompilerAgent: compilare reguli din prompt natural
# ─────────────────────────────────────────────────────────────────────────────

COMPILER_FACTURA_JSON = json.dumps(
    {
        "category": "factura",
        "folder_structure": "Facturi_Curente",
        "naming_convention": "factura_[data].pdf",
    }
)

COMPILER_ANY_JSON = json.dumps(
    {
        "category": "any",
        "folder_structure": "Documente",
        "naming_convention": "{original_filename}",
    }
)

COMPILER_RENAME_JSON = json.dumps(
    {
        "category": "any",
        "folder_structure": "Poze",
        "naming_convention": "descriptive_name_based_on_content",
    }
)


def test_compiler_extracts_category_from_invoice_prompt() -> None:
    agent = CompilerAgent(llm=_make_llm(COMPILER_FACTURA_JSON))
    agent._chain = MagicMock()
    agent._chain.invoke = MagicMock(
        return_value=CompiledRule(
            category="factura",
            folder_structure="Facturi_Curente",
            naming_convention="factura_[data].pdf",
        )
    )
    rule = agent.compile("Facturile merg în folderul Facturi_Curente")
    assert rule.category == "factura"
    assert "Facturi" in rule.folder_structure


def test_compiler_sets_category_any_for_generic_prompt() -> None:
    """Prompt generic (toate fișierele) → category trebuie să fie 'any'."""
    agent = CompilerAgent(llm=_make_llm(COMPILER_ANY_JSON))
    agent._chain = MagicMock()
    agent._chain.invoke = MagicMock(
        return_value=CompiledRule(
            category="any",
            folder_structure="Documente",
            naming_convention="{original_filename}",
        )
    )
    rule = agent.compile("Organizează toate fișierele în Documente")
    assert rule.category == "any"


def test_compiler_sets_descriptive_naming_when_asked() -> None:
    """Dacă utilizatorul cere redenumire → naming_convention = 'descriptive_name_based_on_content'."""
    agent = CompilerAgent(llm=_make_llm(COMPILER_RENAME_JSON))
    agent._chain = MagicMock()
    agent._chain.invoke = MagicMock(
        return_value=CompiledRule(
            category="any",
            folder_structure="Poze",
            naming_convention="descriptive_name_based_on_content",
        )
    )
    rule = agent.compile("Pozele merg în Poze și dă-le nume sugestive")
    assert rule.naming_convention == "descriptive_name_based_on_content"


def test_compiler_keeps_original_filename_when_no_rename() -> None:
    """Fără cerere de redenumire → naming_convention păstrează '{original_filename}'."""
    agent = CompilerAgent(llm=_make_llm(COMPILER_ANY_JSON))
    agent._chain = MagicMock()
    agent._chain.invoke = MagicMock(
        return_value=CompiledRule(
            category="any",
            folder_structure="Documente",
            naming_convention="{original_filename}",
        )
    )
    rule = agent.compile("Mută toate fișierele în Documente")
    assert rule.naming_convention == "{original_filename}"


# ─────────────────────────────────────────────────────────────────────────────
#  EVAL 7 — ExtractionResult: validare câmpuri Pydantic
# ─────────────────────────────────────────────────────────────────────────────


def test_extraction_result_summary_truncated_at_200_chars() -> None:
    """get_technical_summary() nu trebuie să depășească 200 de caractere."""
    long_summary = "x" * 300
    result = ExtractionResult(
        document_type="invoice",
        summary=long_summary,
        suggested_filename="Test_Doc",
        entities=[],
    )
    assert len(result.get_technical_summary()) <= 200


def test_extraction_result_empty_entities_is_valid() -> None:
    result = ExtractionResult(
        document_type="unknown",
        summary="",
        suggested_filename="Unknown",
        entities=[],
    )
    assert result.entities == []


def test_extracted_entity_confidence_clamped() -> None:
    """Confidence în afara [0, 1] trebuie să ridice ValidationError."""
    from ai.agent_extractor import ExtractedEntity

    with pytest.raises(ValidationError):
        ExtractedEntity(field_name="test", value="val", confidence=1.5)


# ─────────────────────────────────────────────────────────────────────────────
#  EVAL 8 — Pipeline end-to-end (Compiler → Extractor → Decider)
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_invoice_end_to_end() -> None:
    """
    Simulează un run complet pentru o factură:
      1. CompilerAgent compilează regula
      2. ExtractorAgent extrage date din document
      3. DeciderAgent decide că fișierul corespunde regulii → 'move'
    """
    # Step 1: Compiler
    compiler = CompilerAgent(llm=_make_llm(COMPILER_FACTURA_JSON))
    rule = CompiledRule(
        category="factura",
        folder_structure="Facturi_Curente",
        naming_convention="factura_[data].pdf",
    )
    compiler._chain = MagicMock()
    compiler._chain.invoke = MagicMock(return_value=rule)
    compiled = compiler.compile("Facturile merg în Facturi_Curente")

    # Step 2: Extractor
    extractor = ExtractorAgent(llm=_make_llm(INVOICE_JSON))
    extraction = extractor.extract("Factură ENEL SA, 150 RON, 12.05.2023")

    # Step 3: Decider
    decider = DeciderAgent(llm=_make_llm(DECISION_MOVE_JSON))
    decider._chain = MagicMock()
    decider._chain.invoke = MagicMock(return_value=DECISION_MOVE_JSON)
    decision = decider.decide(
        summary=extraction.get_technical_summary(),
        original_filename="factura_scan.pdf",
        rule=compiled,
    )

    assert compiled.category == "factura"
    assert extraction.document_type == "invoice"
    assert decision.status == "move"
    assert decision.suggested_name is not None
