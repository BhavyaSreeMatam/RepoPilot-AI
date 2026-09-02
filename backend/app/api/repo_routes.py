from pathlib import Path
import shutil
import uuid
import zipfile
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.auth import get_current_user_sub
from app.schemas.repo_schemas import AskRepoRequest
from app.services.answer_service import answer_question
from app.services.code_chunker import create_code_chunks
from app.services.repo_scanner import scan_repository
from app.services.repository_metadata import (
    create_repository_metadata,
    delete_repository_metadata,
    list_user_repositories,
    mark_repository_indexed,
    require_repository_owner,
)
from app.services.vector_service import (
    delete_repository_index,
    index_repository,
    search_repository,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/repos",
    tags=["Repositories"],
)


BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploads"
EXTRACT_DIR = BASE_DIR / "extracted_repos"


def get_uploaded_zip_for_repo(repo_id: str):
    """
    Find the uploaded ZIP file for a repository.

    Upload files are stored as:
        {repo_id}_{original_filename}
    """

    if not UPLOAD_DIR.exists():
        return None

    matches = list(UPLOAD_DIR.glob(f"{repo_id}_*.zip"))

    if not matches:
        return None

    return matches[0]


def get_original_filename(repo_id: str) -> str:
    """
    Get the original ZIP filename from the saved upload filename.
    """

    zip_path = get_uploaded_zip_for_repo(repo_id)

    if not zip_path:
        return "unknown"

    prefix = f"{repo_id}_"
    return zip_path.name.replace(prefix, "", 1)


def get_repo_root_name(extract_path: Path) -> str:
    """
    Attempt to find the top-level folder name inside the extracted repository.
    """

    if not extract_path.exists():
        return "unknown"

    children = [
        item
        for item in extract_path.iterdir()
        if item.is_dir()
    ]

    if len(children) == 1:
        return children[0].name

    return extract_path.name


def cleanup_repository_files(
    repo_id: str,
    zip_path: Path | None = None,
    extract_path: Path | None = None,
):
    """
    Best-effort cleanup used when an upload fails before repository
    registration is completed.
    """

    if zip_path is None:
        zip_path = get_uploaded_zip_for_repo(repo_id)

    if extract_path is None:
        extract_path = EXTRACT_DIR / repo_id

    if zip_path and zip_path.exists():
        try:
            zip_path.unlink()
        except OSError:
            pass

    if extract_path.exists():
        try:
            shutil.rmtree(extract_path)
        except OSError:
            pass


def safe_extract_zip(
    zip_path: Path,
    extract_path: Path,
):
    """
    Safely extract ZIP files.

    Files that cannot safely be extracted are skipped instead of
    crashing the upload.

    Path traversal attempts such as ../../file.py are rejected.
    """

    skipped_files = []

    resolved_extract_root = extract_path.resolve()

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_name = member.filename

            if member.is_dir():
                continue

            target_path = extract_path / member_name
            resolved_target = target_path.resolve()

            try:
                resolved_target.relative_to(resolved_extract_root)
            except ValueError:
                skipped_files.append(
                    {
                        "file": member_name,
                        "reason": "Unsafe path skipped",
                    }
                )
                continue

            try:
                target_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                with zip_ref.open(member) as source_file:
                    with open(target_path, "wb") as target_file:
                        shutil.copyfileobj(
                            source_file,
                            target_file,
                        )

            except PermissionError:
                skipped_files.append(
                    {
                        "file": member_name,
                        "reason": "Permission denied",
                    }
                )

            except OSError as exc:
                skipped_files.append(
                    {
                        "file": member_name,
                        "reason": str(exc),
                    }
                )

    return skipped_files


def get_owned_repo_path(
    owner_sub: str,
    repo_id: str,
) -> Path:
    """
    Verify repository ownership before accessing files on disk.

    A repository belonging to another user is intentionally returned
    as 404 so RepoPilot does not reveal that the repository exists.
    """

    require_repository_owner(
        owner_sub=owner_sub,
        repo_id=repo_id,
    )

    repo_path = EXTRACT_DIR / repo_id

    if not repo_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    return repo_path


@router.post("/upload")
async def upload_repo(
    file: UploadFile = File(...),
    owner_sub: str = Depends(get_current_user_sub),
):
    """
    Upload a ZIP repository and assign ownership to the authenticated
    Cognito user.
    """

    original_filename = Path(file.filename or "").name

    if not original_filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only .zip files are supported for now.",
        )

    repo_id = str(uuid.uuid4())

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    EXTRACT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    zip_path = UPLOAD_DIR / f"{repo_id}_{original_filename}"
    extract_path = EXTRACT_DIR / repo_id

    try:
        with zip_path.open("wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )

        skipped_files = safe_extract_zip(
            zip_path,
            extract_path,
        )

        scan_result = scan_repository(extract_path)

        repo_name = get_repo_root_name(extract_path)

        create_repository_metadata(
            owner_sub=owner_sub,
            repo_id=repo_id,
            repo_name=repo_name,
            original_filename=original_filename,
        )

    except zipfile.BadZipFile:
        cleanup_repository_files(
            repo_id,
            zip_path,
            extract_path,
        )

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid ZIP file.",
        )

    except HTTPException:
        cleanup_repository_files(
            repo_id,
            zip_path,
            extract_path,
        )
        raise

    except Exception:
        cleanup_repository_files(
            repo_id,
            zip_path,
            extract_path,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to process uploaded repository.",
        )

    return {
        "message": "Repository uploaded and scanned successfully.",
        "repo_id": repo_id,
        "repo_name": repo_name,
        "original_filename": original_filename,
        "total_files_found": scan_result["total_files_found"],
        "code_files_found": scan_result["code_files_found"],
        "ignored_files": scan_result["ignored_files"],
        "languages": scan_result["languages"],
        "sample_code_files": scan_result["code_files"][:20],
        "skipped_extraction_files": skipped_files,
        "indexed": False,
    }


@router.get("")
def list_repositories(
    owner_sub: str = Depends(get_current_user_sub),
):
    """
    List only repositories belonging to the authenticated user.
    """

    metadata_items = list_user_repositories(owner_sub)

    repositories = []

    for metadata in metadata_items:
        repo_id = metadata["repo_id"]
        repo_folder = EXTRACT_DIR / repo_id

        # Do not expose stale metadata for repositories whose files
        # no longer exist on this server.
        if not repo_folder.exists():
            continue

        repositories.append(
            {
                "repo_id": repo_id,
                "repo_name": metadata.get(
                    "repo_name",
                    get_repo_root_name(repo_folder),
                ),
                "original_filename": metadata.get(
                    "original_filename",
                    get_original_filename(repo_id),
                ),
                "indexed": bool(
                    metadata.get("indexed", False)
                ),
                "created_at": metadata.get("created_at"),
            }
        )

    return {
        "total_repositories": len(repositories),
        "repositories": repositories,
    }


@router.delete("/{repo_id}")
def delete_repository(
    repo_id: str,
    owner_sub: str = Depends(get_current_user_sub),
):
    """
    Delete a repository owned by the authenticated user.

    Deletes:
    - uploaded ZIP
    - extracted repository
    - vector index
    - DynamoDB ownership metadata
    """

    require_repository_owner(
        owner_sub=owner_sub,
        repo_id=repo_id,
    )

    repo_path = EXTRACT_DIR / repo_id
    zip_path = get_uploaded_zip_for_repo(repo_id)

    deleted_items = []
    warnings = []

    if zip_path and zip_path.exists():
        try:
            zip_path.unlink()
            deleted_items.append("uploaded_zip")
        except Exception as exc:
            warnings.append(
                f"Could not delete uploaded ZIP: {str(exc)}"
            )

    if repo_path.exists():
        try:
            shutil.rmtree(repo_path)
            deleted_items.append("extracted_repository")
        except Exception as exc:
            warnings.append(
                f"Could not delete extracted repository: {str(exc)}"
            )
    else:
        warnings.append(
            "Extracted repository folder was not found."
        )

    try:
        vector_delete_result = delete_repository_index(repo_id)
    except Exception as exc:
        vector_delete_result = {
            "deleted": False,
        }
        warnings.append(
            f"Could not delete vector index: {str(exc)}"
        )

    delete_repository_metadata(
        owner_sub=owner_sub,
        repo_id=repo_id,
    )

    return {
        "repo_id": repo_id,
        "message": "Repository deletion completed.",
        "deleted_items": deleted_items,
        "vector_index": vector_delete_result,
        "warnings": warnings,
    }


@router.get("/{repo_id}/scan")
def scan_existing_repo(
    repo_id: str,
    owner_sub: str = Depends(get_current_user_sub),
):
    """
    Scan an authenticated user's existing repository.
    """

    repo_path = get_owned_repo_path(
        owner_sub,
        repo_id,
    )

    try:
        scan_result = scan_repository(repo_path)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to scan repository.",
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
def get_repo_chunks(
    repo_id: str,
    owner_sub: str = Depends(get_current_user_sub),
):
    """
    Create code chunks for an authenticated user's repository.
    """

    repo_path = get_owned_repo_path(
        owner_sub,
        repo_id,
    )

    try:
        chunk_result = create_code_chunks(repo_path)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to create code chunks.",
        )

    sample_chunks = []

    for chunk in chunk_result["chunks"][:10]:
        content = chunk["content"]

        sample_chunks.append(
            {
                "file_path": chunk["file_path"],
                "language": chunk["language"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "content_preview": content[:500],
            }
        )

    return {
        "repo_id": repo_id,
        "total_files_used": chunk_result["total_files_used"],
        "total_chunks": chunk_result["total_chunks"],
        "sample_chunks": sample_chunks,
    }


@router.post("/{repo_id}/index")
def index_repo(
    repo_id: str,
    owner_sub: str = Depends(get_current_user_sub),
):
    """
    Index an authenticated user's repository.
    """

    repo_path = get_owned_repo_path(
        owner_sub,
        repo_id,
    )

    try:
        index_result = index_repository(
            repo_id,
            repo_path,
        )

        mark_repository_indexed(
            owner_sub=owner_sub,
            repo_id=repo_id,
        )

    except Exception as exc:
        logger.exception(
            "Repository indexing failed. repo_id=%s owner_sub=%s",
            repo_id,
            owner_sub,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to index repository.",
        ) from exc

    return index_result


@router.get("/{repo_id}/search")
def search_repo(
    repo_id: str,
    query: str,
    top_k: int = 5,
    owner_sub: str = Depends(get_current_user_sub),
):
    """
    Search an authenticated user's indexed repository.
    """

    get_owned_repo_path(
        owner_sub,
        repo_id,
    )

    if not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    try:
        search_result = search_repository(
            repo_id,
            query,
            top_k,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to search repository.",
        )

    return search_result


@router.post("/{repo_id}/ask")
def ask_repo(
    repo_id: str,
    request: AskRepoRequest,
    owner_sub: str = Depends(get_current_user_sub),
):
    """
    Ask a question about an authenticated user's indexed repository.
    """

    get_owned_repo_path(
        owner_sub,
        repo_id,
    )

    try:
        answer_result = answer_question(
            repo_id=repo_id,
            question=request.question,
            top_k=request.top_k,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to answer question.",
        )

    return answer_result