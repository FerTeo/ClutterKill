"""
Multi-Agent AI System — Entry Point

Starts an interactive chat loop. An orchestrator routes each message to:
  - Database Agent: CRUD operations on a mock SQLite database (via MCP)
  - README Agent:   Questions about this project's documentation
"""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def main():
    from agents.database_agent import DatabaseAgent
    from agents.orchestrator import run_orchestrator
    from llm.config import get_llm

    mode = os.getenv("LLM_MODE", "openai").upper()

    print("=" * 52)
    print("  Multi-Agent AI System")
    print(f"  LLM mode: {mode}")
    print("=" * 52)
    print("Examples:")
    print("  'Create a record key=name value=Alice'")
    print("  'List all records in the database'")
    print("  'What does this project do?'")
    print("  'How does the MCP server work?'")
    print("  Type 'quit' to exit.")
    print("=" * 52)
    print()

    llm = get_llm()

    import agents.database_agent as db_module

    async with DatabaseAgent(llm) as db_agent:
        db_module._instance = db_agent  # expose to registry entry

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            try:
                response = await run_orchestrator(llm, user_input)
                print(f"\nAssistant: {response}\n")
            except Exception as exc:
                print(f"\nError: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
