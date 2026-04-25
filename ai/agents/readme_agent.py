"""
README Agent

A LangChain ReAct agent that reads the project README and answers
questions about it. It has two tools:

  read_readme   — returns the full README content
  search_readme — finds lines in the README matching a query
"""
import pathlib

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agents.registry import register

README_PATH = str(pathlib.Path(__file__).parent.parent / "README.md")


@tool
def read_readme() -> str:
    """Read the full contents of the project README.md file."""
    with open(README_PATH, encoding="utf-8") as f:
        return f.read()


@tool
def search_readme(query: str) -> str:
    """Search the README for lines containing a specific term or keyword."""
    with open(README_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    matches = [line.strip() for line in lines if query.lower() in line.lower()]
    if not matches:
        return f"No lines containing '{query}' found in the README."
    return "\n".join(matches)


README_TOOLS = [read_readme, search_readme]


@register(
    name="readme",
    description="Questions about the project: what it does, architecture, setup, or documentation.",
)
async def run_readme_agent(llm, user_input: str) -> str:
    """Run the README agent on a user question and return the answer."""
    agent = create_react_agent(llm, README_TOOLS)
    result = await agent.ainvoke({"messages": [("human", user_input)]})
    return result["messages"][-1].content
