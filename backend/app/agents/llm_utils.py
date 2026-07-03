from openai import OpenAI


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
