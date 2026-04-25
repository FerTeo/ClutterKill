# Architecture

## Overview

```
User (terminal)
      │
      ▼
  main.py  ──────────────────────────────────────────────────────────
      │                                                              │
      │  get_llm()                                              chat loop
      ▼
  llm/config.py
  ┌─────────────────────────────────────────────────┐
  │  LLM_MODE=openai  →  ChatOpenAI (OpenAI API)    │
  │  LLM_MODE=local   →  ChatOllama (local server)  │
  └─────────────────────────────────────────────────┘
      │
      ▼
  agents/orchestrator.py
  ┌───────────────────────────────────────────────────┐
  │  LLM classifies intent → "database" or "readme"  │
  └───────────────────────────────────────────────────┘
        │                         │
        ▼                         ▼
agents/database_agent.py    agents/readme_agent.py
  ReAct agent                 ReAct agent
  (LangGraph)                 (LangGraph)
        │                         │
        │ MCP tools            file tools
        ▼                         ▼
mcp_server/mock_db_server.py   README.md
  FastMCP over stdio
        │
        ▼
  SQLite (temp file)
```

## Components

### `main.py`
Entry point. Loads `.env`, instantiates the LLM, starts the `DatabaseAgent` and runs the interactive chat loop. Calls the orchestrator on each user message.

### `llm/config.py`
Factory function `get_llm()`. Reads `LLM_MODE` from `.env` and returns either:
- `ChatOpenAI` — calls the OpenAI API using `OPENAI_API_KEY`
- `ChatOllama` — calls a local Ollama server at `OLLAMA_BASE_URL` using the model registered as `OLLAMA_MODEL`

### `agents/orchestrator.py`
Sends the user message to the LLM with a routing prompt. The LLM replies with `"database"` or `"readme"`. The orchestrator then delegates to the appropriate agent.

### `agents/database_agent.py`
A LangGraph `create_react_agent` that has access to 5 MCP tools (see below). It is an async context manager that keeps the MCP server subprocess alive for the duration of the session.

### `agents/readme_agent.py`
A LangGraph `create_react_agent` with two plain Python tools:
- `read_readme` — returns the full `README.md`
- `search_readme` — returns lines matching a keyword

### `mcp_server/mock_db_server.py`
A **FastMCP** server that runs as a subprocess and communicates over **stdio** transport. Exposes 5 tools:

| Tool | Operation |
|---|---|
| `create_record(key, value)` | INSERT |
| `read_record(key)` | SELECT |
| `update_record(key, new_value)` | UPDATE |
| `delete_record(key)` | DELETE |
| `list_all_records()` | SELECT * |

Data is stored in a SQLite file in the OS temp directory, so it persists across agent calls within the same session.

## LLM Modes

| | OpenAI | Local (Ollama) |
|---|---|---|
| Config | `LLM_MODE=openai` | `LLM_MODE=local` |
| Model | `gpt-4o-mini` (default) | `gemma4` (default) |
| Setup | API key in `.env` | `ollama serve` running |
| Cost | per token | free, runs on device |

## Data Flow (example: "Create a record key=x value=y")

```
User input
  → Orchestrator (LLM call) → "database"
  → DatabaseAgent.run(input)
  → ReAct loop:
      Thought: I need to call create_record
      Action:  create_record(key="x", value="y")
      → MCP client sends request over stdio
      → mock_db_server.py executes INSERT into SQLite
      → returns "Created: x = y"
      Observation: "Created: x = y"
      Thought: Done.
  → Final answer returned to user
```

## File Structure

```
agents/
├── main.py                      # entry point + chat loop
├── pyproject.toml               # Python dependencies
├── .env                         # secrets and config (not committed)
├── .env.example                 # template
├── Modelfile                    # Ollama model import definition
│
├── llm/
│   └── config.py                # get_llm(): OpenAI or Ollama
│
├── mcp_server/
│   └── mock_db_server.py        # FastMCP server, 5 CRUD tools, SQLite
│
└── agents/
    ├── orchestrator.py          # intent classifier + router
    ├── database_agent.py        # ReAct agent with MCP tools
    └── readme_agent.py          # ReAct agent with file tools
```
