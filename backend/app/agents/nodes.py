from typing import Dict, Any, List

from openai import OpenAI

from app.agents.state import RepoPilotState

# IMPORTANT:
# Adjust this import to match your existing search function.
# You already built indexing + search earlier, so we want to reuse that.
#
# Example possibilities from your earlier stages may be:
# from app.services.search_service import search_codebase
# from app.services.rag_service import search_chunks
# from app.vectorstore.chroma_store import search_chunks
#
# For now, update this import to the actual function name in your project.
from app.services.vector_service import search_repository

def build_context_text(contexts: list) -> str:
    """
    Converts retrieved chunks into one readable context block for the LLM.
    """

    return "\n\n".join(
        [
            f"File: {item.get('file_path', item.get('source', 'unknown'))}\n"
            f"Language: {item.get('language', 'unknown')}\n"
            f"Lines: {item.get('start_line', '?')}-{item.get('end_line', '?')}\n"
            f"Content:\n{item.get('content_preview', item.get('content', item.get('text', item.get('chunk_text', ''))))}"
            for item in contexts
        ]
    )

def run_llm_agent(system_prompt: str, question: str, contexts: list) -> str:
    """
    Runs an OpenAI chat completion using retrieved repository context.
    """

    client = OpenAI()

    context_text = build_context_text(contexts)

    user_prompt = f"""
User question:
{question}

Repository context:
{context_text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content

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


def answer_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Generates the final answer using retrieved repo context.
    """

    question = state["question"]
    route = state.get("route", "general_rag")
    contexts = state.get("contexts", [])

    context_text = "\n\n".join(
    [
        f"File: {item.get('file_path', item.get('source', 'unknown'))}\n"
        f"Language: {item.get('language', 'unknown')}\n"
        f"Lines: {item.get('start_line', '?')}-{item.get('end_line', '?')}\n"
        f"Content:\n{item.get('content_preview', item.get('content', item.get('text', item.get('chunk_text', ''))))}"
        for item in contexts
    ]
)

    system_prompt = f"""
You are RepoPilot AI, an AI engineering copilot for understanding codebases.

The user's question type is: {route}

Use the provided repository context to answer.
Be specific and practical.
Mention relevant files when possible.
If the context is not enough, say what is missing instead of making things up.
"""

    user_prompt = f"""
User question:
{question}

Repository context:
{context_text}
"""
    client=OpenAI()

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    return {
        "answer": answer,
        "steps": state.get("steps", []) + ["answer_agent generated final answer"],
    }

def architecture_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Specialized agent for repository architecture questions.
    """

    system_prompt = """
You are RepoPilot AI's Architecture Agent.

Your job is to explain repository architecture using only the retrieved repository context.

Use this exact response structure:

# Architecture Overview

## 1. Short Summary
Give a brief summary of what the repository appears to do.

## 2. Main Folders and Files
List the main folders/files found in the retrieved context.
For each one, explain its likely role.

## 3. Important Components
Identify important classes, functions, modules, or configuration files.
Explain what each one does.

## 4. How Components Interact
Explain the control flow or data flow between components.
Be clear about which files/classes interact.

## 5. Where a New Developer Should Start
Recommend which files to read first and why.

## 6. Missing Context
Mention files or details that would help produce a more complete architecture explanation.

Rules:
- Use only the retrieved repository context.
- Mention file paths when relevant.
- Do not invent files that are not in the context.
- If something is inferred, clearly say it is inferred.
"""

    answer = run_llm_agent(
        system_prompt=system_prompt,
        question=state["question"],
        contexts=state.get("contexts", []),
    )

    return {
        "answer": answer,
        "steps": state.get("steps", []) + ["architecture_agent generated answer"],
    }


def bug_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Specialized agent for debugging and failure investigation.
    """

    system_prompt = """
Your job is to help debug repository issues using only the retrieved repository context.

Use this exact response structure:

# Bug Diagnosis

## 1. Likely Cause
Explain the most likely cause based on the retrieved code/context.

## 2. Files to Inspect
List the most relevant files.
For each file, explain why it matters.

## 3. Relevant Functions or Classes
List functions/classes/methods involved in the issue.
Mention line ranges when available from the context.

## 4. Step-by-Step Debugging Plan
Give clear steps a developer should follow to investigate.

## 5. Possible Fix or Next Action
Suggest likely fixes or next actions, but only if supported by the context.

## 6. Missing Information
Mention what extra logs, files, traceback, config, or runtime details would help.

Rules:
- Use only the retrieved repository context.
- Do not pretend to know the exact runtime failure unless it appears in the context.
- Clearly separate confirmed facts from likely causes.
- Mention file paths and line ranges when relevant.
"""


    answer = run_llm_agent(
        system_prompt=system_prompt,
        question=state["question"],
        contexts=state.get("contexts", []),
    )

    return {
        "answer": answer,
        "steps": state.get("steps", []) + ["bug_agent generated answer"],
    }


def security_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Specialized agent for security/configuration review.
    """

    system_prompt = """
You are RepoPilot AI's Security Agent.

Your job is to inspect retrieved repository context for security-sensitive information and risks.

Use this exact response structure:

# Security Review

## 1. Confirmed Findings
List security-sensitive items that are directly supported by the retrieved context.
Examples: secrets, environment variables, config files, auth logic, keys, tokens, credentials, unsafe command execution.

## 2. Sensitive Files or Configurations
List files that appear security-relevant.
Explain why each file matters.

## 3. Potential Risks
Explain possible risks based only on the retrieved context.
Clearly say when something is only a potential risk.

## 4. Recommendations
Give practical recommendations for safer handling.

## 5. Missing Context
Mention additional files or information needed for a stronger security review.

Rules:
- Use only the retrieved repository context.
- Do not claim a hardcoded secret exists unless it appears in the context.
- Do not exaggerate risks.
- Mention file paths and line ranges when relevant.
"""

    answer = run_llm_agent(
        system_prompt=system_prompt,
        question=state["question"],
        contexts=state.get("contexts", []),
    )

    return {
        "answer": answer,
        "steps": state.get("steps", []) + ["security_agent generated answer"],
    }


def docs_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Specialized agent for documentation-style answers.
    """

    system_prompt = """
You are RepoPilot AI's Documentation Agent.

Your job is to generate clear developer documentation using only the retrieved repository context.

Use this exact response structure:

# Repository Documentation

## 1. Overview
Briefly explain what this part of the repository appears to do.

## 2. Important Files
List important files from the retrieved context.
For each file, explain its purpose.

## 3. Important Classes, Functions, or Sections
Explain important classes, functions, methods, HTML sections, config fields, or documentation sections found in the context.

## 4. How to Use This Information
Explain how a developer would use this documentation to understand or work with the repository.

## 5. Missing Documentation
Mention what additional files or comments would improve the documentation.

Rules:
- Use only the retrieved repository context.
- Mention file paths when relevant.
- Write clearly for a new developer.
- Do not invent setup steps or features that are not in the context.
"""

    answer = run_llm_agent(
        system_prompt=system_prompt,
        question=state["question"],
        contexts=state.get("contexts", []),
    )

    return {
        "answer": answer,
        "steps": state.get("steps", []) + ["docs_agent generated answer"],
    }


def general_agent(state: RepoPilotState) -> Dict[str, Any]:
    """
    Default general repository Q&A agent.
    """

    system_prompt = """
You are RepoPilot AI's General Repository Agent.

Your job is to answer general repository questions using only the retrieved repository context.

Use this response structure:

# Answer

## 1. Direct Answer
Answer the user's question clearly.

## 2. Supporting Evidence
Mention the files, classes, functions, or documentation sections that support the answer.

## 3. Important Details
Explain any relevant details from the context.

## 4. Missing Context
Mention what additional files or information would help if the answer is incomplete.

Rules:
- Use only the retrieved repository context.
- Mention file paths when relevant.
- If the retrieved context does not contain enough information, say that clearly.
- Do not invent details.
"""

    answer = run_llm_agent(
        system_prompt=system_prompt,
        question=state["question"],
        contexts=state.get("contexts", []),
    )

    return {
        "answer": answer,
        "steps": state.get("steps", []) + ["general_agent generated answer"],
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