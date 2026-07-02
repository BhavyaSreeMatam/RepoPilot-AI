from typing import Dict, List

from openai import OpenAI

from app.core.config import get_settings
from app.services.vector_service import search_repository


ANSWER_MODEL = "gpt-4o-mini"


def get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def build_context_from_matches(matches: List[Dict]) -> str:
    """
    Build a source-grounded context block for the LLM.
    """

    context_parts = []

    for index, match in enumerate(matches, start=1):
        context_parts.append(
            f"""
Source {index}
File: {match["file_path"]}
Language: {match["language"]}
Lines: {match["start_line"]}-{match["end_line"]}

Content:
{match["content_preview"]}
""".strip()
        )

    return "\n\n---\n\n".join(context_parts)


def build_sources(matches: List[Dict]) -> List[Dict]:
    """
    Return clean citation metadata for the frontend/API response.
    """

    sources = []

    for index, match in enumerate(matches, start=1):
        sources.append({
            "source_number": index,
            "file_path": match["file_path"],
            "language": match["language"],
            "start_line": match["start_line"],
            "end_line": match["end_line"],
            "similarity_distance": match["similarity_distance"],
        })

    return sources


def answer_question(repo_id: str, question: str, top_k: int = 5) -> Dict:
    """
    Search the repository and generate a grounded answer using retrieved chunks only.
    """

    search_result = search_repository(
        repo_id=repo_id,
        query=question,
        top_k=top_k
    )

    matches = search_result["matches"]

    if not matches:
        return {
            "repo_id": repo_id,
            "question": question,
            "answer": "I could not find relevant code chunks for this question.",
            "sources": [],
        }

    context = build_context_from_matches(matches)
    sources = build_sources(matches)

    client = get_openai_client()

    system_prompt = """
You are RepoPilot AI, a codebase understanding assistant.

Rules:
1. Answer only using the provided source chunks.
2. Do not invent files, functions, classes, or behavior that are not present in the sources.
3. If the sources are not enough, say that the retrieved context is not enough.
4. Mention specific file paths and line ranges when useful.
5. Keep the answer clear and practical for a developer trying to understand the codebase.
""".strip()

    user_prompt = f"""
Question:
{question}

Retrieved source chunks:
{context}

Write a grounded answer using only the retrieved source chunks.
""".strip()

    response = client.chat.completions.create(
        model=ANSWER_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    return {
        "repo_id": repo_id,
        "question": question,
        "answer": answer,
        "sources": sources,
    }