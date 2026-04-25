"""
Orchestrator

Dynamically discovers all registered agents and builds the routing
prompt from their names and descriptions. Adding a new agent to the
registry is the only change needed — this file never needs editing.
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def _build_prompt(agents) -> str:
    agent_lines = "\n".join(
        f'- "{a.name}": {a.description}' for a in agents
    )
    names = ", ".join(f'"{a.name}"' for a in agents)
    return (
        "You are a routing assistant. Based on the user's message, decide which agent should handle it.\n\n"
        f"Available agents:\n{agent_lines}\n\n"
        f"Reply with ONLY one word — one of: {names}.\n\n"
        "User message: {message}"
    )


async def run_orchestrator(llm, user_input: str) -> str:
    """
    Discover all registered agents, classify the user's intent,
    and delegate to the matching agent.
    """
    # Import triggers @register decorators in each agent module
    import agents.database_agent
    import agents.readme_agent
    from agents.registry import AGENTS

    prompt = _build_prompt(AGENTS)
    chain = ChatPromptTemplate.from_template(prompt) | llm | StrOutputParser()
    decision = (await chain.ainvoke({"message": user_input})).strip().lower()

    matched = next((a for a in AGENTS if a.name in decision), AGENTS[0])
    print(f"[Orchestrator] → {matched.name} agent")
    return await matched.run(llm, user_input)
