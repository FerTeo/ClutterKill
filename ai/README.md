# Multi-Agent AI System

A hands-on demonstration of a multi-agent AI system built with **LangChain** and **LangGraph**, designed for educational purposes. Students can interact with an orchestrator that routes requests to specialized agents.

## Architecture

```
User
 │
 ▼
Orchestrator  ──── routes based on intent ────►  Database Agent  ──► MCP Server ──► SQLite DB
                                             └──► README Agent   ──► README.md
```

### Components

| Component | File | Role |
|---|---|---|
| **Orchestrator** | `agents/orchestrator.py` | Routes user input to the right agent |
| **Database Agent** | `agents/database_agent.py` | Performs CRUD on a mock database via MCP |
| **README Agent** | `agents/readme_agent.py` | Reads and answers questions about this file |
| **MCP Server** | `mcp_server/mock_db_server.py` | Exposes database tools via Model Context Protocol |
| **LLM Factory** | `llm/config.py` | Returns OpenAI or local llama.cpp model |

### How agents work

Each agent is a **ReAct agent** (Reasoning + Acting): it receives a user message, decides which tool to call, calls it, observes the result, and repeats until it has enough information to answer. This is implemented with `create_react_agent` from LangGraph.

### What is MCP?

**MCP (Model Context Protocol)** is an open standard for connecting AI models to external tools and data sources. The database agent connects to an MCP server that runs as a subprocess, exposing CRUD tools over a stdio transport. This cleanly separates the agent logic from the database implementation.

## Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended package manager)

### Installation

```bash
# Clone and enter the project
cd agents

# Install dependencies
uv sync

# Copy the environment config
cp .env.example .env
```

### Configuration

Edit `.env` and choose your LLM mode:

#### Option A — OpenAI API (easiest)

```env
LLM_MODE=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

#### Option B — Local LLM with llama.cpp

1. Install the local dependencies (pick your hardware):

```bash
# macOS (Apple Silicon / Metal GPU)
CMAKE_ARGS="-DGGML_METAL=on" uv pip install ".[local]"

# NVIDIA GPU (CUDA)
CMAKE_ARGS="-DGGML_CUDA=on" uv pip install ".[local]"

# CPU only
uv pip install ".[local]"
```

2. Download a GGUF model — recommended: **Gemma 4 24B MoE** (Q4_K_M quantization)

```bash
mkdir models
# Download from HuggingFace and place the .gguf file in models/
```

3. Update `.env`:

```env
LLM_MODE=local
MODEL_PATH=models/gemma-4-24b-moe-instruct-Q4_K_M.gguf
N_GPU_LAYERS=-1
N_CTX=8192
```

## Running

```bash
uv run python main.py
```

## Example Interactions

### Database operations (Database Agent)
```
You: Create a record with key "student1" and value "Alice"
You: Read the record with key "student1"
You: Update "student1" to "Alice Smith"
You: List all records in the database
You: Delete the record "student1"
```

### Documentation questions (README Agent)
```
You: What does this project do?
You: How do I set up the project?
You: What agents are available?
You: How does the MCP server work?
You: What is the difference between the two LLM modes?
```

## Project Structure

```
agents/
├── main.py                    # Entry point: starts the chat loop
├── pyproject.toml             # Project dependencies
├── .env.example               # Environment variable template
│
├── llm/
│   └── config.py              # LLM factory: OpenAI or local llama.cpp
│
├── mcp_server/
│   └── mock_db_server.py      # FastMCP server with 5 CRUD tools
│
└── agents/
    ├── database_agent.py      # Agent that uses MCP tools
    ├── readme_agent.py        # Agent that reads this README
    └── orchestrator.py        # Router: classifies intent and delegates
```

## Key Technologies

- **[LangChain](https://python.langchain.com/)** — agent framework and tool abstractions
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — `create_react_agent` for ReAct-style agents
- **[MCP](https://modelcontextprotocol.io/)** — open protocol for tool-use (Model Context Protocol)
- **[FastMCP](https://github.com/anthropics/mcp)** — Python server for MCP
- **[llama.cpp](https://github.com/ggerganov/llama.cpp)** — local LLM inference engine
- **[SQLite](https://www.sqlite.org/)** — embedded database for the mock DB
