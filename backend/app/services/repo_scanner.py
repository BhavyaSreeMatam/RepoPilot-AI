from pathlib import Path
from typing import Dict, List


IGNORED_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    "coverage",
    ".idea",
    ".vscode",
}


IGNORED_FILE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
    ".pyo",
    ".class",
    ".lock",
    ".log",
}


LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".env.example": "Environment Example",
    ".md": "Markdown",
    ".txt": "Text",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".dockerfile": "Dockerfile",
}


MAX_FILE_SIZE_BYTES = 500_000


def should_ignore_path(path: Path) -> bool:
    """
    Returns True if a file/folder path should be ignored.
    """

    path_parts = set(path.parts)

    if path_parts.intersection(IGNORED_DIRS):
        return True

    if path.suffix.lower() in IGNORED_FILE_EXTENSIONS:
        return True

    if path.name.lower() in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}:
        return True

    return False


def detect_language(path: Path) -> str:
    """
    Detect programming language based on file extension or file name.
    """

    file_name = path.name.lower()

    if file_name == "dockerfile":
        return "Dockerfile"

    if path.suffix.lower() in LANGUAGE_MAP:
        return LANGUAGE_MAP[path.suffix.lower()]

    return "Unknown"


def scan_repository(repo_path: Path) -> Dict:
    """
    Scan a repository folder and return useful code/documentation files.
    """

    all_files_count = 0
    ignored_files_count = 0
    code_files: List[Dict] = []
    languages: Dict[str, int] = {}

    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue

        all_files_count += 1

        if should_ignore_path(path):
            ignored_files_count += 1
            continue

        try:
            size_bytes = path.stat().st_size
        except OSError:
            ignored_files_count += 1
            continue

        if size_bytes > MAX_FILE_SIZE_BYTES:
            ignored_files_count += 1
            continue

        language = detect_language(path)

        if language == "Unknown":
            ignored_files_count += 1
            continue

        relative_path = str(path.relative_to(repo_path))

        code_file = {
            "path": relative_path,
            "language": language,
            "size_bytes": size_bytes,
        }

        code_files.append(code_file)
        languages[language] = languages.get(language, 0) + 1

    return {
        "total_files_found": all_files_count,
        "code_files_found": len(code_files),
        "ignored_files": ignored_files_count,
        "languages": languages,
        "code_files": code_files,
    }