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

    field_name: str = Field(..., description="Canonical field name (e.g. 'full_name', 'date_of_birth').")
    value: str = Field(..., description="Extracted value exactly as it appears.")
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
        ..., description="Identified document type (e.g. 'invoice', 'identity_card', 'medical_record')."
    )
    summary: str = Field(
        default="", 
        max_length=200,
        description="Rezumat tehnic (Emitent, Dată, Sumă, Tip) de maxim 200 caractere."
    )
    entities: list[ExtractedEntity] = Field(
        default_factory=list, description="All extracted entities."
    )
    raw_thinking: str = Field(
        default="",
        description="The agent's chain-of-thought reasoning (kept for audit).",
    )

    def get_technical_summary(self) -> str:
        """Returnează STRICT rezumatul tehnic de maxim 200 de caractere (Task 9)."""
        return self.summary[:200]


# =====================================================================
#  System prompt — instructs the LLM to *think*, not just parse
# =====================================================================

_SYSTEM_PROMPT = """\
You are an expert data-extraction agent for the ClutterKill system.
Your job is to extract structured information from raw document text
that may come from OCR (noisy, misspelled, broken formatting).

IMPORTANT: You are a THINKING agent.  Before extracting, you MUST
reason step-by-step about the document.

Follow this exact protocol:

### Step 1 — IDENTIFY
Determine the document type (invoice, ID card, contract, medical
record, correspondence, etc.).  State your reasoning.

### Step 2 — PLAN
List the fields you expect to find for this document type.
Mention any fields that are likely missing or corrupted.

### Step 3 — EXTRACT
For each field, extract the value.  If the text is ambiguous,
state the ambiguity and pick the most likely interpretation.
Assign a confidence score (0.0–1.0) to each extraction.

### Step 4 — OUTPUT
Return your answer as a single JSON object with this schema:
{{
  "thinking": "<your full chain-of-thought from steps 1-3>",
  "document_type": "<identified type>",
  "summary": "<STRICT: 'Emitent: [X], Dată: [Y], Sumă: [Z], Tip: [W]'. Limitat la max 200 caractere. Dacă o informație lipsește, scrie N/A.>",
  "entities": [
    {{
      "field_name": "<canonical_field_name>",
      "value": "<extracted value>",
      "confidence": <0.0-1.0>,
      "reasoning": "<why you chose this value>"
    }}
  ]
}}

Rules:
- Output ONLY the JSON object, no markdown fences, no extra text.
- Use snake_case for field_name values.
- If a field is completely unreadable, set confidence to 0.0 and
  value to "UNREADABLE".
- Preserve original values exactly — do NOT normalize dates or names
  unless they are clearly OCR errors.
"""

_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", "Extract structured data from the following document text:\n\n---\n{document_text}\n---"),
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
        logger.info("ExtractorAgent: starting extraction (%d chars)", len(document_text))

        raw_output = self._chain.invoke({"document_text": document_text})
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
        entities = [
            ExtractedEntity(**ent) for ent in data.get("entities", [])
        ]
        return ExtractionResult(
            document_type=data.get("document_type", "unknown"),
            summary=data.get("summary", ""),
            entities=entities,
            raw_thinking=data.get("thinking", ""),
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

    print(f"\n{'='*60}")
    print(f"Document type : {result.document_type}")
    print(f"Summary       : {result.summary}")
    print(f"Thinking      : {result.raw_thinking[:200]}…")
    print(f"{'='*60}")
    for ent in result.entities:
        print(f"  {ent.field_name:20s} = {ent.value:30s}  (conf: {ent.confidence:.1f})")
