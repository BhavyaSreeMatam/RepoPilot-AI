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


def get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def get_chroma_client():
    VECTOR_STORE_DIR.mkdir(exist_ok=True)

    return chromadb.PersistentClient(
        path=str(VECTOR_STORE_DIR),
        settings=ChromaSettings(anonymized_telemetry=False)
    )


def get_collection(repo_id: str):
    client = get_chroma_client()

    collection_name = f"repo_{repo_id.replace('-', '_')}"

    return client.get_or_create_collection(
        name=collection_name,
        metadata={"description": f"Code chunks for repo {repo_id}"}
    )


def create_embedding(text: str) -> List[float]:
    client = get_openai_client()

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )

    return response.data[0].embedding


def format_chunk_for_embedding(chunk: Dict) -> str:
    """
    Add metadata into the text being embedded.
    This helps semantic search understand file path, filename, language, and code content.
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


def index_repository(repo_id: str, repo_path: Path) -> Dict:
    """
    Create chunks, generate embeddings, and store them in ChromaDB.
    """

    chunk_result = create_code_chunks(repo_path)
    chunks = chunk_result["chunks"]

    if not chunks:
        return {
            "repo_id": repo_id,
            "indexed_chunks": 0,
            "message": "No chunks found to index."
        }

    collection = get_collection(repo_id)

    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for index, chunk in enumerate(chunks):
        chunk_id = f"{repo_id}_{index}"

        text_for_embedding = format_chunk_for_embedding(chunk)
        embedding = create_embedding(text_for_embedding)

        ids.append(chunk_id)
        documents.append(text_for_embedding)
        embeddings.append(embedding)

        metadatas.append({
            "repo_id": repo_id,
            "file_path": chunk["file_path"],
            "language": chunk["language"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
        })

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return {
        "repo_id": repo_id,
        "total_files_used": chunk_result["total_files_used"],
        "indexed_chunks": len(chunks),
        "message": "Repository indexed successfully."
    }


def search_repository(repo_id: str, query: str, top_k: int = 5) -> Dict:
    """
    Search indexed repo chunks using semantic similarity.
    """

    collection = get_collection(repo_id)

    query_embedding = create_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    matches = []

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i in range(len(ids)):
        metadata = metadatas[i]
        document = documents[i]

        matches.append({
            "chunk_id": ids[i],
            "file_path": metadata["file_path"],
            "language": metadata["language"],
            "start_line": metadata["start_line"],
            "end_line": metadata["end_line"],
            "similarity_distance": distances[i],
            "content_preview": document[:1000],
        })

    return {
        "repo_id": repo_id,
        "query": query,
        "top_k": top_k,
        "matches": matches,
    }

def delete_repository_index(repo_id: str) -> Dict:
    """
    Delete the ChromaDB collection for a repository.
    """

    client = get_chroma_client()
    collection_name = f"repo_{repo_id.replace('-', '_')}"

    try:
        client.delete_collection(name=collection_name)

        return {
            "repo_id": repo_id,
            "collection_name": collection_name,
            "deleted": True,
            "message": "Repository vector index deleted successfully."
        }

    except Exception as e:
        return {
            "repo_id": repo_id,
            "collection_name": collection_name,
            "deleted": False,
            "message": f"Vector index could not be deleted or did not exist: {str(e)}"
        }