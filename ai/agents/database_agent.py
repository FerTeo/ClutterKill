"""
Database Agent

A LangChain ReAct agent that uses MCP tools to perform CRUD operations
on a mock SQLite database. The MCP server runs as a persistent subprocess
for the lifetime of this agent, so database state is preserved across calls.

Usage:
    async with DatabaseAgent(llm) as agent:
        response = await agent.run("List all records")
        response = await agent.run("Create a record key=foo value=bar")
"""
import pathlib

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from agents.registry import register

MCP_SERVER_PATH = str(
    pathlib.Path(__file__).parent.parent / "mcp_server" / "mock_db_server.py"
)


class DatabaseAgent:
    """
    Async context manager that keeps an MCP server subprocess alive
    and wraps it in a LangChain ReAct agent.

    The server exposes five tools: create_record, read_record,
    update_record, delete_record, list_all_records.
    """

    def __init__(self, llm):
        self.llm = llm
        self._client: MultiServerMCPClient | None = None
        self._agent = None

    async def __aenter__(self):
        self._client = MultiServerMCPClient(
            {
                "mock_db": {
                    "command": "python",
                    "args": [MCP_SERVER_PATH],
                    "transport": "stdio",
                }
            }
        )
        tools = await self._client.get_tools()
        self._agent = create_react_agent(self.llm, tools)
        return self

    async def __aexit__(self, *args):
        pass  # MultiServerMCPClient manages its own lifecycle in v0.1.0+

    async def run(self, user_input: str) -> str:
        """Invoke the agent with a user message and return its final answer."""
        result = await self._agent.ainvoke(
            {"messages": [("human", user_input)]}
        )
        return result["messages"][-1].content


# The registry needs a plain async function. We store the active instance
# in a module-level variable set by main.py after the context manager starts.
_instance: "DatabaseAgent | None" = None


@register(
    name="database",
    description="CRUD operations on the database: create, read, update, delete, or list records.",
)
async def _run_database_agent(llm, user_input: str) -> str:
    if _instance is None:
        raise RuntimeError("DatabaseAgent not initialised. Start it as a context manager first.")
    return await _instance.run(user_input)
