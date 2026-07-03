from dotenv import load_dotenv

# override=True so backend/.env is the single source of truth even if a stale
# OPENAI_API_KEY is already present in the OS/shell environment.
load_dotenv(override=True)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.repo_routes import router as repo_router
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.agents.graph import repopilot_graph
from app.agents.mcp_client import get_mcp_session, close_mcp_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Spawn the specialized-agents MCP server subprocess once at boot.
    # Fails fast if the subprocess cannot start or initialize.
    await get_mcp_session()
    yield
    await close_mcp_session()


app = FastAPI(
    title="RepoPilot AI",
    description="An AI Engineering Copilot for Codebase Understanding, Debugging, and Developer Onboarding",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(repo_router)


@app.get("/")
def root():
    return {
        "message": "RepoPilot AI backend is running",
        "version": "0.1.0"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }

class AgentSummarizeRequest(BaseModel):
    repo_id: str

class AgentAskRequest(BaseModel):
    repo_id: str
    question: str


class SourceItem(BaseModel):
    file_path: str
    language: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    similarity_distance: Optional[float] = None


class AgentAskResponse(BaseModel):
    repo_id: str
    question: str
    route: Optional[str]
    answer: str
    verified: Optional[bool] = None
    verifier_notes: Optional[str] = None
    sources: List[SourceItem]
    steps: List[str]

class AgentDebugRequest(BaseModel):
    repo_id: str
    error_message: str
    extra_context: Optional[str] = None

def build_sources_from_contexts(contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converts full retrieved chunks into clean source metadata for API responses.
    """

    sources = []

    for item in contexts:
        sources.append(
            {
                "file_path": item.get("file_path", item.get("source", "unknown")),
                "language": item.get("language"),
                "start_line": item.get("start_line"),
                "end_line": item.get("end_line"),
                "similarity_distance": item.get("similarity_distance"),
            }
        )

    return sources

@app.post("/agent/ask", response_model=AgentAskResponse)
async def agent_ask(request: AgentAskRequest):
    """
    LangGraph-powered multi-agent ask endpoint.
    """

    initial_state = {
        "repo_id": request.repo_id,
        "question": request.question,
        "route": None,
        "contexts": [],
        "answer": None,
        "verified": None,
        "verifier_notes": None,
        "steps": [],
    }

    result = await repopilot_graph.ainvoke(initial_state)

    contexts = result.get("contexts", [])
    sources = build_sources_from_contexts(contexts)

    return {
            "repo_id": request.repo_id,
            "question": request.question,
            "route": result.get("route"),
            "answer": result.get("answer"),
            "verified": result.get("verified"),
            "verifier_notes": result.get("verifier_notes"),
            "sources": sources,
            "steps": result.get("steps", []),
        }

@app.post("/agent/summarize", response_model=AgentAskResponse)
async def agent_summarize(request: AgentSummarizeRequest):
    """
    Generate a developer onboarding summary for a repository.
    """

    summary_question = """
Give a developer onboarding summary of this repository.

Include:
- project purpose
- main folders and files
- important modules/classes/functions
- high-level architecture and control flow
- setup or configuration clues
- where a new developer should start reading
- possible risks or missing context

Use only the retrieved repository context.
Mention relevant file paths.
"""

    initial_state = {
        "repo_id": request.repo_id,
        "question": summary_question,
        "route": "architecture",
        "contexts": [],
        "answer": None,
        "verified": None,
        "verifier_notes": None,
        "steps": [],
    }

    result = await repopilot_graph.ainvoke(initial_state)

    contexts = result.get("contexts", [])
    sources = build_sources_from_contexts(contexts)

    return {
        "repo_id": request.repo_id,
        "question": "Developer onboarding summary",
        "route": result.get("route"),
        "answer": result.get("answer"),
        "verified": result.get("verified"),
        "verifier_notes": result.get("verifier_notes"),
        "sources": sources,
        "steps": result.get("steps", []),
    }

@app.post("/agent/debug", response_model=AgentAskResponse)
async def agent_debug(request: AgentDebugRequest):
    """
    Diagnose a repository bug/error using the multi-agent pipeline.
    """

    debug_question = f"""
A developer is debugging this repository.

Error or issue:
{request.error_message}

Extra context:
{request.extra_context or "No extra context provided."}

Please provide:
- likely cause
- most relevant files to inspect
- relevant functions/classes
- step-by-step debugging plan
- possible fix or next action
- what additional information would help if the context is incomplete

Use only the retrieved repository context.
Mention relevant file paths and line ranges when possible.
"""

    initial_state = {
        "repo_id": request.repo_id,
        "question": debug_question,
        "route": None,
        "contexts": [],
        "answer": None,
        "verified": None,
        "verifier_notes": None,
        "steps": [],
    }

    result = await repopilot_graph.ainvoke(initial_state)

    contexts = result.get("contexts", [])
    sources = build_sources_from_contexts(contexts)

    return {
        "repo_id": request.repo_id,
        "question": request.error_message,
        "route": result.get("route"),
        "answer": result.get("answer"),
        "verified": result.get("verified"),
        "verifier_notes": result.get("verifier_notes"),
        "sources": sources,
        "steps": result.get("steps", []),
    }