import json
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

DECIDER_PROMPT = """
You are an expert file organizer AI. Your task is to extract information from the following document and decide on a standardized new file name and category.

Examples of past decisions (for similar documents):
{few_shot_examples}

Document Text:
{document_text}

Rules:
1. You must output ONLY a valid JSON object.
2. The JSON must have exactly the following keys:
   - "new_name": The proposed file name (e.g. "factura_ACME_2024.pdf"). Always include a valid extension based on the document type.
   - "category": One of [factura, contract, curs, reteta, imagine, unknown].
   - "confidence": A float between 0.0 and 1.0 representing how sure you are.
   - "reasoning": A short step-by-step thinking process (Chain of Thought) explaining why you chose this name.

Your JSON Output:
"""

async def generate_proposal(llm, document_text: str, few_shot_examples: list[dict]) -> dict:
    """
    Folosește LLM-ul pentru a genera o propunere inițială de redenumire.
    """
    
    # Formatăm exemplele pentru prompt
    examples_str = "No previous examples."
    if few_shot_examples:
        examples_str = ""
        for i, ex in enumerate(few_shot_examples):
            examples_str += f"Example {i+1}:\nText: {ex['text'][:200]}...\nDecision: {json.dumps(ex['decision'])}\n\n"
            
    prompt = ChatPromptTemplate.from_template(DECIDER_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    raw_response = await chain.ainvoke({
        "document_text": document_text,
        "few_shot_examples": examples_str
    })
    
    # Cleanup basic în caz că LLM-ul returnează markdown ```json ... ```
    cleaned_response = raw_response.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]
    if cleaned_response.startswith("```"):
        cleaned_response = cleaned_response[3:]
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]
        
    try:
        decision = json.loads(cleaned_response.strip())
        return decision
    except json.JSONDecodeError as e:
        logger.error(f"Eroare de parsare JSON la ieșirea Decider-ului: {e}\nRaw output: {raw_response}")
        # Returnăm raw response pentru ca Validator-ul să îl poată critica
        return {"error": "Invalid JSON format", "raw_output": raw_response}
