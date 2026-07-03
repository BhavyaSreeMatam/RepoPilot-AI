# RepoPilot AI

RepoPilot AI is an AI engineering copilot for understanding, debugging, and onboarding into unfamiliar codebases.

The system allows users to upload a repository as a ZIP file, index the codebase, and ask natural-language engineering questions. It uses retrieval-augmented generation and a multi-agent workflow to route questions to specialized agents for architecture explanation, onboarding summaries, bug diagnosis, and grounded answer verification.

## Features

- Upload a repository ZIP file from the frontend
- Automatically scan and process code files
- Chunk and index repository content for retrieval
- Ask architecture and codebase questions
- Generate developer onboarding summaries
- Debug repository-specific issues
- Retrieve source file references and line ranges
- Show agent execution steps
- Verify answers against retrieved code context

## Tech Stack

### Backend
- FastAPI
- Python
- OpenAI API
- Local vector store (ChromaDB)
- LangGraph multi-agent workflow for routing, retrieval, answering, debugging, summarization, and verification
- MCP (Model Context Protocol) — the orchestrator communicates with the specialized agents as MCP tools over stdio

### Frontend
- React
- Vite
- JavaScript
- React Markdown
- Custom CSS dashboard UI

## Project Structure

```txt
RepoPilot-AI/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── api.js
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Architecture

The orchestrator (router) communicates with the five specialized agents through **MCP (Model Context Protocol)**. The router, retriever, and verifier run as in-process LangGraph nodes; the specialized agents run in a separate MCP server subprocess and are invoked as MCP tools over stdio. The subprocess is spawned once at FastAPI startup (via the `lifespan` handler) and reused across requests.

```mermaid
flowchart TB
    subgraph Client["Frontend (React / Vite)"]
        UI["Dashboard UI<br/>api.js"]
    end

    subgraph Backend["FastAPI Backend Process"]
        direction TB
        EP["/agent/ask · /agent/summarize · /agent/debug<br/>(async → ainvoke)"]

        subgraph Graph["LangGraph StateGraph (in-process)"]
            direction TB
            R["router_agent<br/>picks route via LLM"]
            RET["retriever_agent<br/>ChromaDB vector search"]
            SPEC["specialized_agent_node<br/>ROUTE_TO_TOOL lookup<br/>+ MCP call_tool"]
            VER["verifier_agent<br/>grounding check"]
            R --> RET --> SPEC --> VER
        end

        MC["mcp_client.py<br/>persistent ClientSession<br/>(AsyncExitStack, stdio)"]

        EP --> R
        VER --> EP
        SPEC -->|"await session.call_tool()"| MC
    end

    subgraph MCPServer["MCP Server Subprocess (stdio)"]
        direction TB
        FM["FastMCP<br/>'repopilot-specialized-agents'"]
        subgraph Tools["@mcp.tool()"]
            T1["architecture_agent"]
            T2["bug_agent"]
            T3["security_agent"]
            T4["docs_agent"]
            T5["general_agent"]
        end
        FM --> Tools
        LLM["run_llm_agent()<br/>llm_utils.py"]
        Tools --> LLM
    end

    OpenAI["OpenAI API<br/>gpt-4.1-mini"]

    UI -->|HTTP| EP
    MC <==>|"MCP over stdio<br/>(spawned at lifespan startup,<br/>env=os.environ.copy())"| FM
    R -.->|LLM call| OpenAI
    VER -.->|LLM call| OpenAI
    LLM -->|LLM call| OpenAI
    RET -.->|embeddings| OpenAI
```

## Setup Instructions

### Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\scripts\activate.ps1
pip install -r requirements.txt
```

Create a `.env` file inside the `backend/` folder:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Run the backend:

```powershell
uvicorn app.main:app
```

The backend will run at:

```txt
http://127.0.0.1:8000
```

API documentation is available at:

```txt
http://127.0.0.1:8000/docs
```

### Frontend Setup

Open a new terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend will run at:

```txt
http://localhost:5173
```

## Usage Flow

1. Start the backend server.
2. Start the frontend development server.
3. Upload a repository ZIP file.
4. Index the uploaded repository.
5. Ask architecture or codebase questions.
6. Generate onboarding summaries.
7. Use the debug assistant for repository-specific issues.
8. Review retrieved sources, agent steps, and verifier notes.

## Screenshots

### Repository Dashboard

![Repository Dashboard](docs/screenshots/Homepage.png)

### Indexed Repository

![Indexed Repository](docs/screenshots/Indexed.png)

### Agent Answer

![Agent Answer](docs/screenshots/Agent_answer.png)

### Sources and Agent Steps

![Sources and Verifier](docs/screenshots/Sources&agentsteps.png)

### Verifier 

![Debug Assistant](docs/screenshots/verifier.png)