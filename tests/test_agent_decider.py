"""
Tests for Agent 2 - Decider
"""

import pytest
from pydantic import ValidationError

from ai.agent_decider import ActionDecision


def test_sanitize_filename():
    """Testează dacă validatorul Pydantic curăță caracterele ilegale."""
    decision = ActionDecision(
        status="move",
        suggested_name="factura/enel:2023.pdf",
        suggested_folder="Facturi",
    )
    # slash-ul și colon-ul trebuie înlocuite cu underscore
    assert decision.suggested_name == "factura_enel_2023.pdf"


def test_invalid_status_raises_error():
    """Testează dacă Pydantic blochează statusuri inventate."""
    with pytest.raises(ValidationError):
        ActionDecision(
            status="delete",  # Invalid status, doar move sau quarantine permise
            suggested_name="doc.pdf",
            suggested_folder="Trash",
        )
