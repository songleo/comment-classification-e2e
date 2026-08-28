from __future__ import annotations

import re
from pathlib import Path

from comment_classifier.settings import PROJECT_ROOT


LOCAL_PATH_PATTERNS = {
    "Windows drive absolute path": re.compile(r"(?i)\b[A-Z]:[\\/]"),
    "macOS user directory": re.compile(r"/Users/[^/\s]+"),
    "Linux user directory": re.compile(r"/home/[^/\s]+"),
    "WSL mounted drive": re.compile(r"(?i)/mnt/[a-z]/"),
}

LOCAL_PYTHON_WORKFLOW_PATTERNS = {
    "local virtual environment": re.compile(r"(?i)(?:python|py)\s+-m\s+venv|\.venv[\\/]"),
    "bare local Python module command": re.compile(r"(?m)^\s*(?:&\s*\$python\s+|python\s+)-m\s+"),
    "legacy local PowerShell workflow": re.compile(r"scripts[\\/](?:run-e2e|start-local-api)\.ps1"),
}


def public_documentation() -> list[Path]:
    documents = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "CONTRIBUTING.md",
        PROJECT_ROOT / "SECURITY.md",
        PROJECT_ROOT / "AGENTS.md",
    ]
    documents.extend(sorted((PROJECT_ROOT / "docs").glob("*.md")))
    return documents


def test_public_documentation_has_no_local_absolute_paths() -> None:
    violations: list[str] = []
    for document in public_documentation():
        content = document.read_text(encoding="utf-8")
        for description, pattern in LOCAL_PATH_PATTERNS.items():
            if match := pattern.search(content):
                relative_path = document.relative_to(PROJECT_ROOT)
                violations.append(f"{relative_path}: {description}: {match.group(0)}")

    assert not violations, "Local absolute paths found:\n" + "\n".join(violations)


def test_public_documentation_uses_docker_only_workflows() -> None:
    violations: list[str] = []
    for document in public_documentation():
        content = document.read_text(encoding="utf-8")
        for description, pattern in LOCAL_PYTHON_WORKFLOW_PATTERNS.items():
            if match := pattern.search(content):
                relative_path = document.relative_to(PROJECT_ROOT)
                violations.append(f"{relative_path}: {description}: {match.group(0)}")

    assert not violations, "Non-Docker documentation workflow found:\n" + "\n".join(violations)
