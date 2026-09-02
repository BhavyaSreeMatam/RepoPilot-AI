from pathlib import Path
from typing import Dict, List

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from app.core.config import get_settings
from app.services.code_chunker import create_code_chunks


BASE_DIR = Path(__file__).resolve().parents[2]
VECTOR_STORE_DIR = BASE_DIR / "vector_store"

EMBEDDING_MODEL = "text-embedding-3-small"

# Instead of making one OpenAI request per chunk, send chunks in batches.
# 32 is conservative enough for code chunks while still reducing hundreds
# of requests to only a handful.
EMBEDDING_BATCH_SIZE = 32


def get_openai_client() -> OpenAI:
    settings = get_settings()

    return OpenAI(
        api_key=settings.openai_api_key,
    )


def get_chroma_client():
    VECTOR_STORE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return chromadb.PersistentClient(
        path=str(VECTOR_STORE_DIR),
        settings=ChromaSettings(
            anonymized_telemetry=False
        ),
    )


def get_collection(repo_id: str):
    client = get_chroma_client()

    collection_name = (
        f"repo_{repo_id.replace('-', '_')}"
    )

    return client.get_or_create_collection(
        name=collection_name,
        metadata={
            "description": (
                f"Code chunks for repo {repo_id}"
            )
        },
    )


def create_embedding(
    text: str,
) -> List[float]:
    """
    Create one embedding.

    This remains useful for semantic-search queries, where we only
    need one embedding at a time.
    """

    client = get_openai_client()

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


def create_embeddings(
    texts: List[str],
) -> List[List[float]]:
    """
    Create embeddings for many documents efficiently.

    OpenAI's embeddings API accepts multiple input strings in one
    request, so repository indexing should batch chunks rather than
    issuing one HTTP request per chunk.
    """

    if not texts:
        return []

    client = get_openai_client()

    embeddings: List[List[float]] = []

    total_texts = len(texts)

    for batch_start in range(
        0,
        total_texts,
        EMBEDDING_BATCH_SIZE,
    ):
        batch_end = min(
            batch_start + EMBEDDING_BATCH_SIZE,
            total_texts,
        )

        batch = texts[
            batch_start:batch_end
        ]

        print(
            (
                "Embedding repository chunks "
                f"{batch_start + 1}-{batch_end} "
                f"of {total_texts}"
            ),
            flush=True,
        )

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )

        # Preserve the exact ordering of the input documents.
        response_items = sorted(
            response.data,
            key=lambda item: item.index,
        )

        embeddings.extend(
            item.embedding
            for item in response_items
        )

    if len(embeddings) != total_texts:
        raise RuntimeError(
            (
                "Embedding count mismatch: "
                f"expected {total_texts}, "
                f"received {len(embeddings)}."
            )
        )

    return embeddings


def format_chunk_for_embedding(
    chunk: Dict,
) -> str:
    """
    Add useful metadata to the embedded text.

    This gives semantic search information about the file path,
    filename, language, line range, and source content.
    """

    file_path = chunk["file_path"]
    file_name = Path(file_path).name

    return f"""
File path: {file_path}
File name: {file_name}
Language: {chunk["language"]}
Line range: {chunk["start_line"]}-{chunk["end_line"]}

This code/documentation chunk comes from {file_name} in the repository.

Content:
{chunk["content"]}
""".strip()


def index_repository(
    repo_id: str,
    repo_path: Path,
) -> Dict:
    """
    Create repository chunks, batch-generate embeddings,
    and store the resulting vectors in ChromaDB.
    """

    chunk_result = create_code_chunks(
        repo_path
    )

    chunks = chunk_result["chunks"]

    if not chunks:
        return {
            "repo_id": repo_id,
            "total_files_used": (
                chunk_result["total_files_used"]
            ),
            "indexed_chunks": 0,
            "message": (
                "No chunks found to index."
            ),
        }

    # Prepare all document text before calling the embeddings API.
    documents = [
        format_chunk_for_embedding(chunk)
        for chunk in chunks
    ]

    print(
        (
            f"Indexing repository {repo_id}: "
            f"{len(chunks)} chunks using "
            f"batch size {EMBEDDING_BATCH_SIZE}"
        ),
        flush=True,
    )

    # This is the major performance improvement.
    #
    # OLD:
    #   one OpenAI request per chunk
    #
    # NEW:
    #   one OpenAI request per batch of 32 chunks
    embeddings = create_embeddings(
        documents
    )

    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        ids.append(
            f"{repo_id}_{index}"
        )

        metadatas.append(
            {
                "repo_id": repo_id,
                "file_path": chunk[
                    "file_path"
                ],
                "language": chunk[
                    "language"
                ],
                "start_line": chunk[
                    "start_line"
                ],
                "end_line": chunk[
                    "end_line"
                ],
            }
        )

    collection = get_collection(
        repo_id
    )

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(
        (
            f"Repository {repo_id} indexed "
            f"successfully: {len(chunks)} chunks"
        ),
        flush=True,
    )

    return {
        "repo_id": repo_id,
        "total_files_used": (
            chunk_result["total_files_used"]
        ),
        "indexed_chunks": len(chunks),
        "message": (
            "Repository indexed successfully."
        ),
    }


def search_repository(
    repo_id: str,
    query: str,
    top_k: int = 5,
) -> Dict:
    """
    Search indexed repository chunks using semantic similarity.
    """

    collection = get_collection(
        repo_id
    )

    # Search only needs one embedding, so the single-item helper
    # is still appropriate here.
    query_embedding = create_embedding(
        query
    )

    results = collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=top_k,
    )

    matches = []

    ids = results.get(
        "ids",
        [[]],
    )[0]

    documents = results.get(
        "documents",
        [[]],
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]],
    )[0]

    distances = results.get(
        "distances",
        [[]],
    )[0]

    for i in range(len(ids)):
        metadata = metadatas[i]
        document = documents[i]

        matches.append(
            {
                "chunk_id": ids[i],
                "file_path": metadata[
                    "file_path"
                ],
                "language": metadata[
                    "language"
                ],
                "start_line": metadata[
                    "start_line"
                ],
                "end_line": metadata[
                    "end_line"
                ],
                "similarity_distance": (
                    distances[i]
                ),
                "content_preview": (
                    document[:1000]
                ),
            }
        )

    return {
        "repo_id": repo_id,
        "query": query,
        "top_k": top_k,
        "matches": matches,
    }


def delete_repository_index(
    repo_id: str,
) -> Dict:
    """
    Delete the ChromaDB collection for a repository.
    """

    client = get_chroma_client()

    collection_name = (
        f"repo_{repo_id.replace('-', '_')}"
    )

    try:
        client.delete_collection(
            name=collection_name
        )

        return {
            "repo_id": repo_id,
            "collection_name": (
                collection_name
            ),
            "deleted": True,
            "message": (
                "Repository vector index "
                "deleted successfully."
            ),
        }

    except Exception as exc:
        return {
            "repo_id": repo_id,
            "collection_name": (
                collection_name
            ),
            "deleted": False,
            "message": (
                "Vector index could not be "
                "deleted or did not exist: "
                f"{str(exc)}"
            ),
        }