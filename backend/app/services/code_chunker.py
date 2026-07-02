from pathlib import Path
from typing import Dict, List

from app.services.repo_scanner import scan_repository


CHUNK_SIZE_LINES = 80
CHUNK_OVERLAP_LINES = 15


def read_text_file(file_path: Path) -> str:
    """
    Read a text/code file safely.
    Tries UTF-8 first, then falls back to latin-1.
    """

    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="latin-1", errors="ignore")


def chunk_file_content(
    content: str,
    file_path: str,
    language: str,
) -> List[Dict]:
    """
    Split file content into line-based chunks.
    Each chunk stores file path, language, line numbers, and content.
    """

    lines = content.splitlines()

    if not lines:
        return []

    chunks = []
    start_index = 0

    while start_index < len(lines):
        end_index = min(start_index + CHUNK_SIZE_LINES, len(lines))
        chunk_lines = lines[start_index:end_index]

        chunk = {
            "file_path": file_path,
            "language": language,
            "start_line": start_index + 1,
            "end_line": end_index,
            "content": "\n".join(chunk_lines),
        }

        chunks.append(chunk)

        if end_index == len(lines):
            break

        start_index = end_index - CHUNK_OVERLAP_LINES

    return chunks


def create_code_chunks(repo_path: Path) -> Dict:
    """
    Scan repository, read useful files, and create code chunks.
    """

    scan_result = scan_repository(repo_path)
    code_files = scan_result["code_files"]

    all_chunks: List[Dict] = []

    for code_file in code_files:
        relative_file_path = code_file["path"]
        absolute_file_path = repo_path / relative_file_path

        try:
            content = read_text_file(absolute_file_path)
        except OSError:
            continue

        file_chunks = chunk_file_content(
            content=content,
            file_path=relative_file_path,
            language=code_file["language"],
        )

        all_chunks.extend(file_chunks)

    return {
        "total_files_used": len(code_files),
        "total_chunks": len(all_chunks),
        "chunks": all_chunks,
    }