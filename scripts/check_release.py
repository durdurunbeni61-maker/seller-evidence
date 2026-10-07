"""Guard a small explicit publication allowlist; not a comprehensive secret scanner."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

FILES = (
    ".github/workflows/tests.yml", ".gitignore", "AGENTS.md", "CONTRIBUTING.md",
    "LICENSE", "README.md", "SECURITY.md", "pyproject.toml",
    "docs/SCHEMAS.md", "docs/THIRD_PARTY_NOTICES.md",
    "examples/experiments.fictional.csv", "examples/stats.fictional.csv",
    "scripts/check_release.py", "src/seller_evidence/__init__.py",
    "src/seller_evidence/__main__.py", "src/seller_evidence/analysis.py",
    "src/seller_evidence/cli.py", "src/seller_evidence/csv_data.py",
    "src/seller_evidence/experiments.py", "tests/test_evidence.py",
)
GENERATED = {".git", ".venv", "__pycache__", ".pytest_cache", ".test-tmp", "build", "dist",
             "data", "reports", "output"}
FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib", "aiohttp", "socket", "http",
                     "playwright", "selenium", "pyppeteer", "webbrowser"}
CHECKS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_credential": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{40,})"),
    "cloud_credential": re.compile(r"AKIA[A-Z0-9]{16}"),
    "personal_email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "absolute_local_path": re.compile(r"(?:[A-Za-z]:[\\/]|/(?:Users|home)/)[A-Za-z0-9]"),
}


def check(root: Path) -> list[str]:
    """Check only published text, and reject undeclared non-generated files."""
    findings = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in GENERATED or part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.is_symlink():
            findings.append(f"Symlink not allowed: {relative.as_posix()}")
        elif path.is_file() and relative.as_posix() not in FILES:
            findings.append(f"Unapproved file: {relative.as_posix()}")
    for name in FILES:
        path = root / name
        if not path.is_file() or path.is_symlink():
            findings.append(f"Missing or unsafe approved file: {name}")
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in CHECKS.items():
            if pattern.search(text):
                findings.append(f"Potential {label}: {name}; inspect privately")
        if name.endswith(".py"):
            for node in ast.walk(ast.parse(text, filename=name)):
                imports = []
                if isinstance(node, ast.Import):
                    imports = [item.name.split(".")[0] for item in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports = [node.module.split(".")[0]]
                if set(imports) & FORBIDDEN_IMPORTS:
                    findings.append(f"Network/browser import: {name}:{node.lineno}")
    return findings


if __name__ == "__main__":
    issues = check(Path(__file__).resolve().parents[1])
    print("\n".join(issues) if issues else f"PASS: {len(FILES)} approved files checked")
    sys.exit(1 if issues else 0)
