"""
Extractor Agent — ai/agent_extractor.py

A *thinking* extraction agent (not a dumb parser) that reasons about
document content, identifies structured data fields, and returns a
validated Pydantic model.

Architecture
────────────
  raw text  ──►  ExtractorAgent.extract()
                       │
                       ├─ 1. THINK  – reason about what the document is
                       ├─ 2. PLAN   – decide which fields to extract
                       ├─ 3. EXTRACT – pull structured data w/ chain-of-thought
                       └─ 4. VALIDATE – parse into Pydantic, retry on failure
                       │
                  ExtractionResult (validated)

The agent uses a multi-step chain-of-thought prompt so the LLM
*reasons* before answering — critical for messy OCR / scanned PDFs.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ValidationError

from ai.llm_config import get_llm, MODEL_EXTRACTOR

logger = logging.getLogger(__name__)

# ─── Maximum retry attempts for structured output parsing ────────────
_MAX_RETRIES = 2


# =====================================================================
#  Pydantic schema — the contract for every extraction result
# =====================================================================


class ExtractedEntity(BaseModel):
    """A single named entity or data point extracted from a document."""

    field_name: str = Field(
        ..., description="Canonical field name (e.g. 'full_name', 'date_of_birth')."
    )
    value: Any = Field(..., description="Extracted value exactly as it appears.")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Agent's self-assessed confidence in the extraction (0-1).",
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for why this value was chosen.",
    )


class ExtractionResult(BaseModel):
    """Complete extraction output for one document."""

    document_type: str = Field(
        ...,
        description="Identified document type (e.g. 'invoice', 'identity_card', 'medical_record').",
    )
    summary: str = Field(
        default="",
        max_length=500,
        description="Dense 1-2 sentence summary containing key details.",
    )
    suggested_filename: str = Field(
        default="",
        description="A concise 2-3 word filename without any file extension.",
    )
    entities: list[ExtractedEntity] = Field(
        default_factory=list, description="All extracted entities."
    )

    def get_technical_summary(self) -> str:
        """Returnează STRICT rezumatul tehnic de maxim 200 de caractere (Task 9)."""
        return self.summary[:200]


# =====================================================================
#  System prompt — instructs the LLM to *think*, not just parse
# =====================================================================

_SYSTEM_PROMPT = """\
You are a fast, precise data-extraction agent. 
Extract structured information from raw document text into JSON. 
Do NOT output any reasoning, explanations, or conversational filler. 

Return your answer as a single JSON object with this exact schema:
{{
  "document_type": "<identified type, e.g. invoice, contract, lab_work, unknown>",
  "summary": "<Dense 1-2 sentence summary containing all key specific details (e.g. subject name, lab number, issuer, total amount, patient name). Limit to 200 chars.>",
  "suggested_filename": "<A concise, 2-3 word descriptive filename. DO NOT include any file extension like .pdf or .docx. Example: Vodafone_Invoice, AI_Lab_1, Medical_Report. Use PascalCase.>",
  "entities": [
    {{
      "field_name": "<canonical_field_name>",
      "value": "<extracted value>",
      "confidence": <0.0-1.0>,
      "reasoning": "<1 sentence why you chose this>"
    }}
  ]
}}

Rules:
- Output ONLY valid JSON.
- No markdown fences.
- If unreadable, set value to "N/A" and confidence 0.0.
"""

_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            "Extract structured data from the following document text:\n\n---\n{document_text}\n---",
        ),
    ]
)


# =====================================================================
#  Repair prompt — used when JSON is malformed on the first try
# =====================================================================

_REPAIR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You previously attempted to extract data but your JSON was invalid. "
            "Fix the JSON below so it matches the required schema. "
            "Output ONLY valid JSON, nothing else.",
        ),
        ("human", "Broken output:\n{broken_json}\n\nValidation error:\n{error}"),
    ]
)


# =====================================================================
#  ExtractorAgent
# =====================================================================


class ExtractorAgent:
    """Thinking extraction agent backed by a local Ollama LLM.

    Usage::

        agent = ExtractorAgent()
        result = agent.extract("John Doe, born 1990-05-12 …")
        print(result.entities)
    """

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm or get_llm(model=MODEL_EXTRACTOR)
        self._chain = _EXTRACTION_PROMPT | self._llm | StrOutputParser()
        self._repair_chain = _REPAIR_PROMPT | self._llm | StrOutputParser()

    # ── public API ───────────────────────────────────────────────────

    def extract(self, document_text: str) -> ExtractionResult:
        """Run the full think→plan→extract→validate pipeline.

        Parameters
        ----------
        document_text : str
            Raw text content of the document (e.g. from OCR or PDF parser).

        Returns
        -------
        ExtractionResult
            Validated extraction with entities, confidence scores, and
            the agent's chain-of-thought reasoning.

        Raises
        ------
        ExtractionError
            If the LLM fails to produce valid JSON after all retries.
        """
        logger.info(
            "ExtractorAgent: starting extraction (%d chars)", len(document_text)
        )

        # Create prompt
        prompt_val = _EXTRACTION_PROMPT.format_messages(document_text=document_text)

        # Retry logic for 429 Resource Exhausted (Free Tier RPM Limits)
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = self._llm.invoke(prompt_val)
                raw_output = response.content
                if isinstance(raw_output, list):
                    raw_output = " ".join(
                        [
                            str(part.get("text", part))
                            if isinstance(part, dict)
                            else str(part)
                            for part in raw_output
                        ]
                    )
                elif not isinstance(raw_output, str):
                    raw_output = str(raw_output)
                break
            except Exception as e:
                if "429" in str(e) and attempt < max_attempts - 1:
                    logger.warning(
                        f"API Rate Limit Hit (429) in Extractor. Sleeping 15s... (Attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(15)
                else:
                    raise e

        logger.debug("Raw LLM output:\n%s", raw_output)

        # Try to parse → validate → retry loop
        result = self._parse_with_retries(raw_output)
        logger.info(
            "Extraction complete: type=%s  entities=%d",
            result.document_type,
            len(result.entities),
        )
        return result

    # ── internals ────────────────────────────────────────────────────

    def _parse_with_retries(self, raw_output: str) -> ExtractionResult:
        """Attempt to parse the LLM output into an ExtractionResult.

        If JSON is malformed, ask the LLM to repair it up to
        ``_MAX_RETRIES`` times.
        """
        last_error: Exception | None = None
        current_output = raw_output

        for attempt in range(_MAX_RETRIES + 1):
            try:
                data = self._extract_json(current_output)
                return self._validate(data)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
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

        raise ExtractionError(
            f"Failed to parse extraction after {_MAX_RETRIES + 1} attempts: {last_error}"
        ) from last_error

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Pull the first JSON object out of the LLM response."""
        # Strip markdown code fences if the model wraps them anyway
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())

    @staticmethod
    def _validate(data: dict) -> ExtractionResult:
        """Map raw JSON dict → ExtractionResult pydantic model."""
        entities = [ExtractedEntity(**ent) for ent in data.get("entities", [])]
        return ExtractionResult(
            document_type=data.get("document_type", "unknown"),
            summary=data.get("summary", ""),
            suggested_filename=data.get("suggested_filename", ""),
            entities=entities,
        )


# =====================================================================
#  Custom exception
# =====================================================================


class ExtractionError(RuntimeError):
    """Raised when the agent cannot produce a valid extraction."""


# ─── Quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample_text = (
        "BULETIN DE IDENTITATE\n"
        "Nume: POPESCU  Prenume: ION ALEXANDRU\n"
        "CNP: 1900512345678\n"
        "Data nașterii: 12.05.1990\n"
        "Domiciliu: Str. Victoriei nr. 42, București, Sector 3\n"
        "Seria: RX  Nr: 123456\n"
    )

    agent = ExtractorAgent()
    result = agent.extract(sample_text)

    print(f"\n{'=' * 60}")
    print(f"Document type : {result.document_type}")
    print(f"Summary       : {result.summary}")
    print(f"{'=' * 60}")
    for ent in result.entities:
        print(f"  {ent.field_name:20s} = {ent.value:30s}  (conf: {ent.confidence:.1f})")
