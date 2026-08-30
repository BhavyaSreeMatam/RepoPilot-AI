import re
from pathlib import Path
from typing import Any, Dict, List


# Security scanning intentionally uses a different ignore policy from the
# normal RAG repository scanner.
#
# In particular, .github is NOT ignored because CI/CD workflows can contain
# security-sensitive configuration.
IGNORED_SECURITY_DIRS = {
    ".git",
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


TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".xml",
    ".sql",
    ".sh",
    ".bat",
    ".ps1",
    ".md",
    ".txt",
}


SPECIAL_SECURITY_FILES = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}


MAX_SECURITY_FILE_SIZE_BYTES = 1_000_000


SEVERITIES = (
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
    "INFO",
)


SECURITY_RULES = [
    {
        "rule_id": "SECRET-AWS-001",
        "category": "hardcoded_secret",
        "severity": "HIGH",
        "pattern": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "message": "Possible AWS access key ID found in source code.",
        "secret": True,
    },
    {
        "rule_id": "SECRET-PRIVATEKEY-001",
        "category": "private_key",
        "severity": "CRITICAL",
        "pattern": re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
            re.IGNORECASE,
        ),
        "message": "Private key material appears to be committed to the repository.",
        "secret": True,
    },
    {
        "rule_id": "SECRET-GENERIC-001",
        "category": "hardcoded_secret",
        "severity": "HIGH",
        "pattern": re.compile(
            r"""(?ix)
            \b(
                api[_-]?key
                |secret
                |client[_-]?secret
                |access[_-]?token
                |auth[_-]?token
                |password
                |passwd
                |access[_-]?key
            )
            \b
            \s*[:=]\s*
            ["']
            [^"']{8,}
            ["']
            """
        ),
        "message": "Possible hard-coded credential or secret found.",
        "secret": True,
    },
    {
        "rule_id": "SECRET-DBURL-001",
        "category": "hardcoded_credential",
        "severity": "HIGH",
        "pattern": re.compile(
            r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
            r"[^:\s/]+:[^@\s/]+@"
        ),
        "message": "Database connection string appears to contain embedded credentials.",
        "secret": True,
    },
    {
        "rule_id": "PY-CMD-001",
        "category": "command_execution",
        "severity": "HIGH",
        "pattern": re.compile(r"\bos\.system\s*\("),
        "message": "os.system() can allow unsafe shell command execution.",
        "secret": False,
    },
    {
        "rule_id": "PY-CMD-002",
        "category": "command_execution",
        "severity": "HIGH",
        "pattern": re.compile(
            r"\bsubprocess\.(?:run|call|Popen|check_call|check_output)"
            r"\s*\([^)]*shell\s*=\s*True",
            re.IGNORECASE,
        ),
        "message": "subprocess is invoked with shell=True, which can create command-injection risk.",
        "secret": False,
    },
    {
        "rule_id": "PY-EVAL-001",
        "category": "dynamic_code_execution",
        "severity": "HIGH",
        "pattern": re.compile(r"(?<![\w.])eval\s*\("),
        "message": "eval() executes dynamic code and can be dangerous with untrusted input.",
        "secret": False,
    },
    {
        "rule_id": "PY-EXEC-001",
        "category": "dynamic_code_execution",
        "severity": "HIGH",
        "pattern": re.compile(r"(?<![\w.])exec\s*\("),
        "message": "exec() executes dynamic code and can be dangerous with untrusted input.",
        "secret": False,
    },
    {
        "rule_id": "PY-PICKLE-001",
        "category": "unsafe_deserialization",
        "severity": "HIGH",
        "pattern": re.compile(r"\bpickle\.(?:load|loads)\s*\("),
        "message": "Python pickle deserialization is unsafe for untrusted data.",
        "secret": False,
    },
    {
        "rule_id": "PY-YAML-001",
        "category": "unsafe_deserialization",
        "severity": "MEDIUM",
        "pattern": re.compile(r"\byaml\.load\s*\("),
        "message": "yaml.load() should be reviewed to ensure a safe loader is used.",
        "secret": False,
    },
    {
        "rule_id": "HTTP-TLS-001",
        "category": "tls_verification",
        "severity": "HIGH",
        "pattern": re.compile(r"\bverify\s*=\s*False\b"),
        "message": "TLS certificate verification appears to be disabled.",
        "secret": False,
    },
    {
        "rule_id": "WEB-DEBUG-001",
        "category": "debug_configuration",
        "severity": "MEDIUM",
        "pattern": re.compile(r"\bdebug\s*=\s*True\b", re.IGNORECASE),
        "message": "Debug mode appears to be enabled and should not be used in production.",
        "secret": False,
    },
    {
        "rule_id": "WEB-CORS-001",
        "category": "cors_configuration",
        "severity": "MEDIUM",
        "pattern": re.compile(
            r"""allow_origins\s*=\s*\[\s*["']\*["']\s*\]""",
            re.IGNORECASE,
        ),
        "message": "CORS appears to allow every origin.",
        "secret": False,
    },
    {
        "rule_id": "CRYPTO-MD5-001",
        "category": "weak_cryptography",
        "severity": "LOW",
        "pattern": re.compile(r"\bhashlib\.md5\s*\("),
        "message": "MD5 is cryptographically weak and should not be used for security-sensitive hashing.",
        "secret": False,
    },
    {
        "rule_id": "CRYPTO-SHA1-001",
        "category": "weak_cryptography",
        "severity": "LOW",
        "pattern": re.compile(r"\bhashlib\.sha1\s*\("),
        "message": "SHA-1 is cryptographically weak and should not be used for security-sensitive hashing.",
        "secret": False,
    },
    {
        "rule_id": "DOCKER-PRIV-001",
        "category": "container_security",
        "severity": "HIGH",
        "pattern": re.compile(r"^\s*privileged\s*:\s*true\s*$", re.IGNORECASE),
        "message": "Container appears to run in privileged mode.",
        "secret": False,
    },
    {
        "rule_id": "DOCKER-ROOT-001",
        "category": "container_security",
        "severity": "MEDIUM",
        "pattern": re.compile(r"^\s*USER\s+root\s*$", re.IGNORECASE),
        "message": "Docker container explicitly runs as the root user.",
        "secret": False,
    },
    {
        "rule_id": "GHA-WRITEALL-001",
        "category": "ci_cd_permissions",
        "severity": "HIGH",
        "pattern": re.compile(r"^\s*permissions\s*:\s*write-all\s*$", re.IGNORECASE),
        "message": "GitHub Actions workflow grants write-all permissions.",
        "secret": False,
    },
    {
        "rule_id": "GHA-PRTARGET-001",
        "category": "ci_cd_security",
        "severity": "MEDIUM",
        "pattern": re.compile(r"^\s*pull_request_target\s*:", re.IGNORECASE),
        "message": "pull_request_target workflow detected; review untrusted-code checkout and secret usage carefully.",
        "secret": False,
    },
]


def _should_ignore(path: Path, repo_path: Path) -> bool:
    try:
        relative_path = path.relative_to(repo_path)
    except ValueError:
        return True

    directory_parts = relative_path.parts[:-1]

    return any(part in IGNORED_SECURITY_DIRS for part in directory_parts)


def _is_security_text_file(path: Path) -> bool:
    name = path.name.lower()

    if name in SPECIAL_SECURITY_FILES:
        return True

    # Include .env, .env.local, .env.production, .env.example, etc.
    if name == ".env" or name.startswith(".env."):
        return True

    return path.suffix.lower() in TEXT_EXTENSIONS


def _looks_like_placeholder(line: str) -> bool:
    """
    Prevent obvious example values from being reported as leaked credentials.
    """

    lowered = line.lower()

    placeholder_markers = (
        "your_api_key",
        "your-api-key",
        "your_secret",
        "your-secret",
        "your_password",
        "your-password",
        "replace_me",
        "replace-me",
        "changeme",
        "change_me",
        "change-me",
        "example",
        "dummy",
        "placeholder",
        "<token>",
        "<secret>",
        "<password>",
        "${",
    )

    return any(marker in lowered for marker in placeholder_markers)


def _redact_evidence(line: str) -> str:
    """
    Avoid returning actual secret values in scanner results.

    RepoPilot should detect secrets without forwarding raw credentials into
    logs, the frontend, or the LLM security agent.
    """

    redacted = line.strip()

    # AWS access key IDs.
    redacted = re.sub(
        r"\bAKIA[0-9A-Z]{16}\b",
        "AKIA****************",
        redacted,
    )

    # Credentials embedded in connection strings.
    redacted = re.sub(
        r"(?i)(://[^:\s/]+:)[^@\s/]+(@)",
        r"\1***REDACTED***\2",
        redacted,
    )

    # Common secret assignments.
    redacted = re.sub(
        r"""(?ix)
        (
            \b(?:api[_-]?key|secret|client[_-]?secret|access[_-]?token|
            auth[_-]?token|password|passwd|access[_-]?key)\b
            \s*[:=]\s*
            ["']
        )
        [^"']+
        (["'])
        """,
        r"\1***REDACTED***\2",
        redacted,
    )

    if "PRIVATE KEY-----" in redacted.upper():
        return "[PRIVATE KEY MATERIAL REDACTED]"

    return redacted[:300]


def _build_finding(
    *,
    rule: Dict[str, Any],
    relative_path: str,
    line_number: int,
    line: str,
) -> Dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "severity": rule["severity"],
        "category": rule["category"],
        "file_path": relative_path,
        "start_line": line_number,
        "end_line": line_number,
        "evidence": _redact_evidence(line),
        "message": rule["message"],
    }


def scan_security_repository(repo_path: Path) -> Dict[str, Any]:
    """
    Perform a read-only static security scan of an extracted repository.

    Important:
    - Repository code is NEVER executed.
    - Binary/generated/dependency folders are skipped.
    - Security-sensitive configuration such as .github workflows and .env
      files is intentionally inspected.
    - Detected credential values are redacted from returned evidence.
    """

    repo_path = repo_path.resolve()

    if not repo_path.exists():
        raise FileNotFoundError(f"Repository does not exist: {repo_path}")

    if not repo_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo_path}")

    findings: List[Dict[str, Any]] = []
    files_scanned = 0
    files_skipped = 0

    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue

        if _should_ignore(path, repo_path):
            files_skipped += 1
            continue

        if not _is_security_text_file(path):
            files_skipped += 1
            continue

        try:
            if path.stat().st_size > MAX_SECURITY_FILE_SIZE_BYTES:
                files_skipped += 1
                continue
        except OSError:
            files_skipped += 1
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            files_skipped += 1
            continue

        files_scanned += 1

        relative_path = str(path.relative_to(repo_path))

        for line_number, line in enumerate(content.splitlines(), start=1):

            for rule in SECURITY_RULES:

                # Avoid false-positive yaml.load() findings when SafeLoader is
                # explicitly present on the same line.
                if (
                    rule["rule_id"] == "PY-YAML-001"
                    and "SafeLoader" in line
                ):
                    continue

                if not rule["pattern"].search(line):
                    continue

                # Don't report obvious example placeholders as leaked secrets.
                if rule["secret"] and _looks_like_placeholder(line):
                    continue

                findings.append(
                    _build_finding(
                        rule=rule,
                        relative_path=relative_path,
                        line_number=line_number,
                        line=line,
                    )
                )

    severity_counts = {
        severity: 0
        for severity in SEVERITIES
    }

    for finding in findings:
        severity = finding["severity"]

        if severity in severity_counts:
            severity_counts[severity] += 1

    return {
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "findings_count": len(findings),
        "severity_counts": severity_counts,
        "findings": findings,
    }