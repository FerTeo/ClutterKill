import logging
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage

from agents.decider_agent import generate_proposal
from agents.validator_agent import validate_proposal
from llm.vector_store import vector_store
from agents.context_manager import truncate_to_token_limit
from agents.registry import register
import json

logger = logging.getLogger(__name__)

# Definim starea pentru Graful LangGraph
class CriticState(TypedDict):
    document_text: str
    few_shot_examples: list[dict]
    llm: any
    current_proposal: dict
    errors: list[str]
    iterations: int

async def decider_node(state: CriticState):
    """Nodul care generează propunerea (Decider)"""
    logger.info(f"Iterația {state['iterations']}: Decider generează propunerea...")
    
    # Dacă avem erori din iterația anterioară, adăugăm un mesaj de corectare la finalul textului
    text_to_process = state["document_text"]
    if state["errors"]:
        correction_prompt = "\n\n[CRITIC FEEDBACK FROM PREVIOUS ATTEMPT]:\n"
        correction_prompt += "Your previous JSON was invalid for the following reasons:\n- "
        correction_prompt += "\n- ".join(state["errors"])
        correction_prompt += "\n\nPlease FIX these errors and return a valid JSON."
        text_to_process += correction_prompt

    proposal = await generate_proposal(state["llm"], text_to_process, state["few_shot_examples"])
    
    return {
        "current_proposal": proposal,
        "iterations": state["iterations"] + 1
    }

def validator_node(state: CriticState):
    """Nodul care validează propunerea (Validator)"""
    logger.info("Validator verifică propunerea...")
    errors = validate_proposal(state["current_proposal"])
    
    if errors:
        logger.warning(f"S-au găsit erori: {errors}")
        
    return {
        "errors": errors
    }

def should_continue(state: CriticState):
    """Decide dacă mergem înapoi la Decider sau am terminat."""
    if not state["errors"]:
        return "end" # Valid!
    if state["iterations"] >= 3:
        logger.error("S-a atins limita maximă de iterații! Se oprește bucla.")
        return "end" # Oprire forțată după 3 încercări
    return "continue" # Mai încercăm

# Construim Graful
graph_builder = StateGraph(CriticState)
graph_builder.add_node("decider", decider_node)
graph_builder.add_node("validator", validator_node)

graph_builder.set_entry_point("decider")
graph_builder.add_edge("decider", "validator")
graph_builder.add_conditional_edges(
    "validator",
    should_continue,
    {
        "continue": "decider",
        "end": END
    }
)

critic_graph = graph_builder.compile()

async def run_critic_system(llm, raw_document_text: str) -> dict:
    """
    Entry point-ul principal pentru a procesa un fișier complet (RAG + Context Mng + Critic Loop).
    """
    # 1. Trunchiere pentru fereastra de context
    truncated_text = truncate_to_token_limit(raw_document_text)
    
    # 2. RAG: Preluăm exemple similare
    similar_examples = vector_store.get_similar_examples(truncated_text, k=3)
    
    # 3. Rulăm graful LangGraph
    initial_state = {
        "document_text": truncated_text,
        "few_shot_examples": similar_examples,
        "llm": llm,
        "current_proposal": {},
        "errors": [],
        "iterations": 0
    }
    
    final_state = await critic_graph.ainvoke(initial_state)
    final_proposal = final_state["current_proposal"]
    
    # Dacă a reușit (fără erori finale), o salvăm în Vector DB pentru învățare continuă
    if not final_state["errors"] and "error" not in final_proposal:
        # Aici e opțional, ar putea fi salvată abia după confirmarea utilizatorului în UI,
        # dar o salvăm automat pentru Spike
        vector_store.save_decision(truncated_text, final_proposal)
        
    return final_proposal

@register("Decider", "Renames files by analyzing their document text using a Critic AI loop and vector DB.")
async def handle_decide_request(llm, user_input: str) -> str:
    """Wrapper for the orchestrator to call the critic system."""
    # În acest spike simplu, presupunem că user_input ESTE textul documentului
    # Într-un sistem complet, un agent de Extracție ar prelua textul din PDF mai întâi
    proposal_dict = await run_critic_system(llm, user_input)
    return f"AI Decision:\n```json\n{json.dumps(proposal_dict, indent=2)}\n```"
