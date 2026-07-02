from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import zipfile
import uuid
import os

from app.services.repo_scanner import scan_repository
from app.services.code_chunker import create_code_chunks
from app.services.vector_service import index_repository, search_repository,delete_repository_index
from app.services.answer_service import answer_question
from app.schemas.repo_schemas import AskRepoRequest

router = APIRouter(
    prefix="/repos",
    tags=["Repositories"]
)

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploads"
EXTRACT_DIR = BASE_DIR / "extracted_repos"

def get_uploaded_zip_for_repo(repo_id: str):
    """
    Finds the uploaded ZIP file for a repo_id.
    Upload files are stored as: {repo_id}_{original_filename}
    """

    if not UPLOAD_DIR.exists():
        return None

    matches = list(UPLOAD_DIR.glob(f"{repo_id}_*.zip"))

    if not matches:
        return None

    return matches[0]


def get_original_filename(repo_id: str) -> str:
    """
    Gets the original ZIP filename from the saved upload filename.
    """

    zip_path = get_uploaded_zip_for_repo(repo_id)

    if not zip_path:
        return "unknown"

    prefix = f"{repo_id}_"
    return zip_path.name.replace(prefix, "", 1)


def get_repo_root_name(extract_path: Path) -> str:
    """
    Attempts to find the top-level folder name inside the extracted repository.
    """

    if not extract_path.exists():
        return "unknown"

    children = [item for item in extract_path.iterdir() if item.is_dir()]

    if len(children) == 1:
        return children[0].name

    return extract_path.name

def safe_extract_zip(zip_path: Path, extract_path: Path):
    """
    Safely extract ZIP files.
    Skips files that cannot be extracted instead of crashing the upload.
    Also prevents path traversal attacks.
    """

    skipped_files = []

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_name = member.filename

            # Skip directories
            if member.is_dir():
                continue

            # Prevent unsafe paths like ../../file.py
            target_path = extract_path / member_name
            resolved_target = target_path.resolve()
            resolved_extract_root = extract_path.resolve()

            if not str(resolved_target).startswith(str(resolved_extract_root)):
                skipped_files.append({
                    "file": member_name,
                    "reason": "Unsafe path skipped"
                })
                continue

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with zip_ref.open(member) as source_file:
                    with open(target_path, "wb") as target_file:
                        shutil.copyfileobj(source_file, target_file)

            except PermissionError:
                skipped_files.append({
                    "file": member_name,
                    "reason": "Permission denied"
                })
                continue

            except OSError as e:
                skipped_files.append({
                    "file": member_name,
                    "reason": str(e)
                })
                continue

    return skipped_files

@router.post("/upload")
async def upload_repo(file: UploadFile = File(...)):
    """
    Upload a ZIP file containing a codebase.
    The backend saves, extracts, and scans the repository.
    """

    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only .zip files are supported for now."
        )

    repo_id = str(uuid.uuid4())

    UPLOAD_DIR.mkdir(exist_ok=True)
    EXTRACT_DIR.mkdir(exist_ok=True)

    zip_path = UPLOAD_DIR / f"{repo_id}_{file.filename}"
    extract_path = EXTRACT_DIR / repo_id

    with zip_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    skipped_files = []

    try:
        skipped_files = safe_extract_zip(zip_path, extract_path)
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid ZIP file."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract ZIP file: {str(e)}"
        )

    try:
        scan_result = scan_repository(extract_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan repository: {str(e)}"
        )



    return {
        "message": "Repository uploaded and scanned successfully.",
        "repo_id": repo_id,
        "original_filename": file.filename,
        "saved_zip_path": str(zip_path),
        "extracted_path": str(extract_path),
        "total_files_found": scan_result["total_files_found"],
        "code_files_found": scan_result["code_files_found"],
        "ignored_files": scan_result["ignored_files"],
        "languages": scan_result["languages"],
        "sample_code_files": scan_result["code_files"][:20],
    }


@router.get("")
def list_repositories():
    """
    List uploaded/extracted repositories.
    """

    repositories = []

    if not EXTRACT_DIR.exists():
        return {
            "total_repositories": 0,
            "repositories": []
        }

    for repo_folder in EXTRACT_DIR.iterdir():
        if not repo_folder.is_dir():
            continue

        repo_id = repo_folder.name
        zip_path = get_uploaded_zip_for_repo(repo_id)

        repositories.append({
            "repo_id": repo_id,
            "repo_name": get_repo_root_name(repo_folder),
            "original_filename": get_original_filename(repo_id),
            "extracted_path": str(repo_folder),
            "uploaded_zip_path": str(zip_path) if zip_path else None,
            "indexed": True,
        })

    return {
        "total_repositories": len(repositories),
        "repositories": repositories
    }

@router.delete("/{repo_id}")
def delete_repository(repo_id: str):
    """
    Delete an uploaded repository, extracted files, and vector index.
    """

    repo_path = EXTRACT_DIR / repo_id
    zip_path = get_uploaded_zip_for_repo(repo_id)

    deleted_items = []
    warnings = []

    if zip_path and zip_path.exists():
        try:
            zip_path.unlink()
            deleted_items.append(str(zip_path))
        except Exception as e:
            warnings.append(f"Could not delete uploaded ZIP: {str(e)}")

    if repo_path.exists():
        try:
            shutil.rmtree(repo_path)
            deleted_items.append(str(repo_path))
        except Exception as e:
            warnings.append(f"Could not delete extracted repository: {str(e)}")
    else:
        warnings.append("Extracted repository folder was not found.")

    vector_delete_result = delete_repository_index(repo_id)

    return {
        "repo_id": repo_id,
        "message": "Repository deletion completed.",
        "deleted_items": deleted_items,
        "vector_index": vector_delete_result,
        "warnings": warnings,
    }

@router.get("/{repo_id}/scan")
def scan_existing_repo(repo_id: str):
    """
    Scan an already extracted repository by repo_id.
    """

    repo_path = EXTRACT_DIR / repo_id

    if not repo_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Repository not found."
        )

    try:
        scan_result = scan_repository(repo_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan repository: {str(e)}"
        )

    return {
        "repo_id": repo_id,
        "total_files_found": scan_result["total_files_found"],
        "code_files_found": scan_result["code_files_found"],
        "ignored_files": scan_result["ignored_files"],
        "languages": scan_result["languages"],
        "sample_code_files": scan_result["code_files"][:50],
    }


@router.get("/{repo_id}/chunks")
def get_repo_chunks(repo_id: str):
    """
    Create code chunks for an already extracted repository.
    """

    repo_path = EXTRACT_DIR / repo_id

    if not repo_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Repository not found."
        )

    try:
        chunk_result = create_code_chunks(repo_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create code chunks: {str(e)}"
        )

    sample_chunks = []

    for chunk in chunk_result["chunks"][:10]:
        content = chunk["content"]

        sample_chunks.append({
            "file_path": chunk["file_path"],
            "language": chunk["language"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "content_preview": content[:500],
        })

    return {
        "repo_id": repo_id,
        "total_files_used": chunk_result["total_files_used"],
        "total_chunks": chunk_result["total_chunks"],
        "sample_chunks": sample_chunks,
    }

@router.post("/{repo_id}/index")
def index_repo(repo_id: str):
    """
    Index repository chunks into the vector database.
    """

    repo_path = EXTRACT_DIR / repo_id

    if not repo_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Repository not found."
        )

    try:
        index_result = index_repository(repo_id, repo_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to index repository: {str(e)}"
        )

    return index_result


@router.get("/{repo_id}/search")
def search_repo(repo_id: str, query: str, top_k: int = 5):
    """
    Search indexed repository chunks using natural language.
    """

    repo_path = EXTRACT_DIR / repo_id

    if not repo_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Repository not found."
        )

    if not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty."
        )

    try:
        search_result = search_repository(repo_id, query, top_k)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search repository: {str(e)}"
        )

    return search_result

@router.post("/{repo_id}/ask")
def ask_repo(repo_id: str, request: AskRepoRequest):
    """
    Ask a natural language question about an indexed repository.
    The answer is generated from retrieved code chunks.
    """

    repo_path = EXTRACT_DIR / repo_id

    if not repo_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Repository not found."
        )

    try:
        answer_result = answer_question(
            repo_id=repo_id,
            question=request.question,
            top_k=request.top_k,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )

    return answer_result

