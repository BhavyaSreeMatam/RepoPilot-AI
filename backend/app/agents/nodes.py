from typing import Dict, Any, List
from pathlib import Path

from openai import OpenAI

from app.agents.state import RepoPilotState
from app.agents.llm_utils import build_context_text, run_llm_agent
from app.agents.mcp_client import get_mcp_session
from app.services.vector_service import search_repository
from app.services.security_scanner import scan_security_repository


# Maps the router's route values to the corresponding MCP tool names.
# Note the router emits "general_rag", which maps to the "general_agent" tool.
ROUTE_TO_TOOL = {
    "architecture": "architecture_agent",
    "bug": "bug_agent",
    "security": "security_agent",
    "docs": "docs_agent",
    "general_rag": "general_agent",
}


def router_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Uses an LLM to decide which specialized agent should handle the question.
    """

    client = OpenAI()

    question = state["question"]

    system_prompt = """
You are RepoPilot AI's Router Agent.

Your job is to classify the user's repository question into exactly one route.

Allowed routes:
- architecture
- bug
- security
- docs
- general_rag

Route meanings:
- architecture: questions about project structure, folders, modules, classes, data flow, control flow, system design, onboarding summaries
- bug: questions about errors, failures, tracebacks, exceptions, debugging, broken behavior, fixes, or files to inspect
- security: questions about secrets, environment variables, API keys, vulnerabilities, unsafe code, authentication, authorization, or security risks
- docs: questions asking for README content, documentation, comments, explanations of files, or generating documentation
- general_rag: general repository questions that do not clearly fit the other categories

Return only the route name.
Do not include explanation.
Do not include punctuation.
"""

    user_prompt = f"""
Question:
{question}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            temperature=0,
        )

        route = response.choices[0].message.content.strip().lower()

    except Exception:
        route = "general_rag"

    allowed_routes = {
        "architecture",
        "bug",
        "security",
        "docs",
        "general_rag",
    }

    if route not in allowed_routes:
        route = "general_rag"

    return {
        "route": route,
        "steps": state.get("steps", []) + [f"llm_router_agent selected route: {route}"],
    }


def retriever_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Retrieves relevant repository chunks.
    Uses route-aware retrieval depth so each specialized agent gets enough context.
    """

    repo_id = state["repo_id"]
    question = state["question"]
    route = state.get("route", "general_rag")

    top_k_by_route = {
        "architecture": 8,
        "bug": 6,
        "security": 8,
        "docs": 8,
        "general_rag": 5,
    }

    top_k = top_k_by_route.get(route, 5)

    search_result = search_repository(
        repo_id=repo_id,
        query=question,
        top_k=top_k,
    )

    matches = search_result.get("matches", [])

    return {
        "contexts": matches,
        "steps": state.get("steps", []) + [
            f"retriever_agent found {len(matches)} chunks using top_k={top_k}"
        ],
    }


def security_scan_node(state: RepoPilotState) -> Dict[str, Any]:
    """
    Runs a repository-wide deterministic security scan only when the router
    selected the security route.

    Findings are stored in structured form and also converted into additional
    contexts so the existing MCP security_agent and verifier can reason over
    them without changing the MCP tool interface.
    """

    route = state.get("route", "general_rag")

    if route != "security":
        return {
            "security_findings": [],
            "security_scan_summary": None,
            "steps": state.get("steps", []) + [
                "security_scan_node skipped because route was not security"
            ],
        }

    repo_id = state["repo_id"]

    # nodes.py is backend/app/agents/nodes.py
    # parents[2] resolves to backend/
    backend_root = Path(__file__).resolve().parents[2]
    repo_path = backend_root / "extracted_repos" / repo_id

    try:
        scan_result = scan_security_repository(repo_path)

    except Exception as exc:
        return {
            "security_findings": [],
            "security_scan_summary": {
                "status": "failed",
                "error": str(exc),
            },
            "steps": state.get("steps", []) + [
                f"security_scan_node failed: {exc}"
            ],
        }

    findings = scan_result.get("findings", [])

    security_scan_summary = {
        "files_scanned": scan_result.get("files_scanned", 0),
        "files_skipped": scan_result.get("files_skipped", 0),
        "findings_count": scan_result.get("findings_count", 0),
        "severity_counts": scan_result.get("severity_counts", {}),
    }

    # Keep the highest-severity findings first so we do not send an enormous
    # repository scan into the LLM if a repository contains many findings.
    severity_rank = {
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
        "INFO": 4,
    }

    sorted_findings = sorted(
        findings,
        key=lambda item: severity_rank.get(item.get("severity", "INFO"), 99),
    )

    findings_for_context = sorted_findings[:25]

    security_contexts = []

    for finding in findings_for_context:
        content = f"""
Repository-wide static security scan finding.

Rule ID: {finding.get("rule_id")}
Severity: {finding.get("severity")}
Category: {finding.get("category")}
File: {finding.get("file_path")}
Lines: {finding.get("start_line")}-{finding.get("end_line")}
Finding: {finding.get("message")}
Evidence: {finding.get("evidence")}

This finding came from RepoPilot's deterministic read-only security scanner.
Treat it as scanner evidence, but explain actual exploitability carefully and
do not exaggerate the risk without supporting repository context.
""".strip()

        security_contexts.append(
            {
                "file_path": finding.get("file_path", "unknown"),
                "language": "Security Scan",
                "start_line": finding.get("start_line"),
                "end_line": finding.get("end_line"),
                "similarity_distance": None,
                "content": content,
            }
        )

    combined_contexts = state.get("contexts", []) + security_contexts

    return {
        "contexts": combined_contexts,
        "security_findings": findings,
        "security_scan_summary": security_scan_summary,
        "steps": state.get("steps", []) + [
            (
                "security_scan_node scanned "
                f"{security_scan_summary['files_scanned']} files and found "
                f"{security_scan_summary['findings_count']} potential findings"
            )
        ],
    }


async def specialized_agent_node(state: RepoPilotState) -> Dict[str, Any]:
    """
    Dispatches the question to the correct specialized agent via an MCP tool call.
    The specialized agents run in a separate MCP server process (see app/mcp_server/server.py).
    """

    route = state.get("route", "general_rag")
    tool_name = ROUTE_TO_TOOL.get(route, "general_agent")

    try:
        session = await get_mcp_session()
        result = await session.call_tool(
            tool_name,
            arguments={
                "question": state["question"],
                "contexts": state.get("contexts", []),
            },
        )

        answer = "\n".join(
            block.text for block in result.content if hasattr(block, "text")
        )

        # A FastMCP tool that raises internally surfaces as isError=True with the
        # error text in content, not as a transport-level exception, so funnel it
        # through the same fallback path below.
        if getattr(result, "isError", False):
            raise RuntimeError(answer or "MCP tool reported an error")

        step = f"{tool_name} agent (via MCP) generated answer"

    except Exception as exc:
        answer = (
            "The specialized analysis agent is currently unavailable "
            f"({exc}). Please retry your question."
        )
        step = f"{tool_name} agent (via MCP) failed: {exc}"

    return {
        "answer": answer,
        "steps": state.get("steps", []) + [step],
    }


def verifier_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Verifies whether the generated answer is grounded in retrieved context.
    """

    client = OpenAI()

    question = state["question"]
    answer = state.get("answer", "")
    contexts = state.get("contexts", [])

    context_text = build_context_text(contexts)

    system_prompt = """
You are RepoPilot AI's Verifier Agent.

Your job is to check whether the generated answer is supported by the retrieved repository context.

Return your response in this exact format:

VERIFIED: yes or no

NOTES:
- Briefly explain whether the answer is grounded in the context.
- Mention any unsupported claims.
- Mention if more files are needed.
"""

    user_prompt = f"""
User question:
{question}

Generated answer:
{answer}

Retrieved repository context:
{context_text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=0,
    )

    verifier_output = response.choices[0].message.content or ""

    verified = "verified: yes" in verifier_output.lower()

    return {
        "verified": verified,
        "verifier_notes": verifier_output,
        "steps": state.get("steps", []) + ["verifier_agent checked answer grounding"],
    }